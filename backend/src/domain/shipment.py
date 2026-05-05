from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4


class ShipmentStatus(Enum):
    DRAFT = "DRAFT"
    DOCUMENTS_PENDING = "DOCUMENTS_PENDING"
    READY_TO_SHIP = "READY_TO_SHIP"
    # Iter 074: FM has confirmed carrier + booking reference + pickup date.
    BOOKED = "BOOKED"
    # Iter 074: shipment has been picked up / dispatched.
    SHIPPED = "SHIPPED"


@dataclass
class ShipmentLineItem:
    part_number: str
    product_id: str | None
    description: str
    quantity: int
    uom: str
    net_weight: Decimal | None = field(default=None)
    gross_weight: Decimal | None = field(default=None)
    package_count: int | None = field(default=None)
    dimensions: str | None = field(default=None)
    country_of_origin: str | None = field(default=None)

    def __post_init__(self) -> None:
        if not self.part_number or not self.part_number.strip():
            raise ValueError("part_number must not be empty or whitespace-only")
        if self.quantity <= 0:
            raise ValueError("quantity must be greater than 0")


class Shipment:
    # id and shipment_number are immutable identifiers; created_at is immutable
    def __init__(
        self,
        *,
        id: str,
        po_id: str,
        shipment_number: str,
        marketplace: str,
        status: ShipmentStatus,
        line_items: list[ShipmentLineItem],
        created_at: datetime,
        updated_at: datetime,
        carrier: str | None = None,
        booking_reference: str | None = None,
        pickup_date: date | None = None,
        shipped_at: datetime | None = None,
        # Iter 106: transport details (vessel + voyage) — set post-booking.
        vessel_name: str | None = None,
        voyage_number: str | None = None,
        # Iter 106: declaration details — set via declare().
        signatory_name: str | None = None,
        signatory_title: str | None = None,
        declared_at: datetime | None = None,
        # Iter 110: logistics details — pallet count on PL header; export reason on CI.
        pallet_count: int | None = None,
        export_reason: str = "",
    ) -> None:
        self._id = id
        self.po_id = po_id
        self._shipment_number = shipment_number
        self.marketplace = marketplace
        self.status = status
        self.line_items = line_items
        self._created_at = created_at
        self.updated_at = updated_at
        self.carrier = carrier
        self.booking_reference = booking_reference
        self.pickup_date = pickup_date
        self.shipped_at = shipped_at
        self.vessel_name = vessel_name
        self.voyage_number = voyage_number
        self.signatory_name = signatory_name
        self.signatory_title = signatory_title
        self.declared_at = declared_at
        self.pallet_count = pallet_count
        self.export_reason = export_reason

    @property
    def id(self) -> str:
        return self._id

    @property
    def shipment_number(self) -> str:
        return self._shipment_number

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @classmethod
    def create(
        cls,
        *,
        po_id: str,
        marketplace: str,
        line_items: list[ShipmentLineItem],
    ) -> Shipment:
        if not line_items:
            raise ValueError("at least one line item is required")
        now = datetime.now(UTC)
        date_str = now.strftime("%Y%m%d")
        hex_suffix = secrets.token_hex(2).upper()
        shipment_number = f"SHP-{date_str}-{hex_suffix}"
        return cls(
            id=str(uuid4()),
            po_id=po_id,
            shipment_number=shipment_number,
            marketplace=marketplace,
            status=ShipmentStatus.DRAFT,
            line_items=list(line_items),
            created_at=now,
            updated_at=now,
        )

    def submit_for_documents(self) -> None:
        # DRAFT is the only state from which a shipment enters document collection
        if self.status is not ShipmentStatus.DRAFT:
            raise ValueError(
                f"submit_for_documents requires DRAFT status; current status is {self.status.value}"
            )
        self.status = ShipmentStatus.DOCUMENTS_PENDING
        self.updated_at = datetime.now(UTC)

    def mark_ready(self) -> None:
        # Document collection must complete before a shipment is ready to ship
        if self.status is not ShipmentStatus.DOCUMENTS_PENDING:
            raise ValueError(
                f"mark_ready requires DOCUMENTS_PENDING status; current status is {self.status.value}"
            )
        self.status = ShipmentStatus.READY_TO_SHIP
        self.updated_at = datetime.now(UTC)

    def book_shipment(
        self,
        *,
        carrier: str,
        booking_reference: str,
        pickup_date: date,
    ) -> None:
        # FM records carrier + booking reference + pickup date. All three required.
        if self.status is not ShipmentStatus.READY_TO_SHIP:
            raise ValueError(
                f"book_shipment requires READY_TO_SHIP status; current status is {self.status.value}"
            )
        if not carrier or not carrier.strip():
            raise ValueError("carrier must not be empty or whitespace-only")
        if not booking_reference or not booking_reference.strip():
            raise ValueError("booking_reference must not be empty or whitespace-only")
        self.carrier = carrier.strip()
        self.booking_reference = booking_reference.strip()
        self.pickup_date = pickup_date
        self.status = ShipmentStatus.BOOKED
        self.updated_at = datetime.now(UTC)

    def mark_shipped(self) -> None:
        # FM marks shipment dispatched after carrier picks up.
        if self.status is not ShipmentStatus.BOOKED:
            raise ValueError(
                f"mark_shipped requires BOOKED status; current status is {self.status.value}"
            )
        now = datetime.now(UTC)
        self.status = ShipmentStatus.SHIPPED
        self.shipped_at = now
        self.updated_at = now

    def set_transport(
        self,
        *,
        vessel_name: str | None,
        voyage_number: str | None,
    ) -> None:
        # Transport details (vessel + voyage) are recorded after booking is confirmed.
        # Both fields are optional but must not be whitespace-only if supplied.
        if self.status not in (
            ShipmentStatus.BOOKED,
            ShipmentStatus.SHIPPED,
        ):
            raise ValueError(
                f"set_transport requires BOOKED or SHIPPED status; current status is {self.status.value}"
            )
        if vessel_name is not None and not vessel_name.strip():
            raise ValueError("vessel_name must not be whitespace-only")
        if voyage_number is not None and not voyage_number.strip():
            raise ValueError("voyage_number must not be whitespace-only")
        self.vessel_name = vessel_name.strip() if vessel_name is not None else None
        self.voyage_number = voyage_number.strip() if voyage_number is not None else None
        self.updated_at = datetime.now(UTC)

    def declare(
        self,
        *,
        signatory_name: str,
        signatory_title: str,
    ) -> None:
        # Signatory name and title are required for a customs declaration.
        # Allowed in any post-DRAFT status so SM can declare at any stage after submission.
        if self.status is ShipmentStatus.DRAFT:
            raise ValueError(
                "declare requires post-DRAFT status; current status is DRAFT"
            )
        if not signatory_name or not signatory_name.strip():
            raise ValueError("signatory_name must not be empty or whitespace-only")
        if not signatory_title or not signatory_title.strip():
            raise ValueError("signatory_title must not be empty or whitespace-only")
        now = datetime.now(UTC)
        self.signatory_name = signatory_name.strip()
        self.signatory_title = signatory_title.strip()
        self.declared_at = now
        self.updated_at = now

    def set_logistics(
        self,
        *,
        pallet_count: int | None,
        export_reason: str,
    ) -> None:
        # pallet_count is optional (nullable); export_reason defaults to "" when not yet set.
        # Both fields are informational and can be set in any status after creation.
        if pallet_count is not None and pallet_count < 0:
            raise ValueError("pallet_count must not be negative")
        if export_reason != export_reason.strip():
            export_reason = export_reason.strip()
        self.pallet_count = pallet_count
        self.export_reason = export_reason
        self.updated_at = datetime.now(UTC)

    def update_line_items(self, updates: list[dict[str, object]]) -> None:
        # Only DRAFT and DOCUMENTS_PENDING shipments accept line item edits
        if self.status is not ShipmentStatus.DRAFT and self.status is not ShipmentStatus.DOCUMENTS_PENDING:
            raise ValueError(
                f"update_line_items is not allowed in {self.status.value} status"
            )
        index: dict[str, ShipmentLineItem] = {li.part_number: li for li in self.line_items}
        for upd in updates:
            pn = str(upd["part_number"])
            if pn not in index:
                raise ValueError(f"part_number '{pn}' not found in shipment")
            item = index[pn]
            item.net_weight = upd.get("net_weight")  # type: ignore[assignment]
            item.gross_weight = upd.get("gross_weight")  # type: ignore[assignment]
            item.package_count = upd.get("package_count")  # type: ignore[assignment]
            item.dimensions = upd.get("dimensions")  # type: ignore[assignment]
            item.country_of_origin = upd.get("country_of_origin")  # type: ignore[assignment]
        self.updated_at = datetime.now(UTC)


def validate_shipment_quantities(
    po_line_items: list[dict[str, object]],
    existing_shipments: list[Shipment],
    new_line_items: list[ShipmentLineItem],
) -> None:
    """Check that new shipment quantities do not exceed accepted PO quantities.

    Only ACCEPTED PO line items are eligible. Raises ValueError for any
    part_number that is REMOVED, PENDING, MODIFIED_BY_*, not found, or would
    exceed accepted qty.
    """
    accepted: dict[str, int] = {}
    all_statuses: dict[str, str] = {}
    for item in po_line_items:
        pn = str(item["part_number"])
        status = str(item["status"])
        all_statuses[pn] = status
        if status == "ACCEPTED":
            accepted[pn] = int(item["quantity"])  # type: ignore[arg-type]

    # Cumulative shipped quantities across all existing shipments
    shipped: dict[str, int] = {}
    for shipment in existing_shipments:
        for li in shipment.line_items:
            shipped[li.part_number] = shipped.get(li.part_number, 0) + li.quantity

    for li in new_line_items:
        pn = li.part_number
        if pn not in all_statuses:
            raise ValueError(
                f"part_number '{pn}' not found in PO line items"
            )
        if all_statuses[pn] != "ACCEPTED":
            raise ValueError(
                f"part_number '{pn}' has status {all_statuses[pn]}; only ACCEPTED line items are eligible for shipment"
            )
        po_qty = accepted[pn]
        already_shipped = shipped.get(pn, 0)
        if already_shipped + li.quantity > po_qty:
            remaining = po_qty - already_shipped
            raise ValueError(
                f"part_number '{pn}': requested {li.quantity}, but only {remaining} remaining "
                f"(PO accepted qty {po_qty}, already shipped {already_shipped})"
            )
