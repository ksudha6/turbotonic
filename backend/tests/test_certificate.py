from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.domain.certificate import Certificate, CertificateStatus

PRODUCT_ID = "prod-001"
QUAL_TYPE_ID = "qt-001"
CERT_NUMBER = "CERT-2024-001"
ISSUER = "Bureau Veritas"
TARGET_MARKET = "EU"
ISSUE_DATE = datetime(2024, 1, 1, tzinfo=UTC)
EXPIRY_DATE_FUTURE = datetime(2099, 12, 31, tzinfo=UTC)
EXPIRY_DATE_PAST = datetime(2020, 1, 1, tzinfo=UTC)


def _make_cert(**kwargs) -> Certificate:
    defaults = dict(
        product_id=PRODUCT_ID,
        qualification_type_id=QUAL_TYPE_ID,
        cert_number=CERT_NUMBER,
        issuer=ISSUER,
        issue_date=ISSUE_DATE,
        target_market=TARGET_MARKET,
    )
    defaults.update(kwargs)
    return Certificate.create(**defaults)


def test_create_with_valid_inputs():
    cert = _make_cert()
    assert cert.id is not None
    assert cert.product_id == PRODUCT_ID
    assert cert.qualification_type_id == QUAL_TYPE_ID
    assert cert.cert_number == CERT_NUMBER
    assert cert.issuer == ISSUER
    assert cert.target_market == TARGET_MARKET
    assert cert.status is CertificateStatus.PENDING
    assert cert.document_id is None
    assert cert.created_at is not None
    assert cert.updated_at is not None


def test_reject_empty_cert_number():
    with pytest.raises(ValueError, match="cert_number"):
        _make_cert(cert_number="")


def test_reject_empty_issuer():
    with pytest.raises(ValueError, match="issuer"):
        _make_cert(issuer="")


def test_reject_empty_product_id():
    with pytest.raises(ValueError, match="product_id"):
        _make_cert(product_id="")


def test_reject_empty_qualification_type_id():
    with pytest.raises(ValueError, match="qualification_type_id"):
        _make_cert(qualification_type_id="")


def test_reject_empty_target_market():
    with pytest.raises(ValueError, match="target_market"):
        _make_cert(target_market="")


def test_mark_valid_transitions_pending_to_valid():
    cert = _make_cert()
    assert cert.status is CertificateStatus.PENDING
    cert.mark_valid()
    assert cert.status is CertificateStatus.VALID


def test_mark_valid_raises_when_already_valid():
    cert = _make_cert()
    cert.mark_valid()
    with pytest.raises(ValueError, match="already VALID"):
        cert.mark_valid()


def test_attach_document_sets_document_id():
    cert = _make_cert()
    cert.attach_document("doc-123")
    assert cert.document_id == "doc-123"


def test_attach_document_raises_on_empty():
    cert = _make_cert()
    with pytest.raises(ValueError, match="document_id"):
        cert.attach_document("")


def test_is_expired_true_when_expiry_in_past():
    cert = _make_cert(expiry_date=EXPIRY_DATE_PAST)
    assert cert.is_expired() is True


def test_is_expired_false_when_expiry_none():
    cert = _make_cert()
    assert cert.is_expired() is False


def test_is_expired_false_when_expiry_in_future():
    cert = _make_cert(expiry_date=EXPIRY_DATE_FUTURE)
    assert cert.is_expired() is False


def test_display_status_expired_for_past_expiry():
    cert = _make_cert(expiry_date=EXPIRY_DATE_PAST)
    assert cert.display_status() == "EXPIRED"


def test_display_status_valid_for_valid_non_expired():
    cert = _make_cert(expiry_date=EXPIRY_DATE_FUTURE)
    cert.mark_valid()
    assert cert.display_status() == "VALID"


def test_display_status_pending_for_pending_cert():
    cert = _make_cert()
    assert cert.display_status() == "PENDING"


def test_is_expired_uses_as_of_parameter():
    cert_date = datetime(2024, 6, 1, tzinfo=UTC)
    cert = _make_cert(expiry_date=cert_date)
    # as_of before expiry -- not expired
    assert cert.is_expired(as_of=datetime(2024, 5, 31, tzinfo=UTC)) is False
    # as_of after expiry -- expired
    assert cert.is_expired(as_of=datetime(2024, 6, 2, tzinfo=UTC)) is True


# Iter 105: approve() state machine
def test_approve_transitions_valid_to_approved():
    cert = _make_cert()
    cert.mark_valid()
    assert cert.status is CertificateStatus.VALID
    cert.approve()
    assert cert.status is CertificateStatus.APPROVED


def test_approve_raises_from_pending():
    cert = _make_cert()
    with pytest.raises(ValueError, match="cannot be approved"):
        cert.approve()


def test_approve_raises_from_approved():
    cert = _make_cert()
    cert.mark_valid()
    cert.approve()
    with pytest.raises(ValueError, match="cannot be approved"):
        cert.approve()


def test_display_status_approved_for_approved_cert():
    cert = _make_cert()
    cert.mark_valid()
    cert.approve()
    assert cert.display_status() == "APPROVED"
