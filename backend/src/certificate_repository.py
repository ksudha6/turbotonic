from __future__ import annotations

from datetime import UTC, datetime

import asyncpg

from src.domain.certificate import Certificate, CertificateStatus


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _parse_dt_opt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return _parse_dt(value)


class CertificateRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def save(self, cert: Certificate) -> None:
        count = await self._conn.fetchval(
            "SELECT COUNT(*) FROM certificates WHERE id = $1", cert.id
        )
        exists = (count or 0) > 0

        if not exists:
            await self._conn.execute(
                """
                INSERT INTO certificates (
                    id, product_id, qualification_type_id, cert_number, issuer,
                    testing_lab, test_date, issue_date, expiry_date,
                    target_market, document_id, status, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                """,
                cert.id,
                cert.product_id,
                cert.qualification_type_id,
                cert.cert_number,
                cert.issuer,
                cert.testing_lab,
                _iso(cert.test_date) if cert.test_date is not None else None,
                _iso(cert.issue_date),
                _iso(cert.expiry_date) if cert.expiry_date is not None else None,
                cert.target_market,
                cert.document_id,
                cert.status.value,
                _iso(cert.created_at),
                _iso(cert.updated_at),
            )
        else:
            await self._conn.execute(
                """
                UPDATE certificates SET
                    cert_number = $1,
                    issuer = $2,
                    testing_lab = $3,
                    test_date = $4,
                    issue_date = $5,
                    expiry_date = $6,
                    target_market = $7,
                    document_id = $8,
                    status = $9,
                    updated_at = $10
                WHERE id = $11
                """,
                cert.cert_number,
                cert.issuer,
                cert.testing_lab,
                _iso(cert.test_date) if cert.test_date is not None else None,
                _iso(cert.issue_date),
                _iso(cert.expiry_date) if cert.expiry_date is not None else None,
                cert.target_market,
                cert.document_id,
                cert.status.value,
                _iso(cert.updated_at),
                cert.id,
            )

    async def get_by_id(self, cert_id: str) -> Certificate | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM certificates WHERE id = $1", cert_id
        )
        if row is None:
            return None
        return _reconstruct(row)

    async def list_by_product(self, product_id: str) -> list[Certificate]:
        rows = await self._conn.fetch(
            "SELECT * FROM certificates WHERE product_id = $1 ORDER BY issue_date DESC",
            product_id,
        )
        return [_reconstruct(row) for row in rows]

    async def list_by_product_and_market(
        self, product_id: str, target_market: str
    ) -> list[Certificate]:
        rows = await self._conn.fetch(
            "SELECT * FROM certificates WHERE product_id = $1 AND target_market = $2 ORDER BY issue_date DESC",
            product_id,
            target_market,
        )
        return [_reconstruct(row) for row in rows]

    async def list_by_qualification(
        self, qualification_type_id: str
    ) -> list[Certificate]:
        rows = await self._conn.fetch(
            "SELECT * FROM certificates WHERE qualification_type_id = $1 ORDER BY issue_date DESC",
            qualification_type_id,
        )
        return [_reconstruct(row) for row in rows]


def _reconstruct(row: asyncpg.Record) -> Certificate:
    return Certificate(
        id=row["id"],
        product_id=row["product_id"],
        qualification_type_id=row["qualification_type_id"],
        cert_number=row["cert_number"],
        issuer=row["issuer"],
        testing_lab=row["testing_lab"] or "",
        test_date=_parse_dt_opt(row["test_date"]),
        issue_date=_parse_dt(row["issue_date"]),
        expiry_date=_parse_dt_opt(row["expiry_date"]),
        target_market=row["target_market"],
        document_id=row["document_id"],
        status=CertificateStatus(row["status"]),
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )
