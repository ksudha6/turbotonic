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

    # Iter 060: optional email address per user. Nullable to preserve existing
    # rows; recipient resolution skips users with NULL or empty email.
    await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT")

    await conn.execute("ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS marketplace TEXT")
    await conn.execute("ALTER TABLE line_items ADD COLUMN IF NOT EXISTS product_id TEXT REFERENCES products(id)")
    await conn.execute("ALTER TABLE line_items ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'PENDING'")
    # Backfill: line items on ACCEPTED POs receive ACCEPTED status; all others keep PENDING
    await conn.execute(
        """
        UPDATE line_items
        SET status = 'ACCEPTED'
        WHERE po_id IN (SELECT id FROM purchase_orders WHERE status = 'ACCEPTED')
        """
    )
    # Iter 056: rename the old binary REJECTED line-item status to REMOVED; REJECTED
    # is no longer a valid line-item status — line-level removal subsumes it.
    await conn.execute("UPDATE line_items SET status = 'REMOVED' WHERE status = 'REJECTED'")
    # Iter 056: per-line optional delivery date override; null means inherit from PO
    await conn.execute("ALTER TABLE line_items ADD COLUMN IF NOT EXISTS required_delivery_date TEXT")
    # Iter 056: PO-scoped negotiation round counter (0..2) and last-actor marker.
    # round_count increments on submit_response; last_actor_role records who spoke last.
    await conn.execute(
        "ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS round_count INTEGER NOT NULL DEFAULT 0"
    )
    await conn.execute("ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS last_actor_role TEXT")
    # Enforce the round cap at the database boundary; drop-and-recreate to stay idempotent.
    await conn.execute(
        "ALTER TABLE purchase_orders DROP CONSTRAINT IF EXISTS purchase_orders_round_count_check"
    )
    await conn.execute(
        "ALTER TABLE purchase_orders ADD CONSTRAINT purchase_orders_round_count_check CHECK (round_count BETWEEN 0 AND 2)"
    )

    # Iter 059: advance-payment gate. Nullable; set by /mark-advance-paid.
    # `requires_advance` is derived from payment_terms metadata, not stored.
    await conn.execute(
        "ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS advance_paid_at TEXT"
    )
    # Backfill: ACCEPTED POs whose payment_terms carry an advance flag are treated
    # as implicitly paid at creation so live production is not retroactively gated.
    # Codes that set has_advance=True in PAYMENT_TERMS_METADATA.
    await conn.execute(
        """
        UPDATE purchase_orders
        SET advance_paid_at = created_at
        WHERE status = 'ACCEPTED'
          AND advance_paid_at IS NULL
          AND payment_terms IN ('ADV', 'CIA', '50_PCT_ADVANCE_50_PCT_BL', '100_PCT_ADVANCE')
        """
    )

    # Iter 056: one row per field edit; the negotiation audit trail.
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS line_edit_history (
            id              TEXT PRIMARY KEY,
            po_id           TEXT NOT NULL REFERENCES purchase_orders(id),
            line_item_id    TEXT,
            part_number     TEXT NOT NULL,
            round           INTEGER NOT NULL,
            actor_role      TEXT NOT NULL,
            field           TEXT NOT NULL,
            old_value       TEXT,
            new_value       TEXT,
            edited_at       TEXT NOT NULL
        )
        """
    )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_line_edit_history_po_round_line ON line_edit_history (po_id, round, line_item_id)"
    )
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

    await conn.execute("ALTER TABLE packaging_specs ADD COLUMN IF NOT EXISTS document_id TEXT")

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS certificates (
            id                      TEXT PRIMARY KEY,
            product_id              TEXT NOT NULL REFERENCES products(id),
            qualification_type_id   TEXT NOT NULL REFERENCES qualification_types(id),
            cert_number             TEXT NOT NULL,
            issuer                  TEXT NOT NULL,
            testing_lab             TEXT NOT NULL DEFAULT '',
            test_date               TEXT,
            issue_date              TEXT NOT NULL,
            expiry_date             TEXT,
            target_market           TEXT NOT NULL,
            document_id             TEXT,
            status                  TEXT NOT NULL,
            created_at              TEXT NOT NULL,
            updated_at              TEXT NOT NULL
        )
        """
    )

    await conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_certificates_product
        ON certificates (product_id)
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS shipments (
            id               TEXT PRIMARY KEY,
            po_id            TEXT NOT NULL REFERENCES purchase_orders(id),
            shipment_number  TEXT UNIQUE NOT NULL,
            marketplace      TEXT NOT NULL,
            status           TEXT NOT NULL DEFAULT 'DRAFT',
            created_at       TEXT NOT NULL,
            updated_at       TEXT NOT NULL
        )
        """
    )

    await conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_shipments_po
        ON shipments (po_id)
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS shipment_line_items (
            id           TEXT PRIMARY KEY,
            shipment_id  TEXT NOT NULL REFERENCES shipments(id),
            part_number  TEXT NOT NULL,
            product_id   TEXT,
            description  TEXT NOT NULL DEFAULT '',
            quantity     INTEGER NOT NULL,
            uom          TEXT NOT NULL,
            sort_order   INTEGER NOT NULL
        )
        """
    )

    await conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_shipment_line_items_shipment
        ON shipment_line_items (shipment_id)
        """
    )

    # Iter 044: weight, dimension, and origin fields for packing list generation.
    # All nullable; populated via PATCH /api/v1/shipments/{id}.
    await conn.execute(
        "ALTER TABLE shipment_line_items ADD COLUMN IF NOT EXISTS net_weight TEXT"
    )
    await conn.execute(
        "ALTER TABLE shipment_line_items ADD COLUMN IF NOT EXISTS gross_weight TEXT"
    )
    await conn.execute(
        "ALTER TABLE shipment_line_items ADD COLUMN IF NOT EXISTS package_count INTEGER"
    )
    await conn.execute(
        "ALTER TABLE shipment_line_items ADD COLUMN IF NOT EXISTS dimensions TEXT"
    )
    await conn.execute(
        "ALTER TABLE shipment_line_items ADD COLUMN IF NOT EXISTS country_of_origin TEXT"
    )

    # Iter 074: shipment booking metadata. All nullable; populated on book_shipment transition.
    await conn.execute(
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS carrier TEXT"
    )
    await conn.execute(
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS booking_reference TEXT"
    )
    await conn.execute(
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS pickup_date TEXT"
    )
    await conn.execute(
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS shipped_at TEXT"
    )

    # Iter 074: rename PO milestone READY_TO_SHIP -> READY_FOR_SHIPMENT.
    # The existing literal must be migrated before any read code expects the new name.
    await conn.execute(
        "UPDATE milestone_updates SET milestone='READY_FOR_SHIPMENT' WHERE milestone='READY_TO_SHIP'"
    )

    # Iter 046: document requirements checklist per shipment.
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS shipment_document_requirements (
            id               TEXT PRIMARY KEY,
            shipment_id      TEXT NOT NULL REFERENCES shipments(id),
            document_type    TEXT NOT NULL,
            is_auto_generated INTEGER NOT NULL DEFAULT 0,
            status           TEXT NOT NULL DEFAULT 'PENDING',
            document_id      TEXT REFERENCES files(id),
            created_at       TEXT NOT NULL,
            updated_at       TEXT NOT NULL
        )
        """
    )

    await conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_shipment_document_requirements_shipment
        ON shipment_document_requirements (shipment_id)
        """
    )
