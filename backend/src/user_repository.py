from __future__ import annotations

from datetime import UTC, datetime

import asyncpg

from src.domain.user import User, UserRole, UserStatus


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class UserRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def save(self, user: User) -> None:
        count = await self._conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE id = $1", user.id
        )
        exists = (count or 0) > 0

        if not exists:
            await self._conn.execute(
                """
                INSERT INTO users (id, username, display_name, role, status, vendor_id, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                user.id, user.username, user.display_name, user.role.value,
                user.status.value, user.vendor_id, _iso(user.created_at),
            )
        else:
            await self._conn.execute(
                """
                UPDATE users SET username = $1, display_name = $2, role = $3,
                    status = $4, vendor_id = $5
                WHERE id = $6
                """,
                user.username, user.display_name, user.role.value,
                user.status.value, user.vendor_id, user.id,
            )

    async def get_by_id(self, user_id: str) -> User | None:
        row = await self._conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        if row is None:
            return None
        return _reconstruct(row)

    async def get_by_username(self, username: str) -> User | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM users WHERE username = $1", username
        )
        if row is None:
            return None
        return _reconstruct(row)

    async def count_users(self) -> int:
        return await self._conn.fetchval("SELECT COUNT(*) FROM users")

    async def count_active_admins(self) -> int:
        return await self._conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE role = $1 AND status = $2",
            UserRole.ADMIN.value, UserStatus.ACTIVE.value,
        )

    async def save_credential(
        self, credential_id: str, user_id: str, public_key: bytes, sign_count: int
    ) -> None:
        await self._conn.execute(
            """
            INSERT INTO webauthn_credentials (credential_id, user_id, public_key, sign_count, created_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            credential_id, user_id, public_key, sign_count, _iso(datetime.now(UTC)),
        )

    async def get_credentials_by_user_id(self, user_id: str) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT * FROM webauthn_credentials WHERE user_id = $1", user_id
        )

    async def update_sign_count(self, credential_id: str, new_count: int) -> None:
        await self._conn.execute(
            "UPDATE webauthn_credentials SET sign_count = $1 WHERE credential_id = $2",
            new_count, credential_id,
        )


def _reconstruct(row: asyncpg.Record) -> User:
    return User(
        id=row["id"],
        username=row["username"],
        display_name=row["display_name"],
        role=UserRole(row["role"]),
        status=UserStatus(row["status"]),
        vendor_id=row["vendor_id"],
        created_at=_parse_dt(row["created_at"]),
    )
