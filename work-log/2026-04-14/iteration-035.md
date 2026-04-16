# Iteration 035 -- Document storage infrastructure

## Context

The system has no file handling; all data is structured records in SQLite. This iteration adds an API-only document storage layer (upload, download, delete, list by entity) backed by local filesystem at `uploads/`, with metadata in a `files` table. Certificates, packaging specs, and shipment documents all depend on this infrastructure.

## JTBD (Jobs To Be Done)

- When I need to attach a document to a certificate, packaging spec, or shipment, I want a storage API that handles upload/download/delete, so that each downstream feature doesn't reinvent file handling
- When I upload a file, I want its metadata (name, size, content type) recorded, so that I can list and retrieve files by entity
- When I download a file, I want the original filename preserved in the response headers, so that the browser prompts a meaningful save dialog

## Tasks

### Database schema
- [x] Add `files` table to `schema.py`:
  ```
  files (
      id              TEXT PRIMARY KEY,
      entity_type     TEXT NOT NULL,
      entity_id       TEXT NOT NULL,
      file_type       TEXT NOT NULL DEFAULT '',
      original_name   TEXT NOT NULL,
      stored_path     TEXT NOT NULL,
      content_type    TEXT NOT NULL,
      size_bytes      INTEGER NOT NULL,
      uploaded_at     TEXT NOT NULL
  )
  ```
- `entity_type`: the aggregate the file belongs to (e.g. CERTIFICATE, PACKAGING_SPEC, SHIPMENT). Free-text string, not an enum, to avoid schema changes as new entity types are added.
- `entity_id`: the ID of the owning aggregate
- `file_type`: optional sub-type within the entity (e.g. "TEST_REPORT", "FNSKU_LABEL"). Defaults to empty string.
- [x] Add index on `(entity_type, entity_id)` for the list query

### Domain model
- [x] Create `backend/src/domain/document.py`
  - `FileMetadata` dataclass: id, entity_type, entity_id, file_type, original_name, stored_path, content_type, size_bytes, uploaded_at
  - Factory `FileMetadata.create(entity_type, entity_id, file_type, original_name, stored_path, content_type, size_bytes) -> FileMetadata`
  - Validation: reject empty/whitespace-only `entity_type`, `entity_id`, `original_name`
  - Validation: `size_bytes` must be > 0

### DTOs
- [x] Create `backend/src/document_dto.py`
  - `FileUploadResponse(BaseModel)`: id, entity_type, entity_id, file_type, original_name, content_type, size_bytes, uploaded_at
  - `FileListItem(BaseModel)`: id, file_type, original_name, content_type, size_bytes, uploaded_at
  - `file_metadata_to_response(FileMetadata) -> FileUploadResponse`
  - `file_metadata_to_list_item(FileMetadata) -> FileListItem`

### Repository
- [x] Create `backend/src/document_repository.py`
  - `DocumentRepository.__init__(conn: asyncpg.Connection)`
  - `save(metadata: FileMetadata) -> None` -- INSERT
  - `get_by_id(file_id: str) -> FileMetadata | None`
  - `list_by_entity(entity_type: str, entity_id: str) -> list[FileMetadata]`
  - `delete(file_id: str) -> bool` -- DELETE row, return True if existed

### File storage service
- [x] Create `backend/src/services/file_storage.py`
  - `FileStorageService.__init__(base_dir: Path)` -- defaults to `uploads/` at project root
  - `async save_file(entity_type: str, entity_id: str, filename: str, content: bytes) -> str` -- returns `stored_path` relative to base_dir. Directory structure: `{entity_type}/{entity_id}/{uuid}_{filename}`
  - `read_file(stored_path: str) -> Path` -- returns absolute Path; raises FileNotFoundError if missing
  - `delete_file(stored_path: str) -> None` -- deletes file from disk; no-op if missing
  - Ensure directory creation is handled (os.makedirs with exist_ok=True)

### Router
- [x] Create `backend/src/routers/document.py`
  - All endpoints require authentication (`require_auth` dependency). Role guards deferred per backlog.
  - `POST /api/v1/files/upload` -- multipart form: `file` (UploadFile), `entity_type` (Form str), `entity_id` (Form str), `file_type` (Form str, optional default "")
    - Read file content, save via FileStorageService, create FileMetadata, save to DB
    - Return `FileUploadResponse`, status 201
    - Reject files > 10 MB (configurable constant at top of module)
    - Restrict content type to PDF only (`application/pdf`). Reject other file types with 415 Unsupported Media Type.
    - Sanitize uploaded filename: strip path separators to prevent path traversal
  - `GET /api/v1/files/{file_id}` -- stream file content with original filename in Content-Disposition
    - Sanitize `original_name` in Content-Disposition header: strip newlines, non-ASCII, and path separators
    - 404 if file_id not in DB or file missing from disk
  - `DELETE /api/v1/files/{file_id}` -- delete metadata from DB and file from disk
    - 404 if file_id not in DB
    - Return 204 on success
  - `GET /api/v1/files?entity_type=X&entity_id=Y` -- list files for an entity
    - Return `list[FileListItem]`
- [x] Register router in `backend/src/main.py`

### Existing test impact
- No existing tests break. This is a new module with new tables. The `files` table creation must be added to the test DB setup in `conftest.py` and the document repo dependency must be overridden.

### Tests (permanent)
- [x] `backend/tests/test_document.py` -- domain model tests:
  - FileMetadata.create with valid inputs
  - Reject empty entity_type, entity_id, original_name
  - Reject size_bytes <= 0
- [x] `backend/tests/test_api_document.py` -- API tests:
  - Upload a file, verify 201 and response fields
  - Download the uploaded file, verify content matches
  - List files by entity_type + entity_id
  - List files for entity with no files, verify empty list
  - Delete a file, verify 204 and subsequent 404 on download
  - Delete nonexistent file_id, verify 404
  - Upload file > 10 MB, verify rejection
  - Upload zero-byte file, verify rejection
  - Upload non-PDF file (e.g. text/plain), verify 415 rejection
  - Upload with path traversal in filename (e.g. `../../etc/passwd.pdf`), verify filename is sanitized
  - Download nonexistent file_id, verify 404
  - Download when file exists in DB but missing from disk, verify 404

### Tests (scratch)

Not needed. Permanent API tests cover stored_path structure and directory creation implicitly.

## Acceptance criteria
- [x] `POST /api/v1/files/upload` accepts multipart file with entity_type, entity_id, file_type; returns metadata with 201
- [x] `GET /api/v1/files/{file_id}` streams file with correct Content-Type and Content-Disposition
- [x] `DELETE /api/v1/files/{file_id}` removes both DB record and disk file
- [x] `GET /api/v1/files?entity_type=X&entity_id=Y` returns list of files for that entity
- [x] Files > 10 MB are rejected
- [x] All permanent tests pass via `make test`
- [x] `uploads/` directory is in `.gitignore`

## Notes

Added document storage infrastructure: `files` table with `(entity_type, entity_id)` index, `FileMetadata` domain model with validation, `DocumentRepository` for CRUD, `FileStorageService` for disk operations with path traversal protection, and a router with four endpoints (upload, download, delete, list). All endpoints require authentication; role guards deferred. PDF-only restriction at upload. Filename sanitization strips path separators on both storage and DB metadata. Added `python-multipart` dependency for FastAPI file uploads. Conftest updated with temp upload directory per test fixture and cleanup on teardown. 19 new tests (7 domain + 12 API) all pass alongside 265 existing.

## Files created
- `backend/src/domain/document.py`
- `backend/src/document_dto.py`
- `backend/src/document_repository.py`
- `backend/src/services/file_storage.py`
- `backend/src/routers/document.py`
- `backend/tests/test_document.py`
- `backend/tests/test_api_document.py`

## Files modified
- `backend/src/schema.py` -- add `files` table
- `backend/src/main.py` -- register document router
- `.gitignore` -- add `uploads/`
