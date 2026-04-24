from __future__ import annotations

import asyncio
import os
import random
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import asyncpg

from src.db import DEFAULT_DATABASE_URL
from src.domain.activity import ActivityEvent, EntityType, NotificationCategory, TargetRole
from src.domain.certificate import CertificateStatus
from src.domain.invoice import InvoiceStatus
from src.domain.milestone import ProductionMilestone
from src.domain.purchase_order import LineItemStatus, POStatus, POType
from src.domain.shipment import ShipmentStatus
from src.domain.user import UserRole, UserStatus
from src.domain.vendor import VendorStatus, VendorType
from src.schema import init_db

# Deterministic variety: fixture data should look the same across dev machines.
random.seed(1729)

_NOW = datetime.now(UTC)

VALID_MARKETPLACES: tuple[str, ...] = ("AMZ", "3PL_1", "3PL_2", "3PL_3")


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _offset(days: int) -> str:
    return _iso(_NOW + timedelta(days=days))


def _make_users(vendor_ids: list[str]) -> list[dict[str, object]]:
    # Five users covering every UserRole, with vendor_id only on the VENDOR row.
    created = _offset(-30)
    rows: list[dict[str, object]] = [
        {
            "id": str(uuid4()),
            "username": "alice",
            "display_name": "Alice Admin",
            "role": UserRole.ADMIN.value,
            "status": UserStatus.ACTIVE.value,
            "vendor_id": None,
            "email": "alice@example.com",
            "created_at": created,
        },
        {
            "id": str(uuid4()),
            "username": "bob",
            "display_name": "Bob Procurement",
            "role": UserRole.PROCUREMENT_MANAGER.value,
            "status": UserStatus.ACTIVE.value,
            "vendor_id": None,
            "email": "bob@example.com",
            "created_at": created,
        },
        {
            "id": str(uuid4()),
            "username": "carol",
            "display_name": "Carol SM",
            "role": UserRole.SM.value,
            "status": UserStatus.ACTIVE.value,
            "vendor_id": None,
            "email": "carol@example.com",
            "created_at": created,
        },
        {
            "id": str(uuid4()),
            "username": "dave",
            "display_name": "Dave Vendor",
            "role": UserRole.VENDOR.value,
            "status": UserStatus.ACTIVE.value,
            "vendor_id": vendor_ids[0],
            "email": "dave@example.com",
            "created_at": created,
        },
        {
            "id": str(uuid4()),
            "username": "erin",
            "display_name": "Erin Quality",
            "role": UserRole.QUALITY_LAB.value,
            "status": UserStatus.ACTIVE.value,
            "vendor_id": None,
            "email": "erin@example.com",
            "created_at": created,
        },
        {
            "id": str(uuid4()),
            "username": "frank",
            "display_name": "Frank Freight",
            "role": UserRole.FREIGHT_MANAGER.value,
            "status": UserStatus.ACTIVE.value,
            "vendor_id": None,
            "email": "frank@example.com",
            "created_at": created,
        },
    ]
    return rows


_VENDOR_FIXTURES: tuple[tuple[str, str, VendorType], ...] = (
    ("Shenzhen Precision Works", "CN", VendorType.PROCUREMENT),
    ("Mumbai Metal Forge", "IN", VendorType.PROCUREMENT),
    ("Hanoi Plastics Co", "VN", VendorType.PROCUREMENT),
    ("Chicago OpEx Supplies", "US", VendorType.OPEX),
    ("Hamburg Freight Lines", "DE", VendorType.FREIGHT),
    ("Sao Paulo Misc Trading", "BR", VendorType.MISCELLANEOUS),
)


def _make_vendors() -> list[dict[str, object]]:
    created = _offset(-45)
    rows: list[dict[str, object]] = []
    for name, country, vtype in _VENDOR_FIXTURES:
        rows.append(
            {
                "id": str(uuid4()),
                "name": name,
                "country": country,
                "status": VendorStatus.ACTIVE.value,
                "vendor_type": vtype.value,
                "address": f"{name}, {country}",
                "account_details": f"Bank: demo | A/C: {random.randint(10000000, 99999999)}",
                "created_at": created,
                "updated_at": created,
            }
        )
    return rows


def _make_products(vendors: list[dict[str, object]]) -> list[dict[str, object]]:
    # Two products per vendor; every third product requires certification.
    created = _offset(-40)
    rows: list[dict[str, object]] = []
    idx = 0
    for vendor in vendors:
        for n in (1, 2):
            part_number = f"PN-{vendor['country']}-{idx:03d}"
            requires_cert = 1 if idx % 3 == 0 else 0
            rows.append(
                {
                    "id": str(uuid4()),
                    "vendor_id": vendor["id"],
                    "part_number": part_number,
                    "description": f"{vendor['name']} component {n}",
                    "requires_certification": requires_cert,
                    "manufacturing_address": f"Plant {n}, {vendor['country']}",
                    "created_at": created,
                    "updated_at": created,
                }
            )
            idx += 1
    return rows


_PO_STATUS_CYCLE: tuple[POStatus, ...] = (
    POStatus.DRAFT,
    POStatus.PENDING,
    POStatus.ACCEPTED,
    POStatus.REJECTED,
    POStatus.REVISED,
    POStatus.MODIFIED,
)

_PAYMENT_TERMS_CYCLE: tuple[str, ...] = ("NET30", "NET60", "ADV", "50_PCT_ADVANCE_50_PCT_BL", "LC", "TT")
_INCOTERM_CYCLE: tuple[str, ...] = ("FOB", "CIF", "DAP", "EXW", "DDP")
_CURRENCY_CYCLE: tuple[str, ...] = ("USD", "EUR", "CNY", "INR")
_PORT_CYCLE: tuple[tuple[str, str], ...] = (
    ("CNSHA", "USLAX"),
    ("INNSA", "NLRTM"),
    ("VNSGN", "USLGB"),
    ("DEHAM", "USNYC"),
    ("BRSSZ", "USSAV"),
)


def _make_purchase_orders(
    vendors: list[dict[str, object]],
) -> list[dict[str, object]]:
    # 18 POs spread across vendors and every POStatus value.
    rows: list[dict[str, object]] = []
    for i in range(18):
        vendor = vendors[i % len(vendors)]
        # Stagger status per vendor round so each vendor ends up with distinct statuses
        # across its 3 POs instead of all landing on the same status (vendor_idx == status_idx).
        status = _PO_STATUS_CYCLE[(i + i // len(vendors)) % len(_PO_STATUS_CYCLE)]
        po_type = POType.OPEX if vendor["vendor_type"] == VendorType.OPEX.value else POType.PROCUREMENT
        payment_terms = _PAYMENT_TERMS_CYCLE[i % len(_PAYMENT_TERMS_CYCLE)]
        incoterm = _INCOTERM_CYCLE[i % len(_INCOTERM_CYCLE)]
        currency = _CURRENCY_CYCLE[i % len(_CURRENCY_CYCLE)]
        pol, pod = _PORT_CYCLE[i % len(_PORT_CYCLE)]
        issued = _offset(-90 + i * 5)
        required = _offset(-40 + i * 7)
        created = issued
        # Advance-required, ACCEPTED POs get advance_paid_at so production can flow.
        has_advance = payment_terms in ("ADV", "CIA", "50_PCT_ADVANCE_50_PCT_BL", "100_PCT_ADVANCE")
        advance_paid_at = issued if (status is POStatus.ACCEPTED and has_advance) else None
        rows.append(
            {
                "id": str(uuid4()),
                "po_number": f"PO-2026-{1000 + i:04d}",
                "status": status.value,
                "vendor_id": vendor["id"],
                "po_type": po_type.value,
                "ship_to_address": "1 Warehouse Way, Long Beach, CA 90802",
                "payment_terms": payment_terms,
                "currency": currency,
                "issued_date": issued,
                "required_delivery_date": required,
                "terms_and_conditions": "Standard T&Cs apply.",
                "incoterm": incoterm,
                "port_of_loading": pol,
                "port_of_discharge": pod,
                "country_of_origin": vendor["country"],
                "country_of_destination": "US",
                "buyer_name": "Turbo Tonic Inc.",
                "buyer_country": "US",
                "marketplace": VALID_MARKETPLACES[i % len(VALID_MARKETPLACES)],
                "round_count": 1 if status is POStatus.MODIFIED else 0,
                "last_actor_role": (UserRole.VENDOR.value if status is POStatus.MODIFIED else None),
                "advance_paid_at": advance_paid_at,
                "created_at": created,
                "updated_at": created,
            }
        )
    return rows


def _line_status_for(po_status: str, idx: int) -> str:
    # Line statuses follow the PO: ACCEPTED POs have ACCEPTED lines; draft/pending
    # keep PENDING; one REMOVED line sprinkled in to exercise the filter path.
    if po_status == POStatus.ACCEPTED.value:
        return LineItemStatus.ACCEPTED.value
    if idx == 2:
        return LineItemStatus.REMOVED.value
    return LineItemStatus.PENDING.value


def _make_line_items(
    pos: list[dict[str, object]],
    products: list[dict[str, object]],
) -> list[dict[str, object]]:
    # 2-4 lines per PO; link product_id when a product matches the PO's vendor.
    rows: list[dict[str, object]] = []
    for i, po in enumerate(pos):
        vendor_products = [p for p in products if p["vendor_id"] == po["vendor_id"]]
        line_count = 2 + (i % 3)
        for j in range(line_count):
            product = vendor_products[j % len(vendor_products)] if vendor_products else None
            part_number = str(product["part_number"]) if product else f"PART-{i:02d}-{j}"
            rows.append(
                {
                    "id": str(uuid4()),
                    "po_id": po["id"],
                    "part_number": part_number,
                    "description": f"Line {j + 1} of {po['po_number']}",
                    "quantity": 10 * (j + 1) + i,
                    "uom": "EA",
                    "unit_price": f"{12.50 + j * 3.25:.2f}",
                    "hs_code": "8471.30.0100",
                    "country_of_origin": po["country_of_origin"],
                    "sort_order": j,
                    "product_id": product["id"] if product else None,
                    "status": _line_status_for(str(po["status"]), j),
                    "required_delivery_date": None,
                }
            )
    return rows


def _make_shipments(pos: list[dict[str, object]]) -> list[dict[str, object]]:
    # Pick six ACCEPTED POs; if fewer than six ACCEPTED, fall back to the first six.
    accepted = [p for p in pos if p["status"] == POStatus.ACCEPTED.value]
    targets = (accepted + pos)[:6]
    statuses = (
        ShipmentStatus.DRAFT,
        ShipmentStatus.DOCUMENTS_PENDING,
        ShipmentStatus.READY_TO_SHIP,
    )
    rows: list[dict[str, object]] = []
    for i, po in enumerate(targets):
        ship_count = 1 + (i % 2)
        for s in range(ship_count):
            rows.append(
                {
                    "id": str(uuid4()),
                    "po_id": po["id"],
                    "shipment_number": f"SHP-2026-{i:03d}-{s}",
                    "marketplace": str(po["marketplace"]) if po["marketplace"] else VALID_MARKETPLACES[0],
                    "status": statuses[(i + s) % len(statuses)].value,
                    "created_at": _offset(-20 + i),
                    "updated_at": _offset(-5 + i),
                }
            )
    return rows


def _make_shipment_line_items(
    shipments: list[dict[str, object]],
    line_items: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for i, shipment in enumerate(shipments):
        po_lines = [
            li for li in line_items
            if li["po_id"] == shipment["po_id"] and li["status"] == LineItemStatus.ACCEPTED.value
        ]
        if not po_lines:
            po_lines = [li for li in line_items if li["po_id"] == shipment["po_id"]][:2]
        count = min(len(po_lines), 1 + (i % 3))
        for j, li in enumerate(po_lines[:count]):
            rows.append(
                {
                    "id": str(uuid4()),
                    "shipment_id": shipment["id"],
                    "part_number": li["part_number"],
                    "product_id": li.get("product_id"),
                    "description": li["description"],
                    "quantity": max(1, int(li["quantity"]) // 2),
                    "uom": li["uom"],
                    "sort_order": j,
                    "net_weight": "1.25",
                    "gross_weight": "1.40",
                    "package_count": 2,
                    "dimensions": "30x20x10cm",
                    "country_of_origin": li["country_of_origin"],
                }
            )
    return rows


def _make_invoices(pos: list[dict[str, object]]) -> list[dict[str, object]]:
    # Only ACCEPTED POs can invoice; fall back to all if fewer than ten ACCEPTED exist.
    eligible = [p for p in pos if p["status"] == POStatus.ACCEPTED.value]
    if len(eligible) < 10:
        eligible = eligible + [p for p in pos if p not in eligible]
    statuses = list(InvoiceStatus)
    rows: list[dict[str, object]] = []
    for i in range(10):
        po = eligible[i % len(eligible)]
        status = statuses[i % len(statuses)]
        dispute_reason = "Quantity mismatch on line 2" if status is InvoiceStatus.DISPUTED else ""
        rows.append(
            {
                "id": str(uuid4()),
                "invoice_number": f"INV-2026-{2000 + i:04d}",
                "po_id": po["id"],
                "status": status.value,
                "payment_terms": po["payment_terms"],
                "currency": po["currency"],
                "dispute_reason": dispute_reason,
                "created_at": _offset(-15 + i),
                "updated_at": _offset(-5 + i),
            }
        )
    return rows


def _make_invoice_line_items(
    invoices: list[dict[str, object]],
    line_items: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for i, inv in enumerate(invoices):
        po_lines = [li for li in line_items if li["po_id"] == inv["po_id"]]
        count = max(1, min(len(po_lines), 1 + (i % 3)))
        for j, li in enumerate(po_lines[:count]):
            rows.append(
                {
                    "id": str(uuid4()),
                    "invoice_id": inv["id"],
                    "part_number": li["part_number"],
                    "description": li["description"],
                    "quantity": li["quantity"],
                    "uom": li["uom"],
                    "unit_price": li["unit_price"],
                    "sort_order": j,
                }
            )
    return rows


def _make_milestone_updates(pos: list[dict[str, object]]) -> list[dict[str, object]]:
    # A handful of ACCEPTED POs get a prefix of the milestone sequence.
    accepted = [p for p in pos if p["status"] == POStatus.ACCEPTED.value]
    milestone_list = list(ProductionMilestone)
    rows: list[dict[str, object]] = []
    for i, po in enumerate(accepted[:4]):
        count = 2 + (i % 3)
        for j, m in enumerate(milestone_list[:count]):
            rows.append(
                {
                    "id": str(uuid4()),
                    "po_id": po["id"],
                    "milestone": m.value,
                    "posted_at": _offset(-10 + i + j),
                }
            )
    return rows


async def _fetch_quality_cert_qt_id(conn: asyncpg.Connection) -> str:
    qt_id = await conn.fetchval(
        "SELECT id FROM qualification_types WHERE name = 'QUALITY_CERTIFICATE'"
    )
    if qt_id is None:
        raise RuntimeError("QUALITY_CERTIFICATE qualification_type missing; init_db should have seeded it")
    return str(qt_id)


def _make_certificates(
    products: list[dict[str, object]],
    qt_id: str,
) -> list[dict[str, object]]:
    cert_products = [p for p in products if p["requires_certification"] == 1][:5]
    statuses = (CertificateStatus.VALID, CertificateStatus.PENDING)
    rows: list[dict[str, object]] = []
    for i, product in enumerate(cert_products):
        issue = _NOW + timedelta(days=-60 + i * 5)
        expiry = issue + timedelta(days=365)
        rows.append(
            {
                "id": str(uuid4()),
                "product_id": product["id"],
                "qualification_type_id": qt_id,
                "cert_number": f"CERT-{i:04d}",
                "issuer": "Global Testing Authority",
                "testing_lab": "Lab 7",
                "test_date": _iso(issue - timedelta(days=10)),
                "issue_date": _iso(issue),
                "expiry_date": _iso(expiry),
                "target_market": "US",
                "document_id": None,
                "status": statuses[i % len(statuses)].value,
                "created_at": _iso(issue),
                "updated_at": _iso(issue),
            }
        )
    return rows


def _make_activity_log(pos: list[dict[str, object]]) -> list[dict[str, object]]:
    # Dashboard uses activity_log as its feed; variety here is what makes the
    # dev-server UI look populated. Covers every event type the Phase 4 dashboard
    # groups into its "recent activity" panel.
    events = (
        (ActivityEvent.PO_CREATED, NotificationCategory.LIVE, TargetRole.SM),
        (ActivityEvent.PO_SUBMITTED, NotificationCategory.ACTION_REQUIRED, TargetRole.VENDOR),
        (ActivityEvent.PO_ACCEPTED, NotificationCategory.LIVE, TargetRole.SM),
        (ActivityEvent.PO_MODIFIED, NotificationCategory.ACTION_REQUIRED, TargetRole.SM),
        (ActivityEvent.PO_REJECTED, NotificationCategory.LIVE, TargetRole.SM),
        (ActivityEvent.PO_REVISED, NotificationCategory.ACTION_REQUIRED, TargetRole.VENDOR),
        (ActivityEvent.PO_LINE_MODIFIED, NotificationCategory.ACTION_REQUIRED, TargetRole.SM),
        (ActivityEvent.PO_ADVANCE_PAID, NotificationCategory.LIVE, TargetRole.VENDOR),
        (ActivityEvent.INVOICE_CREATED, NotificationCategory.LIVE, TargetRole.SM),
        (ActivityEvent.INVOICE_SUBMITTED, NotificationCategory.ACTION_REQUIRED, TargetRole.SM),
        (ActivityEvent.INVOICE_APPROVED, NotificationCategory.LIVE, TargetRole.VENDOR),
        (ActivityEvent.INVOICE_PAID, NotificationCategory.LIVE, TargetRole.VENDOR),
        (ActivityEvent.INVOICE_DISPUTED, NotificationCategory.ACTION_REQUIRED, TargetRole.VENDOR),
        (ActivityEvent.MILESTONE_POSTED, NotificationCategory.LIVE, TargetRole.SM),
        (ActivityEvent.MILESTONE_OVERDUE, NotificationCategory.DELAYED, TargetRole.SM),
        (ActivityEvent.CERT_UPLOADED, NotificationCategory.LIVE, TargetRole.SM),
        (ActivityEvent.CERT_REQUESTED, NotificationCategory.ACTION_REQUIRED, TargetRole.VENDOR),
        (ActivityEvent.PACKAGING_COLLECTED, NotificationCategory.LIVE, TargetRole.SM),
        (ActivityEvent.DOCUMENT_UPLOADED, NotificationCategory.LIVE, TargetRole.SM),
    )
    rows: list[dict[str, object]] = []
    for i, (event, category, target) in enumerate(events):
        po = pos[i % len(pos)]
        rows.append(
            {
                "id": str(uuid4()),
                "entity_type": EntityType.PO.value,
                "entity_id": po["id"],
                "event": event.value,
                "category": category.value,
                "target_role": target.value if target is not None else None,
                "actor_id": None,
                "detail": f"{event.value} on {po['po_number']}",
                "read_at": None,
                "created_at": _offset(-14 + i),
            }
        )
    return rows


async def _insert(conn: asyncpg.Connection, sql: str, rows: list[dict[str, object]], columns: tuple[str, ...]) -> None:
    if not rows:
        return
    records = [tuple(row[col] for col in columns) for row in rows]
    await conn.executemany(sql, records)


async def seed(conn: asyncpg.Connection) -> None:
    existing = await conn.fetchval("SELECT COUNT(*) FROM users")
    if (existing or 0) > 0:
        print("seed: users exist, skipping")
        return

    vendors = _make_vendors()
    products = _make_products(vendors)
    users = _make_users([str(v["id"]) for v in vendors])
    pos = _make_purchase_orders(vendors)
    line_items = _make_line_items(pos, products)
    shipments = _make_shipments(pos)
    shipment_lines = _make_shipment_line_items(shipments, line_items)
    invoices = _make_invoices(pos)
    invoice_lines = _make_invoice_line_items(invoices, line_items)
    milestones = _make_milestone_updates(pos)
    activity = _make_activity_log(pos)

    async with conn.transaction():
        qt_id = await _fetch_quality_cert_qt_id(conn)
        certificates = _make_certificates(products, qt_id)

        await _insert(
            conn,
            """
            INSERT INTO vendors (id, name, country, status, vendor_type, address, account_details, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            vendors,
            ("id", "name", "country", "status", "vendor_type", "address", "account_details", "created_at", "updated_at"),
        )

        await _insert(
            conn,
            """
            INSERT INTO users (id, username, display_name, role, status, vendor_id, email, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            users,
            ("id", "username", "display_name", "role", "status", "vendor_id", "email", "created_at"),
        )

        await _insert(
            conn,
            """
            INSERT INTO products (id, vendor_id, part_number, description, requires_certification, manufacturing_address, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            products,
            ("id", "vendor_id", "part_number", "description", "requires_certification", "manufacturing_address", "created_at", "updated_at"),
        )

        # Link certified products to QUALITY_CERTIFICATE qualification type.
        cert_links = [
            {"product_id": p["id"], "qualification_type_id": qt_id}
            for p in products
            if p["requires_certification"] == 1
        ]
        await _insert(
            conn,
            """
            INSERT INTO product_qualifications (product_id, qualification_type_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            cert_links,
            ("product_id", "qualification_type_id"),
        )

        await _insert(
            conn,
            """
            INSERT INTO purchase_orders (
                id, po_number, status, vendor_id, po_type, ship_to_address, payment_terms,
                currency, issued_date, required_delivery_date, terms_and_conditions, incoterm,
                port_of_loading, port_of_discharge, country_of_origin, country_of_destination,
                buyer_name, buyer_country, marketplace, round_count, last_actor_role,
                advance_paid_at, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16,
                    $17, $18, $19, $20, $21, $22, $23, $24)
            """,
            pos,
            (
                "id", "po_number", "status", "vendor_id", "po_type", "ship_to_address",
                "payment_terms", "currency", "issued_date", "required_delivery_date",
                "terms_and_conditions", "incoterm", "port_of_loading", "port_of_discharge",
                "country_of_origin", "country_of_destination", "buyer_name", "buyer_country",
                "marketplace", "round_count", "last_actor_role", "advance_paid_at",
                "created_at", "updated_at",
            ),
        )

        await _insert(
            conn,
            """
            INSERT INTO line_items (
                id, po_id, part_number, description, quantity, uom, unit_price, hs_code,
                country_of_origin, sort_order, product_id, status, required_delivery_date
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """,
            line_items,
            (
                "id", "po_id", "part_number", "description", "quantity", "uom", "unit_price",
                "hs_code", "country_of_origin", "sort_order", "product_id", "status",
                "required_delivery_date",
            ),
        )

        await _insert(
            conn,
            """
            INSERT INTO shipments (id, po_id, shipment_number, marketplace, status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            shipments,
            ("id", "po_id", "shipment_number", "marketplace", "status", "created_at", "updated_at"),
        )

        await _insert(
            conn,
            """
            INSERT INTO shipment_line_items (
                id, shipment_id, part_number, product_id, description, quantity, uom, sort_order,
                net_weight, gross_weight, package_count, dimensions, country_of_origin
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """,
            shipment_lines,
            (
                "id", "shipment_id", "part_number", "product_id", "description", "quantity",
                "uom", "sort_order", "net_weight", "gross_weight", "package_count", "dimensions",
                "country_of_origin",
            ),
        )

        await _insert(
            conn,
            """
            INSERT INTO invoices (
                id, invoice_number, po_id, status, payment_terms, currency, dispute_reason,
                created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            invoices,
            (
                "id", "invoice_number", "po_id", "status", "payment_terms", "currency",
                "dispute_reason", "created_at", "updated_at",
            ),
        )

        await _insert(
            conn,
            """
            INSERT INTO invoice_line_items (
                id, invoice_id, part_number, description, quantity, uom, unit_price, sort_order
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            invoice_lines,
            ("id", "invoice_id", "part_number", "description", "quantity", "uom", "unit_price", "sort_order"),
        )

        await _insert(
            conn,
            """
            INSERT INTO milestone_updates (id, po_id, milestone, posted_at)
            VALUES ($1, $2, $3, $4)
            """,
            milestones,
            ("id", "po_id", "milestone", "posted_at"),
        )

        await _insert(
            conn,
            """
            INSERT INTO certificates (
                id, product_id, qualification_type_id, cert_number, issuer, testing_lab,
                test_date, issue_date, expiry_date, target_market, document_id, status,
                created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
            certificates,
            (
                "id", "product_id", "qualification_type_id", "cert_number", "issuer",
                "testing_lab", "test_date", "issue_date", "expiry_date", "target_market",
                "document_id", "status", "created_at", "updated_at",
            ),
        )

        await _insert(
            conn,
            """
            INSERT INTO activity_log (
                id, entity_type, entity_id, event, category, target_role, actor_id, detail,
                read_at, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            activity,
            (
                "id", "entity_type", "entity_id", "event", "category", "target_role",
                "actor_id", "detail", "read_at", "created_at",
            ),
        )

    print(
        "seed: inserted "
        f"{len(vendors)} vendors, {len(users)} users, {len(products)} products, "
        f"{len(pos)} POs, {len(line_items)} line items, {len(shipments)} shipments, "
        f"{len(shipment_lines)} shipment lines, {len(invoices)} invoices, "
        f"{len(invoice_lines)} invoice lines, {len(milestones)} milestones, "
        f"{len(certificates)} certificates, {len(activity)} activity entries"
    )


async def main() -> None:
    url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    conn = await asyncpg.connect(url)
    try:
        await init_db(conn)
        await seed(conn)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
