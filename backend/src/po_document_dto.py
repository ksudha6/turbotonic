from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class POFileUploadResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    file_type: str
    original_name: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
    uploaded_by: str | None
    uploaded_by_username: str | None


# Same shape as POFileUploadResponse; both the upload response and list items
# carry the full metadata including resolved uploader username.
POFileListItem = POFileUploadResponse
