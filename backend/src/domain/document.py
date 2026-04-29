from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


class FileMetadata:
    # id owns the aggregate identity; entity_type + entity_id own the business reference
    def __init__(
        self,
        *,
        id: str,
        entity_type: str,
        entity_id: str,
        file_type: str,
        original_name: str,
        stored_path: str,
        content_type: str,
        size_bytes: int,
        uploaded_at: datetime,
        uploaded_by: str | None = None,
    ) -> None:
        self._id = id
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.file_type = file_type
        self.original_name = original_name
        self.stored_path = stored_path
        self.content_type = content_type
        self.size_bytes = size_bytes
        self._uploaded_at = uploaded_at
        self.uploaded_by = uploaded_by

    @property
    def id(self) -> str:
        return self._id

    @property
    def uploaded_at(self) -> datetime:
        return self._uploaded_at

    @classmethod
    def create(
        cls,
        *,
        entity_type: str,
        entity_id: str,
        file_type: str,
        original_name: str,
        stored_path: str,
        content_type: str,
        size_bytes: int,
        uploaded_by: str | None = None,
    ) -> FileMetadata:
        if not entity_type or not entity_type.strip():
            raise ValueError("entity_type must not be empty or whitespace-only")
        if not entity_id or not entity_id.strip():
            raise ValueError("entity_id must not be empty or whitespace-only")
        if not original_name or not original_name.strip():
            raise ValueError("original_name must not be empty or whitespace-only")
        if size_bytes <= 0:
            raise ValueError("size_bytes must be greater than 0")
        return cls(
            id=str(uuid4()),
            entity_type=entity_type,
            entity_id=entity_id,
            file_type=file_type,
            original_name=original_name,
            stored_path=stored_path,
            content_type=content_type,
            size_bytes=size_bytes,
            uploaded_at=datetime.now(UTC),
            uploaded_by=uploaded_by,
        )
