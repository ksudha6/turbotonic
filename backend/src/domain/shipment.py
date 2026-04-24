from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4


class ShipmentStatus(Enum):
    DRAFT = "DRAFT"
    DOCUMENTS_PENDING = "DOCUMENTS_PENDING"
    READY_TO_SHIP = "READY_TO_SHIP"


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
    ) -> None:
        self._id = id
        self.po_id = po_id
        self._shipment_number = shipment_number
        self.marketplace = marketplace
        self.status = status
        self.line_items = line_items
        self._created_at = created_at
        self.updated_at = updated_at

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

    def update_line_items(self, updates: list[dict[str, object]]) -> None:
        # Only DRAFT and DOCUMENTS_PENDING shipments accept line item edits
        if self.status is ShipmentStatus.READY_TO_SHIP:
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
