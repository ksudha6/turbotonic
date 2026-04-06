from __future__ import annotations

import aiosqlite


async def _migrate_vendors(conn: aiosqlite.Connection) -> None:
    """Create Vendor records from existing free-text vendor_id values on POs."""
    # Only run if vendors table is empty
    async with conn.execute("SELECT COUNT(*) FROM vendors") as cursor:
        row = await cursor.fetchone()
        if row[0] > 0:
            return

    # Get distinct vendor_id values from existing POs
    async with conn.execute(
        "SELECT DISTINCT vendor_id FROM purchase_orders"
    ) as cursor:
        rows = await cursor.fetchall()

    if not rows:
        return

    from datetime import UTC, datetime
    from uuid import uuid4

    now = datetime.now(UTC).isoformat()

    for (old_vendor_id,) in rows:
        new_id = str(uuid4())
        # Create a vendor record using the old vendor_id as the name; type defaults to PROCUREMENT
        await conn.execute(
            """
            INSERT INTO vendors (id, name, country, status, vendor_type, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (new_id, old_vendor_id, "", "ACTIVE", "PROCUREMENT", now, now),
        )
        # Update all POs that referenced this vendor_id string to use the new UUID
        await conn.execute(
            "UPDATE purchase_orders SET vendor_id = ? WHERE vendor_id = ?",
            (new_id, old_vendor_id),
        )

    await conn.commit()


async def init_db(conn: aiosqlite.Connection) -> None:
    # Foreign key enforcement is per-connection in SQLite.
    await conn.execute("PRAGMA foreign_keys = ON")

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id                    TEXT PRIMARY KEY,
            po_number             TEXT UNIQUE NOT NULL,
            status                TEXT NOT NULL,
            vendor_id             TEXT NOT NULL,
            po_type               TEXT NOT NULL,
            ship_to_address       TEXT,
            payment_terms         TEXT,
            currency              TEXT NOT NULL,
            issued_date           TEXT NOT NULL,
            required_delivery_date TEXT NOT NULL,
            terms_and_conditions  TEXT,
            incoterm              TEXT,
            port_of_loading       TEXT,
            port_of_discharge     TEXT,
            country_of_origin     TEXT,
            country_of_destination TEXT,
            created_at            TEXT NOT NULL,
            updated_at            TEXT NOT NULL
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS line_items (
            id               TEXT PRIMARY KEY,
            po_id            TEXT NOT NULL REFERENCES purchase_orders(id),
            part_number      TEXT NOT NULL,
            description      TEXT,
            quantity         INTEGER NOT NULL,
            uom              TEXT NOT NULL,
            unit_price       TEXT NOT NULL,
            hs_code          TEXT,
            country_of_origin TEXT,
            sort_order       INTEGER NOT NULL
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rejection_history (
            id          TEXT PRIMARY KEY,
            po_id       TEXT NOT NULL REFERENCES purchase_orders(id),
            comment     TEXT NOT NULL,
            rejected_at TEXT NOT NULL
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vendors (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            country     TEXT NOT NULL,
            status      TEXT NOT NULL,
            vendor_type TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS invoices (
            id              TEXT PRIMARY KEY,
            invoice_number  TEXT UNIQUE NOT NULL,
            po_id           TEXT NOT NULL REFERENCES purchase_orders(id),
            status          TEXT NOT NULL,
            payment_terms   TEXT NOT NULL,
            currency        TEXT NOT NULL,
            dispute_reason  TEXT NOT NULL DEFAULT '',
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS invoice_line_items (
            id              TEXT PRIMARY KEY,
            invoice_id      TEXT NOT NULL REFERENCES invoices(id),
            part_number     TEXT NOT NULL,
            description     TEXT,
            quantity        INTEGER NOT NULL,
            uom             TEXT NOT NULL,
            unit_price      TEXT NOT NULL,
            sort_order      INTEGER NOT NULL
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS milestone_updates (
            id         TEXT PRIMARY KEY,
            po_id      TEXT NOT NULL REFERENCES purchase_orders(id),
            milestone  TEXT NOT NULL,
            posted_at  TEXT NOT NULL
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS activity_log (
            id          TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            entity_id   TEXT NOT NULL,
            event       TEXT NOT NULL,
            category    TEXT NOT NULL,
            target_role TEXT,
            actor_id    TEXT,
            detail      TEXT,
            read_at     TEXT,
            created_at  TEXT NOT NULL
        )
        """
    )

    # Add buyer columns to existing purchase_orders tables.
    for col in ("buyer_name", "buyer_country"):
        try:
            await conn.execute(
                f"ALTER TABLE purchase_orders ADD COLUMN {col} TEXT NOT NULL DEFAULT ''"
            )
        except Exception as exc:
            if "duplicate column name" not in str(exc).lower():
                raise

    # Add vendor_type to vendors table.
    for col, default in [("vendor_type", "PROCUREMENT")]:
        try:
            await conn.execute(
                f"ALTER TABLE vendors ADD COLUMN {col} TEXT NOT NULL DEFAULT '{default}'"
            )
        except Exception as exc:
            if "duplicate column name" not in str(exc).lower():
                raise

    # Add po_type to purchase_orders table.
    for col, default in [("po_type", "PROCUREMENT")]:
        try:
            await conn.execute(
                f"ALTER TABLE purchase_orders ADD COLUMN {col} TEXT NOT NULL DEFAULT '{default}'"
            )
        except Exception as exc:
            if "duplicate column name" not in str(exc).lower():
                raise

    await conn.commit()

    await _migrate_vendors(conn)
