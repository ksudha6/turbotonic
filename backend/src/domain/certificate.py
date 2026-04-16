from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4


class CertificateStatus(str, Enum):
    PENDING = "PENDING"
    VALID = "VALID"


class Certificate:
    # id and created_at are immutable; all other fields are mutable
    def __init__(
        self,
        *,
        id: str,
        product_id: str,
        qualification_type_id: str,
        cert_number: str,
        issuer: str,
        testing_lab: str,
        test_date: datetime | None,
        issue_date: datetime,
        expiry_date: datetime | None,
        target_market: str,
        document_id: str | None,
        status: CertificateStatus,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id
        self.product_id = product_id
        self.qualification_type_id = qualification_type_id
        self.cert_number = cert_number
        self.issuer = issuer
        self.testing_lab = testing_lab
        self.test_date = test_date
        self.issue_date = issue_date
        self.expiry_date = expiry_date
        self.target_market = target_market
        self.document_id = document_id
        self.status = status
        self._created_at = created_at
        self.updated_at = updated_at

    @property
    def id(self) -> str:
        return self._id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @classmethod
    def create(
        cls,
        *,
        product_id: str,
        qualification_type_id: str,
        cert_number: str,
        issuer: str,
        testing_lab: str = "",
        test_date: datetime | None = None,
        issue_date: datetime,
        expiry_date: datetime | None = None,
        target_market: str,
    ) -> Certificate:
        if not product_id or not product_id.strip():
            raise ValueError("product_id must not be empty or whitespace-only")
        if not qualification_type_id or not qualification_type_id.strip():
            raise ValueError("qualification_type_id must not be empty or whitespace-only")
        if not cert_number or not cert_number.strip():
            raise ValueError("cert_number must not be empty or whitespace-only")
        if not issuer or not issuer.strip():
            raise ValueError("issuer must not be empty or whitespace-only")
        if not target_market or not target_market.strip():
            raise ValueError("target_market must not be empty or whitespace-only")
        now = datetime.now(UTC)
        return cls(
            id=str(uuid4()),
            product_id=product_id,
            qualification_type_id=qualification_type_id,
            cert_number=cert_number,
            issuer=issuer,
            testing_lab=testing_lab,
            test_date=test_date,
            issue_date=issue_date,
            expiry_date=expiry_date,
            target_market=target_market,
            document_id=None,
            status=CertificateStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

    def mark_valid(self) -> None:
        # Transitions PENDING -> VALID; VALID is terminal
        if self.status is CertificateStatus.VALID:
            raise ValueError("Certificate is already VALID")
        self.status = CertificateStatus.VALID
        self.updated_at = datetime.now(UTC)

    def attach_document(self, document_id: str) -> None:
        # document_id owns the link to the stored file
        if not document_id or not document_id.strip():
            raise ValueError("document_id must not be empty or whitespace-only")
        self.document_id = document_id
        self.updated_at = datetime.now(UTC)

    def update(
        self,
        *,
        cert_number: str | None = None,
        issuer: str | None = None,
        testing_lab: str | None = None,
        test_date: datetime | None = None,
        issue_date: datetime | None = None,
        expiry_date: datetime | None = None,
        target_market: str | None = None,
    ) -> None:
        if cert_number is not None:
            self.cert_number = cert_number
        if issuer is not None:
            self.issuer = issuer
        if testing_lab is not None:
            self.testing_lab = testing_lab
        if test_date is not None:
            self.test_date = test_date
        if issue_date is not None:
            self.issue_date = issue_date
        if expiry_date is not None:
            self.expiry_date = expiry_date
        if target_market is not None:
            self.target_market = target_market
        self.updated_at = datetime.now(UTC)

    def is_expired(self, as_of: datetime | None = None) -> bool:
        # True when expiry_date is set and lies in the past relative to as_of
        if self.expiry_date is None:
            return False
        reference = as_of if as_of is not None else datetime.now(UTC)
        return self.expiry_date < reference

    def display_status(self, as_of: datetime | None = None) -> str:
        # Returns "EXPIRED" for expired certificates regardless of persisted status
        if self.is_expired(as_of):
            return "EXPIRED"
        return self.status.value
