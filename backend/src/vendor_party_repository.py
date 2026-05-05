from __future__ import annotations

import json
from datetime import UTC, datetime

import asyncpg

from src.domain.vendor_party import (
    VendorParty,
    VendorPartyInUseError,
    VendorPartyRole,
    VendorPartyValidationError,
)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _reconstruct(row: asyncpg.Record) -> VendorParty:
    return VendorParty(
        id=row["id"],
        vendor_id=row["vendor_id"],
        role=VendorPartyRole(row["role"]),
        legal_name=row["legal_name"],
        address=row["address"],
        country=row["country"],
        tax_id=row["tax_id"] or "",
        banking_details=row["banking_details"] or "",
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


class VendorPartyRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def create(
        self,
        *,
        vendor_id: str,
        role: VendorPartyRole,
        legal_name: str,
        address: str,
        country: str,
        tax_id: str = "",
        banking_details: str = "",
    ) -> VendorParty:
        # VendorParty.create validates all fields; raises VendorPartyValidationError on failure.
        party = VendorParty.create(
            vendor_id=vendor_id,
            role=role,
            legal_name=legal_name,
            address=address,
            country=country,
            tax_id=tax_id,
            banking_details=banking_details,
        )
        await self._conn.execute(
            """
            INSERT INTO vendor_parties
                (id, vendor_id, role, legal_name, address, country, tax_id, banking_details, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            party.id,
            party.vendor_id,
            party.role.value,
            party.legal_name,
            party.address,
            party.country,
            party.tax_id,
            party.banking_details,
            _iso(party.created_at),
            _iso(party.updated_at),
        )
        return party

    async def get(self, party_id: str) -> VendorParty | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM vendor_parties WHERE id = $1", party_id
        )
        if row is None:
            return None
        return _reconstruct(row)

    async def list_by_vendor(self, vendor_id: str) -> list[VendorParty]:
        rows = await self._conn.fetch(
            "SELECT * FROM vendor_parties WHERE vendor_id = $1 ORDER BY role, created_at",
            vendor_id,
        )
        return [_reconstruct(row) for row in rows]

    async def list_by_vendor_and_role(
        self, vendor_id: str, role: VendorPartyRole
    ) -> list[VendorParty]:
        rows = await self._conn.fetch(
            "SELECT * FROM vendor_parties WHERE vendor_id = $1 AND role = $2 ORDER BY created_at",
            vendor_id,
            role.value,
        )
        return [_reconstruct(row) for row in rows]

    async def update(self, party_id: str, **fields: object) -> VendorParty:
        party = await self.get(party_id)
        if party is None:
            raise ValueError(f"VendorParty not found: {party_id!r}")
        # Delegate field-level validation to the domain object.
        party.update(**fields)  # type: ignore[arg-type]
        await self._conn.execute(
            """
            UPDATE vendor_parties
            SET legal_name = $1, address = $2, country = $3, tax_id = $4,
                banking_details = $5, updated_at = $6
            WHERE id = $7
            """,
            party.legal_name,
            party.address,
            party.country,
            party.tax_id,
            party.banking_details,
            _iso(party.updated_at),
            party.id,
        )
        return party

    async def delete(self, party_id: str) -> None:
        # Count all FK references across vendors, products, shipments, and purchase_orders.
        ref_count: int = await self._conn.fetchval(
            """
            SELECT
                (SELECT COUNT(*) FROM vendors
                 WHERE default_seller_party_id = $1
                    OR default_shipper_party_id = $1
                    OR default_remit_to_party_id = $1)
              + (SELECT COUNT(*) FROM products WHERE manufacturer_party_id = $1)
              + (SELECT COUNT(*) FROM shipments WHERE shipper_party_id = $1)
              + (SELECT COUNT(*) FROM purchase_orders
                 WHERE seller_party_id = $1 OR remit_to_party_id = $1)
            """,
            party_id,
        ) or 0
        if ref_count > 0:
            raise VendorPartyInUseError(
                f"VendorParty is referenced by {ref_count} active records"
            )
        await self._conn.execute(
            "DELETE FROM vendor_parties WHERE id = $1", party_id
        )

    async def set_default_party_on_vendor(
        self, vendor_id: str, role: VendorPartyRole, party_id: str | None
    ) -> None:
        # Direct SQL update to set a single default_*_party_id on the vendor row.
        # VendorRepository.save is not used here to avoid a full-row read + rewrite.
        column_map = {
            VendorPartyRole.SELLER: "default_seller_party_id",
            VendorPartyRole.SHIPPER: "default_shipper_party_id",
            VendorPartyRole.REMIT_TO: "default_remit_to_party_id",
        }
        column = column_map.get(role)
        if column is None:
            raise ValueError(f"unsupported role for vendor default: {role!r}")
        await self._conn.execute(
            f"UPDATE vendors SET {column} = $1, updated_at = $2 WHERE id = $3",
            party_id,
            _iso(datetime.now(UTC)),
            vendor_id,
        )
