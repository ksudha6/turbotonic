from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4


class FileStorageService:
    # base_dir owns all stored files; stored_path is always relative to base_dir
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    async def save_file(
        self, entity_type: str, entity_id: str, filename: str, content: bytes
    ) -> str:
        # Sanitize filename: strip path separators to prevent traversal
        safe_name = filename.replace("/", "_").replace("\\", "_")
        unique_name = f"{uuid4()}_{safe_name}"
        stored_path = f"{entity_type}/{entity_id}/{unique_name}"
        full_path = self._base_dir / stored_path
        os.makedirs(full_path.parent, exist_ok=True)
        full_path.write_bytes(content)
        return stored_path

    def read_file(self, stored_path: str) -> Path:
        # Resolve to absolute path and validate it stays within base_dir
        full_path = (self._base_dir / stored_path).resolve()
        base_resolved = self._base_dir.resolve()
        if not str(full_path).startswith(str(base_resolved)):
            raise FileNotFoundError(f"Path traversal detected: {stored_path}")
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {stored_path}")
        return full_path

    def delete_file(self, stored_path: str) -> None:
        # Delete file from disk; no-op if missing
        full_path = (self._base_dir / stored_path).resolve()
        base_resolved = self._base_dir.resolve()
        if not str(full_path).startswith(str(base_resolved)):
            return
        if full_path.exists():
            full_path.unlink()
