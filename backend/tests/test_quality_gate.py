"""Unit tests for the quality gate service.

All cases use in-memory fakes; no DB or HTTP.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import AsyncIterator
from unittest.mock import AsyncMock

import pytest

from src.domain.certificate import Certificate, CertificateStatus
from src.domain.product import Product
from src.domain.purchase_order import LineItem, PurchaseOrder
from src.domain.qualification_type import QualificationType
from src.services.quality_gate import CertWarningReason, check_po_qualifications

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MARKETPLACE = "AMZ"
_PRODUCT_ID = "prod-001"
_QT_ID = "qt-001"
_QT_NAME = "CE Mark"
_PART_NUMBER = "PN-001"


def _make_line(*, product_id: str | None = _PRODUCT_ID) -> LineItem:
    return LineItem(
        part_number=_PART_NUMBER,
        description="Widget",
        quantity=1,
        uom="EA",
        unit_price=Decimal("10.00"),
        hs_code="8471.30",
        country_of_origin="US",
        product_id=product_id,
    )


def _make_po(*, marketplace: str | None = _MARKETPLACE, lines: list[LineItem] | None = None) -> PurchaseOrder:
    if lines is None:
        lines = [_make_line()]
    now = datetime.now(UTC)
    return PurchaseOrder.create(
        po_number="PO-001",
        vendor_id="vendor-1",
        buyer_name="Buyer",
        buyer_country="US",
        ship_to_address="123 St",
        payment_terms="NET30",
        currency="USD",
        issued_date=now,
        required_delivery_date=now + timedelta(days=30),
        terms_and_conditions="T&C",
        incoterm="FOB",
        port_of_loading="USLAX",
        port_of_discharge="CNSHA",
        country_of_origin="US",
        country_of_destination="CN",
        line_items=lines,
        marketplace=marketplace,
    )


def _make_product() -> Product:
    now = datetime.now(UTC)
    return Product(
        id=_PRODUCT_ID,
        vendor_id="vendor-1",
        part_number=_PART_NUMBER,
        description="Widget",
        manufacturing_address="",
        created_at=now,
        updated_at=now,
    )


def _make_qual() -> QualificationType:
    return QualificationType(
        id=_QT_ID,
        name=_QT_NAME,
        description="",
        target_market=_MARKETPLACE,
        applies_to_category="",
        created_at=datetime.now(UTC),
    )


def _make_cert(
    *,
    status: CertificateStatus = CertificateStatus.VALID,
    expired: bool = False,
    qt_id: str = _QT_ID,
    product_id: str = _PRODUCT_ID,
    target_market: str = _MARKETPLACE,
) -> Certificate:
    now = datetime.now(UTC)
    expiry = now - timedelta(days=1) if expired else now + timedelta(days=365)
    return Certificate(
        id="cert-001",
        product_id=product_id,
        qualification_type_id=qt_id,
        cert_number="CERT-001",
        issuer="Lab",
        testing_lab="",
        test_date=None,
        issue_date=now - timedelta(days=10),
        expiry_date=expiry,
        target_market=target_market,
        document_id=None,
        status=status,
        created_at=now,
        updated_at=now,
    )


def _make_repos(
    product: Product | None = None,
    quals: list[QualificationType] | None = None,
    certs: list[Certificate] | None = None,
):
    product_repo = AsyncMock()
    product_repo.get_by_id.return_value = product if product is not None else _make_product()

    qual_repo = AsyncMock()
    qual_repo.list_by_product.return_value = quals if quals is not None else [_make_qual()]

    cert_repo = AsyncMock()
    cert_repo.list_by_product_and_market.return_value = certs if certs is not None else []

    return product_repo, qual_repo, cert_repo


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


async def test_no_marketplace_returns_empty() -> None:
    # Gate skips entirely when marketplace is not set.
    po = _make_po(marketplace=None)
    product_repo, qual_repo, cert_repo = _make_repos()
    warnings = await check_po_qualifications(po, product_repo, qual_repo, cert_repo)
    assert warnings == []
    product_repo.get_by_id.assert_not_called()


async def test_line_without_product_id_is_skipped() -> None:
    # Line items with no product link produce no warning and no repo call.
    po = _make_po(lines=[_make_line(product_id=None)])
    product_repo, qual_repo, cert_repo = _make_repos()
    warnings = await check_po_qualifications(po, product_repo, qual_repo, cert_repo)
    assert warnings == []
    product_repo.get_by_id.assert_not_called()


async def test_valid_cert_produces_no_warning() -> None:
    cert = _make_cert(status=CertificateStatus.VALID, expired=False)
    po = _make_po()
    product_repo, qual_repo, cert_repo = _make_repos(certs=[cert])
    warnings = await check_po_qualifications(po, product_repo, qual_repo, cert_repo)
    assert warnings == []


async def test_missing_cert_produces_missing_warning() -> None:
    po = _make_po()
    product_repo, qual_repo, cert_repo = _make_repos(certs=[])
    warnings = await check_po_qualifications(po, product_repo, qual_repo, cert_repo)
    assert len(warnings) == 1
    w = warnings[0]
    assert w.reason is CertWarningReason.MISSING
    assert w.part_number == _PART_NUMBER
    assert w.product_id == _PRODUCT_ID
    assert w.qualification_type_id == _QT_ID
    assert w.qualification_name == _QT_NAME
    assert w.line_item_index == 0


async def test_expired_cert_produces_expired_warning() -> None:
    cert = _make_cert(status=CertificateStatus.VALID, expired=True)
    po = _make_po()
    product_repo, qual_repo, cert_repo = _make_repos(certs=[cert])
    warnings = await check_po_qualifications(po, product_repo, qual_repo, cert_repo)
    assert len(warnings) == 1
    assert warnings[0].reason is CertWarningReason.EXPIRED


async def test_pending_cert_produces_missing_warning() -> None:
    # PENDING does not count as valid coverage; treat as MISSING.
    cert = _make_cert(status=CertificateStatus.PENDING, expired=False)
    po = _make_po()
    product_repo, qual_repo, cert_repo = _make_repos(certs=[cert])
    warnings = await check_po_qualifications(po, product_repo, qual_repo, cert_repo)
    assert len(warnings) == 1
    assert warnings[0].reason is CertWarningReason.MISSING


async def test_product_with_no_qualifications_produces_no_warning() -> None:
    # A product with no assigned qualification types needs no certs.
    po = _make_po()
    product_repo, qual_repo, cert_repo = _make_repos(quals=[])
    warnings = await check_po_qualifications(po, product_repo, qual_repo, cert_repo)
    assert warnings == []


async def test_multiple_line_items_mixed_coverage() -> None:
    # Line 0: product with missing cert -> warning.
    # Line 1: product with valid cert -> no warning.
    product_id_a = "prod-a"
    product_id_b = "prod-b"
    qt_a = QualificationType(
        id="qt-a", name="CE Mark", description="", target_market=_MARKETPLACE,
        applies_to_category="", created_at=datetime.now(UTC),
    )
    qt_b = QualificationType(
        id="qt-b", name="FCC", description="", target_market=_MARKETPLACE,
        applies_to_category="", created_at=datetime.now(UTC),
    )
    now = datetime.now(UTC)
    product_a = Product(
        id=product_id_a, vendor_id="v", part_number="PN-A", description="",
        manufacturing_address="", created_at=now, updated_at=now,
    )
    product_b = Product(
        id=product_id_b, vendor_id="v", part_number="PN-B", description="",
        manufacturing_address="", created_at=now, updated_at=now,
    )
    cert_b = _make_cert(status=CertificateStatus.VALID, expired=False, qt_id="qt-b", product_id=product_id_b)

    line_a = LineItem(
        part_number="PN-A", description="A", quantity=1, uom="EA",
        unit_price=Decimal("1.00"), hs_code="8471.30", country_of_origin="US",
        product_id=product_id_a,
    )
    line_b = LineItem(
        part_number="PN-B", description="B", quantity=1, uom="EA",
        unit_price=Decimal("1.00"), hs_code="8471.30", country_of_origin="US",
        product_id=product_id_b,
    )

    po = _make_po(lines=[line_a, line_b])

    product_repo = AsyncMock()
    product_repo.get_by_id.side_effect = lambda pid: (
        product_a if pid == product_id_a else product_b
    )

    qual_repo = AsyncMock()
    qual_repo.list_by_product.side_effect = lambda pid: (
        [qt_a] if pid == product_id_a else [qt_b]
    )

    cert_repo = AsyncMock()
    cert_repo.list_by_product_and_market.side_effect = lambda pid, _market: (
        [] if pid == product_id_a else [cert_b]
    )

    warnings = await check_po_qualifications(po, product_repo, qual_repo, cert_repo)
    assert len(warnings) == 1
    w = warnings[0]
    assert w.line_item_index == 0
    assert w.part_number == "PN-A"
    assert w.reason is CertWarningReason.MISSING
