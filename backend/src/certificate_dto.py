from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

from src.domain.certificate import Certificate


class CertificateCreate(BaseModel):
    product_id: str
    qualification_type_id: str
    cert_number: str
    issuer: str
    testing_lab: str = ""
    test_date: datetime | None = None
    issue_date: datetime
    expiry_date: datetime | None = None
    target_market: str

    @field_validator("product_id")
    @classmethod
    def product_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("product_id must not be empty or whitespace-only")
        return v

    @field_validator("qualification_type_id")
    @classmethod
    def qualification_type_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("qualification_type_id must not be empty or whitespace-only")
        return v

    @field_validator("cert_number")
    @classmethod
    def cert_number_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("cert_number must not be empty or whitespace-only")
        return v

    @field_validator("issuer")
    @classmethod
    def issuer_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("issuer must not be empty or whitespace-only")
        return v

    @field_validator("target_market")
    @classmethod
    def target_market_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("target_market must not be empty or whitespace-only")
        return v


class CertificateUpdate(BaseModel):
    cert_number: str | None = None
    issuer: str | None = None
    testing_lab: str | None = None
    test_date: datetime | None = None
    issue_date: datetime | None = None
    expiry_date: datetime | None = None
    target_market: str | None = None
    status: str | None = None


class CertificateResponse(BaseModel):
    id: str
    product_id: str
    qualification_type_id: str
    cert_number: str
    issuer: str
    testing_lab: str
    test_date: datetime | None
    issue_date: datetime
    expiry_date: datetime | None
    target_market: str
    document_id: str | None
    # status is str to allow computed "EXPIRED" value
    status: str
    created_at: datetime
    updated_at: datetime


class CertificateListItem(BaseModel):
    id: str
    product_id: str
    qualification_type_id: str
    cert_number: str
    issuer: str
    target_market: str
    status: str
    expiry_date: datetime | None


def certificate_to_response(cert: Certificate) -> CertificateResponse:
    return CertificateResponse(
        id=cert.id,
        product_id=cert.product_id,
        qualification_type_id=cert.qualification_type_id,
        cert_number=cert.cert_number,
        issuer=cert.issuer,
        testing_lab=cert.testing_lab,
        test_date=cert.test_date,
        issue_date=cert.issue_date,
        expiry_date=cert.expiry_date,
        target_market=cert.target_market,
        document_id=cert.document_id,
        status=cert.display_status(),
        created_at=cert.created_at,
        updated_at=cert.updated_at,
    )


def certificate_to_list_item(cert: Certificate) -> CertificateListItem:
    return CertificateListItem(
        id=cert.id,
        product_id=cert.product_id,
        qualification_type_id=cert.qualification_type_id,
        cert_number=cert.cert_number,
        issuer=cert.issuer,
        target_market=cert.target_market,
        status=cert.display_status(),
        expiry_date=cert.expiry_date,
    )
