from __future__ import annotations

import aiosqlite


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

    await conn.commit()
