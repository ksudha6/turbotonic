"""Iter 113: VendorParty domain unit tests."""
from __future__ import annotations

import time
from datetime import UTC, datetime

import pytest

from src.domain.vendor_party import VendorParty, VendorPartyRole, VendorPartyValidationError


def test_vendor_party_create_valid() -> None:
    vendor_id = "vendor-1"
    role = VendorPartyRole.SELLER
    legal_name = "Test Co Ltd"
    address = "123 Main St, Hong Kong"
    country = "HK"
    tax_id = "HK-12345"
    banking_details = "Bank of HK / Acct 9999"

    party = VendorParty.create(
        vendor_id=vendor_id,
        role=role,
        legal_name=legal_name,
        address=address,
        country=country,
        tax_id=tax_id,
        banking_details=banking_details,
    )

    assert party.vendor_id == vendor_id
    assert party.role == VendorPartyRole.SELLER
    assert party.legal_name == legal_name
    assert party.address == address
    assert party.country == country
    assert party.tax_id == tax_id
    assert party.banking_details == banking_details
    assert isinstance(party.id, str) and len(party.id) > 0
    assert isinstance(party.created_at, datetime)
    assert isinstance(party.updated_at, datetime)
    assert party.created_at == party.updated_at


def test_vendor_party_create_rejects_empty_legal_name() -> None:
    with pytest.raises(VendorPartyValidationError, match="legal_name"):
        VendorParty.create(
            vendor_id="v-1",
            role=VendorPartyRole.MANUFACTURER,
            legal_name="",
            address="Factory St",
            country="CN",
        )


def test_vendor_party_create_rejects_whitespace_legal_name() -> None:
    with pytest.raises(VendorPartyValidationError, match="legal_name"):
        VendorParty.create(
            vendor_id="v-1",
            role=VendorPartyRole.MANUFACTURER,
            legal_name="   ",
            address="Factory St",
            country="CN",
        )


def test_vendor_party_create_rejects_empty_address() -> None:
    with pytest.raises(VendorPartyValidationError, match="address"):
        VendorParty.create(
            vendor_id="v-1",
            role=VendorPartyRole.SHIPPER,
            legal_name="My Co",
            address="",
            country="CN",
        )


def test_vendor_party_create_rejects_unknown_country() -> None:
    with pytest.raises(VendorPartyValidationError, match="invalid country"):
        VendorParty.create(
            vendor_id="v-1",
            role=VendorPartyRole.SELLER,
            legal_name="My Co",
            address="Some address",
            country="XX",
        )


def test_vendor_party_update_advances_updated_at() -> None:
    party = VendorParty.create(
        vendor_id="v-1",
        role=VendorPartyRole.SELLER,
        legal_name="Old Name",
        address="Old Address",
        country="US",
    )
    original_updated_at = party.updated_at
    # Ensure a distinct timestamp by sleeping 1ms
    time.sleep(0.01)
    party.update(legal_name="New Name")

    assert party.legal_name == "New Name"
    assert party.updated_at > original_updated_at


def test_vendor_party_update_rejects_invalid_country() -> None:
    party = VendorParty.create(
        vendor_id="v-1",
        role=VendorPartyRole.MANUFACTURER,
        legal_name="Factory A",
        address="Shenzhen",
        country="CN",
    )
    with pytest.raises(VendorPartyValidationError, match="invalid country"):
        party.update(country="ZZ")


def test_vendor_party_role_values() -> None:
    # Assert all four roles exist with correct string values
    assert VendorPartyRole.MANUFACTURER == "MANUFACTURER"
    assert VendorPartyRole.SELLER == "SELLER"
    assert VendorPartyRole.SHIPPER == "SHIPPER"
    assert VendorPartyRole.REMIT_TO == "REMIT_TO"
