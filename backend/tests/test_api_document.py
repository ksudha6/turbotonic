from __future__ import annotations

import io

import pytest

pytestmark = pytest.mark.asyncio

PDF_CONTENT = b"%PDF-1.4 test content for document storage"
ENTITY_TYPE = "CERTIFICATE"
ENTITY_ID = "cert-123"
FILE_TYPE = "TEST_REPORT"


async def _upload_pdf(client, entity_type=ENTITY_TYPE, entity_id=ENTITY_ID,
                      file_type=FILE_TYPE, content=PDF_CONTENT, filename="test.pdf"):
    return await client.post(
        "/api/v1/files/upload",
        files={"file": (filename, io.BytesIO(content), "application/pdf")},
        data={"entity_type": entity_type, "entity_id": entity_id, "file_type": file_type},
    )


async def test_upload_pdf(authenticated_client):
    resp = await _upload_pdf(authenticated_client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["entity_type"] == ENTITY_TYPE
    assert body["entity_id"] == ENTITY_ID
    assert body["file_type"] == FILE_TYPE
    assert body["original_name"] == "test.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["size_bytes"] == len(PDF_CONTENT)
    assert "id" in body
    assert "uploaded_at" in body


async def test_download_uploaded_file(authenticated_client):
    upload_resp = await _upload_pdf(authenticated_client)
    file_id = upload_resp.json()["id"]
    resp = await authenticated_client.get(f"/api/v1/files/{file_id}")
    assert resp.status_code == 200
    assert resp.content == PDF_CONTENT
    assert "test.pdf" in resp.headers.get("content-disposition", "")


async def test_list_files_by_entity(authenticated_client):
    await _upload_pdf(authenticated_client)
    resp = await authenticated_client.get(
        "/api/v1/files/", params={"entity_type": ENTITY_TYPE, "entity_id": ENTITY_ID}
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["original_name"] == "test.pdf"


async def test_list_files_empty(authenticated_client):
    resp = await authenticated_client.get(
        "/api/v1/files/", params={"entity_type": "NONEXISTENT", "entity_id": "none"}
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_delete_file(authenticated_client):
    upload_resp = await _upload_pdf(authenticated_client)
    file_id = upload_resp.json()["id"]
    del_resp = await authenticated_client.delete(f"/api/v1/files/{file_id}")
    assert del_resp.status_code == 204
    get_resp = await authenticated_client.get(f"/api/v1/files/{file_id}")
    assert get_resp.status_code == 404


async def test_delete_nonexistent(authenticated_client):
    resp = await authenticated_client.delete("/api/v1/files/nonexistent-id")
    assert resp.status_code == 404


async def test_upload_too_large(authenticated_client):
    big_content = b"x" * (10 * 1024 * 1024 + 1)
    resp = await _upload_pdf(authenticated_client, content=big_content)
    assert resp.status_code == 413


async def test_upload_zero_bytes(authenticated_client):
    resp = await _upload_pdf(authenticated_client, content=b"")
    assert resp.status_code == 400


async def test_upload_non_pdf(authenticated_client):
    resp = await authenticated_client.post(
        "/api/v1/files/upload",
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        data={"entity_type": ENTITY_TYPE, "entity_id": ENTITY_ID, "file_type": ""},
    )
    assert resp.status_code == 415


async def test_upload_path_traversal_filename(authenticated_client):
    resp = await _upload_pdf(authenticated_client, filename="../../etc/passwd.pdf")
    assert resp.status_code == 201
    body = resp.json()
    assert "/" not in body["original_name"]
    assert "\\" not in body["original_name"]


async def test_download_nonexistent(authenticated_client):
    resp = await authenticated_client.get("/api/v1/files/no-such-id")
    assert resp.status_code == 404


async def test_download_file_missing_from_disk(authenticated_client, upload_dir):
    upload_resp = await _upload_pdf(authenticated_client)
    file_id = upload_resp.json()["id"]
    # Delete physical files from disk
    for f in upload_dir.rglob("*"):
        if f.is_file():
            f.unlink()
    resp = await authenticated_client.get(f"/api/v1/files/{file_id}")
    assert resp.status_code == 404


async def test_upload_empty_entity_type(authenticated_client):
    resp = await _upload_pdf(authenticated_client, entity_type="")
    assert resp.status_code == 422


async def test_upload_empty_entity_id(authenticated_client):
    resp = await _upload_pdf(authenticated_client, entity_id="")
    assert resp.status_code == 422
