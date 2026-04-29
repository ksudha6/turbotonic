from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

import asyncpg

from src.domain.document import FileMetadata


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class DocumentRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def save(self, metadata: FileMetadata) -> None:
        # INSERT only -- files are never updated
        await self._conn.execute(
            """
            INSERT INTO files (id, entity_type, entity_id, file_type, original_name,
                stored_path, content_type, size_bytes, uploaded_at, uploaded_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            metadata.id,
            metadata.entity_type,
            metadata.entity_id,
            metadata.file_type,
            metadata.original_name,
            metadata.stored_path,
            metadata.content_type,
            metadata.size_bytes,
            _iso(metadata.uploaded_at),
            metadata.uploaded_by,
        )

    async def get_by_id(self, file_id: str) -> FileMetadata | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM files WHERE id = $1", file_id
        )
        if row is None:
            return None
        return _reconstruct(row)

    async def list_by_entity(
        self,
        entity_type: str,
        entity_id: str,
        order: Literal["asc", "desc"] = "asc",
    ) -> list[FileMetadata]:
        # All existing callers rely on ASC order; PO documents use DESC.
        direction = "DESC" if order == "desc" else "ASC"
        rows = await self._conn.fetch(
            f"SELECT * FROM files WHERE entity_type = $1 AND entity_id = $2 ORDER BY uploaded_at {direction}",
            entity_type,
            entity_id,
        )
        return [_reconstruct(row) for row in rows]

    async def delete(self, file_id: str) -> bool:
        result = await self._conn.execute(
            "DELETE FROM files WHERE id = $1", file_id
        )
        # asyncpg returns "DELETE N" where N is the number of rows affected
        deleted_count = int(result.split()[-1])
        return deleted_count > 0


def _reconstruct(row: asyncpg.Record) -> FileMetadata:
    return FileMetadata(
        id=row["id"],
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        file_type=row["file_type"],
        original_name=row["original_name"],
        stored_path=row["stored_path"],
        content_type=row["content_type"],
        size_bytes=row["size_bytes"],
        uploaded_at=_parse_dt(row["uploaded_at"]),
        uploaded_by=row["uploaded_by"] if "uploaded_by" in row.keys() else None,
    )
