from __future__ import annotations

import asyncpg


async def init_db(conn: asyncpg.Connection) -> None:
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
            buyer_name            TEXT NOT NULL DEFAULT '',
            buyer_country         TEXT NOT NULL DEFAULT '',
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
        CREATE TABLE IF NOT EXISTS products (
            id                      TEXT PRIMARY KEY,
            vendor_id               TEXT NOT NULL REFERENCES vendors(id),
            part_number             TEXT NOT NULL,
            description             TEXT NOT NULL DEFAULT '',
            requires_certification  INTEGER NOT NULL DEFAULT 0,
            created_at              TEXT NOT NULL,
            updated_at              TEXT NOT NULL,
            UNIQUE(vendor_id, part_number)
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

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id           TEXT PRIMARY KEY,
            username     TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            role         TEXT NOT NULL,
            status       TEXT NOT NULL,
            vendor_id    TEXT REFERENCES vendors(id),
            created_at   TEXT NOT NULL
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS webauthn_credentials (
            credential_id TEXT PRIMARY KEY,
            user_id       TEXT NOT NULL REFERENCES users(id),
            public_key    BYTEA NOT NULL,
            sign_count    INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT NOT NULL
        )
        """
    )

    await conn.execute("ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS marketplace TEXT")
    await conn.execute("ALTER TABLE line_items ADD COLUMN IF NOT EXISTS product_id TEXT REFERENCES products(id)")
    await conn.execute("ALTER TABLE vendors ADD COLUMN IF NOT EXISTS address TEXT NOT NULL DEFAULT ''")
    await conn.execute("ALTER TABLE vendors ADD COLUMN IF NOT EXISTS account_details TEXT NOT NULL DEFAULT ''")
    await conn.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS manufacturing_address TEXT NOT NULL DEFAULT ''")

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            id              TEXT PRIMARY KEY,
            entity_type     TEXT NOT NULL,
            entity_id       TEXT NOT NULL,
            file_type       TEXT NOT NULL DEFAULT '',
            original_name   TEXT NOT NULL,
            stored_path     TEXT NOT NULL,
            content_type    TEXT NOT NULL,
            size_bytes      INTEGER NOT NULL,
            uploaded_at     TEXT NOT NULL
        )
        """
    )

    await conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_files_entity
        ON files (entity_type, entity_id)
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS qualification_types (
            id                    TEXT PRIMARY KEY,
            name                  TEXT UNIQUE NOT NULL,
            description           TEXT NOT NULL DEFAULT '',
            target_market         TEXT NOT NULL,
            applies_to_category   TEXT NOT NULL DEFAULT '',
            created_at            TEXT NOT NULL
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS product_qualifications (
            product_id            TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            qualification_type_id TEXT NOT NULL REFERENCES qualification_types(id),
            PRIMARY KEY (product_id, qualification_type_id)
        )
        """
    )

    # Migration: products with requires_certification=1 get a QUALITY_CERTIFICATE qualification
    cert_exists = await conn.fetchval(
        "SELECT COUNT(*) FROM qualification_types WHERE name = 'QUALITY_CERTIFICATE'"
    )
    if (cert_exists or 0) == 0:
        from datetime import UTC, datetime
        from uuid import uuid4
        cert_id = str(uuid4())
        now = datetime.now(UTC).isoformat()
        await conn.execute(
            """
            INSERT INTO qualification_types (id, name, description, target_market, applies_to_category, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (name) DO NOTHING
            """,
            cert_id, "QUALITY_CERTIFICATE", "General quality certificate requirement", "ALL", "", now,
        )

    await conn.execute(
        """
        INSERT INTO product_qualifications (product_id, qualification_type_id)
        SELECT p.id, qt.id
        FROM products p
        JOIN qualification_types qt ON qt.name = 'QUALITY_CERTIFICATE'
        WHERE p.requires_certification = 1
        ON CONFLICT DO NOTHING
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS packaging_specs (
            id                TEXT PRIMARY KEY,
            product_id        TEXT NOT NULL REFERENCES products(id),
            marketplace       TEXT NOT NULL,
            spec_name         TEXT NOT NULL,
            description       TEXT NOT NULL DEFAULT '',
            requirements_text TEXT NOT NULL DEFAULT '',
            status            TEXT NOT NULL DEFAULT 'PENDING',
            created_at        TEXT NOT NULL,
            updated_at        TEXT NOT NULL,
            UNIQUE(product_id, marketplace, spec_name)
        )
        """
    )

    await conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_packaging_specs_product
        ON packaging_specs (product_id)
        """
    )
