from __future__ import annotations

import pytest

from src.domain.document import FileMetadata


def test_create_valid():
    fm = FileMetadata.create(
        entity_type="CERTIFICATE", entity_id="cert-1", file_type="TEST_REPORT",
        original_name="report.pdf", stored_path="CERTIFICATE/cert-1/uuid_report.pdf",
        content_type="application/pdf", size_bytes=1024,
    )
    assert fm.id
    assert fm.entity_type == "CERTIFICATE"
    assert fm.entity_id == "cert-1"
    assert fm.file_type == "TEST_REPORT"
    assert fm.original_name == "report.pdf"
    assert fm.size_bytes == 1024
    assert fm.uploaded_at is not None


def test_reject_empty_entity_type():
    with pytest.raises(ValueError, match="entity_type"):
        FileMetadata.create(entity_type="", entity_id="x", file_type="", original_name="f.pdf",
                           stored_path="p", content_type="application/pdf", size_bytes=1)


def test_reject_whitespace_entity_type():
    with pytest.raises(ValueError, match="entity_type"):
        FileMetadata.create(entity_type="  ", entity_id="x", file_type="", original_name="f.pdf",
                           stored_path="p", content_type="application/pdf", size_bytes=1)


def test_reject_empty_entity_id():
    with pytest.raises(ValueError, match="entity_id"):
        FileMetadata.create(entity_type="X", entity_id="", file_type="", original_name="f.pdf",
                           stored_path="p", content_type="application/pdf", size_bytes=1)


def test_reject_whitespace_original_name():
    with pytest.raises(ValueError, match="original_name"):
        FileMetadata.create(entity_type="X", entity_id="x", file_type="", original_name="   ",
                           stored_path="p", content_type="application/pdf", size_bytes=1)


def test_reject_zero_size():
    with pytest.raises(ValueError, match="size_bytes"):
        FileMetadata.create(entity_type="X", entity_id="x", file_type="", original_name="f.pdf",
                           stored_path="p", content_type="application/pdf", size_bytes=0)


def test_reject_negative_size():
    with pytest.raises(ValueError, match="size_bytes"):
        FileMetadata.create(entity_type="X", entity_id="x", file_type="", original_name="f.pdf",
                           stored_path="p", content_type="application/pdf", size_bytes=-5)
