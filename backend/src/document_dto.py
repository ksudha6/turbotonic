from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from src.domain.document import FileMetadata


class FileUploadResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    file_type: str
    original_name: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime


class FileListItem(BaseModel):
    id: str
    file_type: str
    original_name: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime


def file_metadata_to_response(metadata: FileMetadata) -> FileUploadResponse:
    return FileUploadResponse(
        id=metadata.id,
        entity_type=metadata.entity_type,
        entity_id=metadata.entity_id,
        file_type=metadata.file_type,
        original_name=metadata.original_name,
        content_type=metadata.content_type,
        size_bytes=metadata.size_bytes,
        uploaded_at=metadata.uploaded_at,
    )


def file_metadata_to_list_item(metadata: FileMetadata) -> FileListItem:
    return FileListItem(
        id=metadata.id,
        file_type=metadata.file_type,
        original_name=metadata.original_name,
        content_type=metadata.content_type,
        size_bytes=metadata.size_bytes,
        uploaded_at=metadata.uploaded_at,
    )
