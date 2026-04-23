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
                INSERT INTO users (id, username, display_name, role, status, vendor_id, created_at, email)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                user.id, user.username, user.display_name, user.role.value,
                user.status.value, user.vendor_id, _iso(user.created_at),
                user.email,
            )
        else:
            await self._conn.execute(
                """
                UPDATE users SET username = $1, display_name = $2, role = $3,
                    status = $4, vendor_id = $5, email = $6
                WHERE id = $7
                """,
                user.username, user.display_name, user.role.value,
                user.status.value, user.vendor_id, user.email, user.id,
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

    async def list_active_emails_by_roles(self, roles: tuple[str, ...]) -> list[str]:
        # Returns the non-null, non-empty emails of every ACTIVE user whose role is
        # in `roles`. The caller is the notification dispatcher resolving SM-targeted
        # recipients (SM + ADMIN) without pulling the full User rows.
        rows = await self._conn.fetch(
            """
            SELECT email FROM users
            WHERE status = $1
              AND role = ANY($2::text[])
              AND email IS NOT NULL
              AND email <> ''
            ORDER BY email
            """,
            UserStatus.ACTIVE.value, list(roles),
        )
        return [row["email"] for row in rows]

    async def list_active_emails_by_vendor(self, vendor_id: str) -> list[str]:
        # Vendor-scoped recipients: ACTIVE VENDOR users with matching vendor_id.
        # Inactive users and null/empty emails are excluded at the query boundary.
        rows = await self._conn.fetch(
            """
            SELECT email FROM users
            WHERE status = $1
              AND role = $2
              AND vendor_id = $3
              AND email IS NOT NULL
              AND email <> ''
            ORDER BY email
            """,
            UserStatus.ACTIVE.value, UserRole.VENDOR.value, vendor_id,
        )
        return [row["email"] for row in rows]

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
    # Older rows may not carry the email column depending on migration order;
    # .get() on asyncpg.Record raises KeyError, so fall back via indexing in a try.
    try:
        email_value = row["email"]
    except KeyError:
        email_value = None
    return User(
        id=row["id"],
        username=row["username"],
        display_name=row["display_name"],
        role=UserRole(row["role"]),
        status=UserStatus(row["status"]),
        vendor_id=row["vendor_id"],
        created_at=_parse_dt(row["created_at"]),
        email=email_value,
    )
