from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4

from src.domain.reference_data import (
    PAYMENT_TERMS_METADATA,
    VALID_COUNTRIES,
    VALID_CURRENCIES,
    VALID_INCOTERMS,
    VALID_MARKETPLACES,
    VALID_PAYMENT_TERMS,
    VALID_PORTS,
)
from src.domain.user import UserRole


class LineHasDownstreamArtifactError(ValueError):
    """Raised when post-acceptance removal hits a line already in an invoice or shipment.

    Carrying the specific reason message through the exception lets the router
    surface it in the 409 detail without introspecting arbitrary ValueError text.
    """


class POStatus(Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    # REJECTED is only reachable via negotiation convergence when every line
    # has been removed. It is not set by a direct reject() call.
    REJECTED = "REJECTED"
    REVISED = "REVISED"
    # MODIFIED indicates an in-flight negotiation round; the PO is between hand-offs.
    MODIFIED = "MODIFIED"


class POType(Enum):
    PROCUREMENT = "PROCUREMENT"
    OPEX = "OPEX"


class LineItemStatus(Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    # MODIFIED_BY_VENDOR / MODIFIED_BY_SM mark which party last edited the line;
    # the other party is the one allowed to accept or counter.
    MODIFIED_BY_VENDOR = "MODIFIED_BY_VENDOR"
    MODIFIED_BY_SM = "MODIFIED_BY_SM"
    # REMOVED is a terminal status — the line has been dropped from the PO.
    REMOVED = "REMOVED"


# Fields the vendor or SM may edit on a line via modify_line.
# part_number is immutable; the identity of the line is the contract under negotiation.
EDITABLE_LINE_FIELDS: tuple[str, ...] = (
    "quantity",
    "unit_price",
    "uom",
    "description",
    "hs_code",
    "country_of_origin",
    "required_delivery_date",
)

_MAX_ROUND_COUNT: int = 2


@dataclass
class LineItem:
    part_number: str
    description: str
    quantity: int
    uom: str
    unit_price: Decimal
    hs_code: str
    country_of_origin: str
    product_id: str | None = None
    status: LineItemStatus = field(default=LineItemStatus.PENDING)
    required_delivery_date: datetime | None = None

    def __post_init__(self) -> None:
        if not self.part_number or not self.part_number.strip():
            raise ValueError("part_number must not be empty or whitespace-only")
        # quantity == 0 is valid on a REMOVED line; creation still rejects zero because
        # new lines are always PENDING and must carry a real quantity.
        if self.quantity < 0:
            raise ValueError("quantity must be >= 0")
        if self.quantity == 0 and self.status is not LineItemStatus.REMOVED:
            raise ValueError("quantity must be greater than 0")
        if self.unit_price < Decimal("0"):
            raise ValueError("unit_price must be >= 0")


@dataclass
class RejectionRecord:
    comment: str
    rejected_at: datetime


@dataclass
class LineEditHistoryEntry:
    # One row per field edit; append-only. part_number carries through because
    # line identity is by part_number within a PO.
    part_number: str
    round: int
    actor_role: UserRole
    field: str
    old_value: str
    new_value: str
    edited_at: datetime


class PurchaseOrder:
    # id owns the aggregate identity; po_number owns the business reference
    def __init__(
        self,
        *,
        id: str,
        po_number: str,
        status: POStatus,
        po_type: POType,
        vendor_id: str,
        buyer_name: str,
        buyer_country: str,
        ship_to_address: str,
        payment_terms: str,
        currency: str,
        issued_date: datetime,
        required_delivery_date: datetime,
        terms_and_conditions: str,
        incoterm: str,
        port_of_loading: str,
        port_of_discharge: str,
        country_of_origin: str,
        country_of_destination: str,
        line_items: list[LineItem],
        rejection_history: list[RejectionRecord],
        created_at: datetime,
        updated_at: datetime,
        marketplace: str | None = None,
        round_count: int = 0,
        last_actor_role: UserRole | None = None,
        line_edit_history: list[LineEditHistoryEntry] | None = None,
        advance_paid_at: datetime | None = None,
    ) -> None:
        self._id = id
        self._po_number = po_number
        self.status = status
        self.po_type = po_type
        self.vendor_id = vendor_id
        self.buyer_name = buyer_name
        self.buyer_country = buyer_country
        self.ship_to_address = ship_to_address
        self.payment_terms = payment_terms
        self.currency = currency
        self.issued_date = issued_date
        self.required_delivery_date = required_delivery_date
        self.terms_and_conditions = terms_and_conditions
        self.incoterm = incoterm
        self.port_of_loading = port_of_loading
        self.port_of_discharge = port_of_discharge
        self.country_of_origin = country_of_origin
        self.country_of_destination = country_of_destination
        self.marketplace = marketplace
        self.line_items = line_items
        self.rejection_history = rejection_history
        self._created_at = created_at
        self.updated_at = updated_at
        self.round_count = round_count
        self.last_actor_role = last_actor_role
        self.line_edit_history = line_edit_history if line_edit_history is not None else []
        self.advance_paid_at = advance_paid_at

    @property
    def id(self) -> str:
        return self._id

    @property
    def po_number(self) -> str:
        return self._po_number

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def requires_advance(self) -> bool:
        # Derives from payment_terms reference metadata; no stored column.
        entry = PAYMENT_TERMS_METADATA.get(self.payment_terms, {})
        return bool(entry.get("has_advance", False))

    @property
    def total_value(self) -> Decimal:
        return sum(
            (item.quantity * item.unit_price for item in self.line_items),
            Decimal("0"),
        )

    @classmethod
    def _validate_reference_fields(
        cls,
        *,
        currency: str,
        payment_terms: str,
        incoterm: str,
        buyer_country: str,
        country_of_origin: str,
        country_of_destination: str,
        port_of_loading: str,
        port_of_discharge: str,
    ) -> None:
        # Each field is constrained to its reference set; codes outside it are rejected
        if currency not in VALID_CURRENCIES:
            raise ValueError(f"invalid currency: {currency!r}")
        if payment_terms not in VALID_PAYMENT_TERMS:
            raise ValueError(f"invalid payment_terms: {payment_terms!r}")
        if incoterm not in VALID_INCOTERMS:
            raise ValueError(f"invalid incoterm: {incoterm!r}")
        if buyer_country not in VALID_COUNTRIES:
            raise ValueError(f"invalid buyer_country: {buyer_country!r}")
        if country_of_origin not in VALID_COUNTRIES:
            raise ValueError(f"invalid country_of_origin: {country_of_origin!r}")
        if country_of_destination not in VALID_COUNTRIES:
            raise ValueError(f"invalid country_of_destination: {country_of_destination!r}")
        if port_of_loading not in VALID_PORTS:
            raise ValueError(f"invalid port_of_loading: {port_of_loading!r}")
        if port_of_discharge not in VALID_PORTS:
            raise ValueError(f"invalid port_of_discharge: {port_of_discharge!r}")

    @classmethod
    def create(
        cls,
        *,
        po_number: str,
        vendor_id: str,
        buyer_name: str,
        buyer_country: str,
        ship_to_address: str,
        payment_terms: str,
        currency: str,
        issued_date: datetime,
        required_delivery_date: datetime,
        terms_and_conditions: str,
        incoterm: str,
        port_of_loading: str,
        port_of_discharge: str,
        country_of_origin: str,
        country_of_destination: str,
        line_items: list[LineItem],
        po_type: POType = POType.PROCUREMENT,
        marketplace: str | None = None,
    ) -> PurchaseOrder:
        cls._validate_reference_fields(
            currency=currency,
            payment_terms=payment_terms,
            incoterm=incoterm,
            buyer_country=buyer_country,
            country_of_origin=country_of_origin,
            country_of_destination=country_of_destination,
            port_of_loading=port_of_loading,
            port_of_discharge=port_of_discharge,
        )
        if marketplace is not None and marketplace not in VALID_MARKETPLACES:
            raise ValueError(f"invalid marketplace: {marketplace!r}")
        if not line_items:
            raise ValueError("at least one line item is required")
        now = datetime.now(UTC)
        return cls(
            id=str(uuid4()),
            po_number=po_number,
            status=POStatus.DRAFT,
            po_type=po_type,
            vendor_id=vendor_id,
            buyer_name=buyer_name,
            buyer_country=buyer_country,
            ship_to_address=ship_to_address,
            payment_terms=payment_terms,
            currency=currency,
            issued_date=issued_date,
            required_delivery_date=required_delivery_date,
            terms_and_conditions=terms_and_conditions,
            incoterm=incoterm,
            port_of_loading=port_of_loading,
            port_of_discharge=port_of_discharge,
            country_of_origin=country_of_origin,
            country_of_destination=country_of_destination,
            marketplace=marketplace,
            line_items=list(line_items),
            rejection_history=[],
            created_at=now,
            updated_at=now,
        )

    def submit(self) -> None:
        # DRAFT is the only state from which a PO may enter the review pipeline
        if self.status is not POStatus.DRAFT:
            raise ValueError(
                f"submit requires DRAFT status; current status is {self.status.value}"
            )
        self.status = POStatus.PENDING
        self.updated_at = datetime.now(UTC)

    def accept(self) -> None:
        # Convenience: SM accepts all lines at round 0. Only valid on a PENDING PO.
        if self.status is not POStatus.PENDING:
            raise ValueError(
                f"accept requires PENDING status; current status is {self.status.value}"
            )
        for item in self.line_items:
            item.status = LineItemStatus.ACCEPTED
        self.status = POStatus.ACCEPTED
        self.updated_at = datetime.now(UTC)

    # ------------------------------------------------------------------
    # Line-level negotiation (iter 056)
    # ------------------------------------------------------------------

    def _find_line(self, part_number: str) -> LineItem:
        for item in self.line_items:
            if item.part_number == part_number:
                return item
        raise ValueError(f"unknown part_number: {part_number!r}")

    def modify_line(
        self,
        part_number: str,
        actor_role: UserRole,
        fields: dict[str, object],
    ) -> None:
        # Vendor or SM counter-proposes new field values on a single line.
        if self.status not in (POStatus.PENDING, POStatus.MODIFIED):
            raise ValueError(
                f"modify_line requires PENDING or MODIFIED status; current status is {self.status.value}"
            )
        if "part_number" in fields:
            raise ValueError("part_number is immutable and cannot be modified")
        invalid_fields = [name for name in fields if name not in EDITABLE_LINE_FIELDS]
        if invalid_fields:
            raise ValueError(
                f"fields not editable: {sorted(invalid_fields)}; "
                f"editable fields are {list(EDITABLE_LINE_FIELDS)}"
            )
        line = self._find_line(part_number)
        if line.status in (LineItemStatus.ACCEPTED, LineItemStatus.REMOVED):
            raise ValueError(
                f"cannot modify line in terminal status {line.status.value}"
            )

        now = datetime.now(UTC)

        # qty=0 is a removal shortcut: skip MODIFIED_BY_* and go straight to REMOVED.
        qty_candidate = fields.get("quantity")
        going_to_zero = qty_candidate is not None and int(qty_candidate) == 0  # type: ignore[arg-type]

        changed_entries: list[LineEditHistoryEntry] = []
        for field_name, new_value in fields.items():
            old_value = getattr(line, field_name)
            if old_value == new_value:
                continue
            changed_entries.append(
                LineEditHistoryEntry(
                    part_number=line.part_number,
                    round=self.round_count,
                    actor_role=actor_role,
                    field=field_name,
                    old_value=_to_str(old_value),
                    new_value=_to_str(new_value),
                    edited_at=now,
                )
            )
            setattr(line, field_name, new_value)

        if going_to_zero:
            line.status = LineItemStatus.REMOVED
        else:
            line.status = (
                LineItemStatus.MODIFIED_BY_VENDOR
                if actor_role is UserRole.VENDOR
                else LineItemStatus.MODIFIED_BY_SM
            )

        self.line_edit_history.extend(changed_entries)
        self.updated_at = now

    def accept_line(self, part_number: str, actor_role: UserRole) -> None:
        # Accept the other party's latest modification on a line.
        if self.status not in (POStatus.PENDING, POStatus.MODIFIED):
            raise ValueError(
                f"accept_line requires PENDING or MODIFIED status; current status is {self.status.value}"
            )
        line = self._find_line(part_number)
        if line.status not in (
            LineItemStatus.PENDING,
            LineItemStatus.MODIFIED_BY_VENDOR,
            LineItemStatus.MODIFIED_BY_SM,
        ):
            raise ValueError(
                f"cannot accept line in status {line.status.value}"
            )
        # A party cannot accept their own modification — the counterpart must.
        if (
            line.status is LineItemStatus.MODIFIED_BY_VENDOR
            and actor_role is UserRole.VENDOR
        ) or (
            line.status is LineItemStatus.MODIFIED_BY_SM and actor_role is UserRole.SM
        ):
            raise ValueError(
                "cannot accept a line modified by the same role; the counterpart must accept"
            )
        line.status = LineItemStatus.ACCEPTED
        self.updated_at = datetime.now(UTC)

    def remove_line(self, part_number: str, actor_role: UserRole) -> None:
        # Voluntary pre-acceptance removal; either party may remove a non-terminal line.
        if self.status not in (POStatus.PENDING, POStatus.MODIFIED):
            raise ValueError(
                f"remove_line requires PENDING or MODIFIED status; current status is {self.status.value}"
            )
        line = self._find_line(part_number)
        if line.status in (LineItemStatus.ACCEPTED, LineItemStatus.REMOVED):
            raise ValueError(
                f"cannot remove line in terminal status {line.status.value}"
            )
        line.status = LineItemStatus.REMOVED
        self.updated_at = datetime.now(UTC)

    def force_accept_line(self, part_number: str, actor_role: UserRole) -> None:
        # Round-2 SM override: force a contested line to ACCEPTED.
        self._check_force_preconditions(actor_role)
        line = self._find_line(part_number)
        if line.status in (LineItemStatus.ACCEPTED, LineItemStatus.REMOVED):
            raise ValueError(
                f"cannot force-accept line in terminal status {line.status.value}"
            )
        line.status = LineItemStatus.ACCEPTED
        self.updated_at = datetime.now(UTC)

    def force_remove_line(self, part_number: str, actor_role: UserRole) -> None:
        # Round-2 SM override: force a contested line to REMOVED.
        self._check_force_preconditions(actor_role)
        line = self._find_line(part_number)
        if line.status in (LineItemStatus.ACCEPTED, LineItemStatus.REMOVED):
            raise ValueError(
                f"cannot force-remove line in terminal status {line.status.value}"
            )
        line.status = LineItemStatus.REMOVED
        self.updated_at = datetime.now(UTC)

    def _check_force_preconditions(self, actor_role: UserRole) -> None:
        if actor_role is not UserRole.SM:
            raise ValueError("force actions are only permitted for SM role")
        if self.round_count != _MAX_ROUND_COUNT:
            raise ValueError(
                f"force actions are only permitted at round {_MAX_ROUND_COUNT}; "
                f"current round is {self.round_count}"
            )

    def submit_response(self, actor_role: UserRole) -> None:
        # Hand-off: caller finalises their round of edits. Increments round_count,
        # records last_actor_role, and checks for convergence.
        if self.status not in (POStatus.PENDING, POStatus.MODIFIED):
            raise ValueError(
                f"submit_response requires PENDING or MODIFIED status; "
                f"current status is {self.status.value}"
            )

        # Terminal convergence — is every line ACCEPTED or REMOVED?
        all_terminal = all(
            item.status in (LineItemStatus.ACCEPTED, LineItemStatus.REMOVED)
            for item in self.line_items
        )
        any_accepted = any(
            item.status is LineItemStatus.ACCEPTED for item in self.line_items
        )

        if not all_terminal and self.round_count >= _MAX_ROUND_COUNT:
            raise ValueError(
                f"round cap reached ({_MAX_ROUND_COUNT}); use force_accept_line or "
                "force_remove_line to resolve remaining lines"
            )

        self.last_actor_role = actor_role

        if all_terminal:
            # Convergence: skip round increment; the negotiation has ended.
            if any_accepted:
                self.status = POStatus.ACCEPTED
            else:
                self.status = POStatus.REJECTED
        else:
            # Still contested — increment the round counter and mark the PO as MODIFIED.
            self.round_count += 1
            self.status = POStatus.MODIFIED

        self.updated_at = datetime.now(UTC)

    # ------------------------------------------------------------------
    # Revise/resubmit (unchanged from iter 037)
    # ------------------------------------------------------------------

    def revise(
        self,
        *,
        vendor_id: str,
        buyer_name: str,
        buyer_country: str,
        ship_to_address: str,
        payment_terms: str,
        currency: str,
        issued_date: datetime,
        required_delivery_date: datetime,
        terms_and_conditions: str,
        incoterm: str,
        port_of_loading: str,
        port_of_discharge: str,
        country_of_origin: str,
        country_of_destination: str,
        line_items: list[LineItem],
        marketplace: str | None = None,
    ) -> None:
        # Revision is the vendor's response to a rejection; only valid after REJECTED
        if self.status is not POStatus.REJECTED:
            raise ValueError(
                f"revise requires REJECTED status; current status is {self.status.value}"
            )
        self._validate_reference_fields(
            currency=currency,
            payment_terms=payment_terms,
            incoterm=incoterm,
            buyer_country=buyer_country,
            country_of_origin=country_of_origin,
            country_of_destination=country_of_destination,
            port_of_loading=port_of_loading,
            port_of_discharge=port_of_discharge,
        )
        if marketplace is not None and marketplace not in VALID_MARKETPLACES:
            raise ValueError(f"invalid marketplace: {marketplace!r}")
        if not line_items:
            raise ValueError("at least one line item is required")
        self.vendor_id = vendor_id
        self.buyer_name = buyer_name
        self.buyer_country = buyer_country
        self.ship_to_address = ship_to_address
        self.payment_terms = payment_terms
        self.currency = currency
        self.issued_date = issued_date
        self.required_delivery_date = required_delivery_date
        self.terms_and_conditions = terms_and_conditions
        self.incoterm = incoterm
        self.port_of_loading = port_of_loading
        self.port_of_discharge = port_of_discharge
        self.country_of_origin = country_of_origin
        self.country_of_destination = country_of_destination
        self.marketplace = marketplace
        self.line_items = list(line_items)
        self.status = POStatus.REVISED
        self.updated_at = datetime.now(UTC)

    def resubmit(self) -> None:
        # REVISED re-enters the review pipeline as PENDING
        if self.status is not POStatus.REVISED:
            raise ValueError(
                f"resubmit requires REVISED status; current status is {self.status.value}"
            )
        self.status = POStatus.PENDING
        self.updated_at = datetime.now(UTC)

    # ------------------------------------------------------------------
    # Advance payment gate and post-acceptance scope changes (iter 059)
    # ------------------------------------------------------------------

    def mark_advance_paid(self, actor_id: str) -> None:
        # Records the advance receipt. Idempotent: a second call on an already-paid
        # PO is a no-op — no timestamp change, no updated_at bump.
        if self.advance_paid_at is not None:
            return
        if self.status not in (POStatus.ACCEPTED, POStatus.MODIFIED):
            raise ValueError(
                f"mark_advance_paid requires ACCEPTED or MODIFIED status; "
                f"current status is {self.status.value}"
            )
        if not self.requires_advance:
            raise ValueError(
                f"payment_terms {self.payment_terms!r} does not require an advance"
            )
        now = datetime.now(UTC)
        self.advance_paid_at = now
        self.updated_at = now

    def can_modify_post_acceptance(
        self, first_milestone_posted_at: datetime | None
    ) -> bool:
        # The post-acceptance scope-change window closes on the first of:
        # (a) a production milestone has been posted, or
        # (b) the advance has been recorded (for advance-required POs).
        # Status must still be ACCEPTED; MODIFIED means a round is open and the
        # normal line-negotiation path handles scope changes.
        if self.status is not POStatus.ACCEPTED:
            return False
        if first_milestone_posted_at is not None:
            return False
        if self.requires_advance and self.advance_paid_at is not None:
            return False
        return True

    def add_line_post_acceptance(
        self,
        line: LineItem,
        actor_id: str,
        first_milestone_posted_at: datetime | None,
    ) -> None:
        # SM-only add. Gate composition lives on the PO so the service layer
        # supplies the "first milestone posted at" observation. The added line is
        # ACCEPTED directly: SM is the adder, no negotiation is needed.
        if not self.can_modify_post_acceptance(first_milestone_posted_at):
            raise ValueError(
                "post-acceptance modification window is closed: "
                "PO is not ACCEPTED, a milestone has been posted, or the advance is paid"
            )
        # Part numbers are unique within a PO by domain rule.
        for existing in self.line_items:
            if existing.part_number == line.part_number:
                raise ValueError(
                    f"line with part_number {line.part_number!r} already exists"
                )
        line.status = LineItemStatus.ACCEPTED
        self.line_items.append(line)
        self.updated_at = datetime.now(UTC)

    def remove_line_post_acceptance(
        self,
        part_number: str,
        actor_id: str,
        first_milestone_posted_at: datetime | None,
        has_downstream_artifact: bool,
    ) -> None:
        # SM-only remove. Gate and downstream-artifact check are both applied;
        # the router composes them from the respective repositories and passes
        # the booleans/timestamps in so the domain stays side-effect-free.
        if not self.can_modify_post_acceptance(first_milestone_posted_at):
            raise ValueError(
                "post-acceptance modification window is closed: "
                "PO is not ACCEPTED, a milestone has been posted, or the advance is paid"
            )
        line = self._find_line(part_number)
        if line.status is LineItemStatus.REMOVED:
            raise ValueError(
                f"line {part_number!r} is already REMOVED"
            )
        if has_downstream_artifact:
            raise LineHasDownstreamArtifactError(
                f"line {part_number!r} is referenced by an invoice or shipment "
                "and cannot be removed"
            )
        line.status = LineItemStatus.REMOVED
        self.updated_at = datetime.now(UTC)


def _to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
