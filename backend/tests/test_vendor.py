from __future__ import annotations

import pytest

from src.domain.vendor import Vendor, VendorStatus, VendorType


# ---------------------------------------------------------------------------
# Vendor.create
# ---------------------------------------------------------------------------


def test_create_vendor_active_status() -> None:
    vendor = Vendor.create(name="Acme Corp", country="US", vendor_type=VendorType.PROCUREMENT)
    assert vendor.status is VendorStatus.ACTIVE


def test_create_vendor_generates_uuid() -> None:
    vendor = Vendor.create(name="Acme Corp", country="US", vendor_type=VendorType.PROCUREMENT)
    assert isinstance(vendor.id, str)
    assert len(vendor.id) == 36


def test_create_vendor_sets_timestamps() -> None:
    vendor = Vendor.create(name="Acme Corp", country="US", vendor_type=VendorType.PROCUREMENT)
    assert vendor.created_at == vendor.updated_at


def test_create_vendor_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="name"):
        Vendor.create(name="", country="US", vendor_type=VendorType.PROCUREMENT)


def test_create_vendor_rejects_whitespace_name() -> None:
    with pytest.raises(ValueError, match="name"):
        Vendor.create(name="   ", country="US", vendor_type=VendorType.PROCUREMENT)


def test_create_vendor_rejects_empty_country() -> None:
    with pytest.raises(ValueError, match="country"):
        Vendor.create(name="Acme Corp", country="", vendor_type=VendorType.PROCUREMENT)


def test_create_vendor_rejects_whitespace_country() -> None:
    with pytest.raises(ValueError, match="country"):
        Vendor.create(name="Acme Corp", country="   ", vendor_type=VendorType.PROCUREMENT)


# ---------------------------------------------------------------------------
# Vendor.deactivate
# ---------------------------------------------------------------------------


def test_deactivate_sets_inactive() -> None:
    vendor = Vendor.create(name="Acme Corp", country="US", vendor_type=VendorType.PROCUREMENT)
    vendor.deactivate()
    assert vendor.status is VendorStatus.INACTIVE


def test_deactivate_already_inactive_raises() -> None:
    vendor = Vendor.create(name="Acme Corp", country="US", vendor_type=VendorType.PROCUREMENT)
    vendor.deactivate()
    with pytest.raises(ValueError, match="INACTIVE"):
        vendor.deactivate()


# ---------------------------------------------------------------------------
# Vendor.reactivate
# ---------------------------------------------------------------------------


def test_reactivate_sets_active() -> None:
    vendor = Vendor.create(name="Acme Corp", country="US", vendor_type=VendorType.PROCUREMENT)
    vendor.deactivate()
    vendor.reactivate()
    assert vendor.status is VendorStatus.ACTIVE


def test_reactivate_already_active_raises() -> None:
    vendor = Vendor.create(name="Acme Corp", country="US", vendor_type=VendorType.PROCUREMENT)
    with pytest.raises(ValueError, match="ACTIVE"):
        vendor.reactivate()
