from __future__ import annotations

import time

import pytest

from src.domain.brand import Brand, BrandStatus


def test_create_brand_succeeds_with_full_body() -> None:
    brand = Brand.create(
        name="Acme Brands",
        legal_name="Acme Brands Inc.",
        address="123 Commerce Blvd",
        country="US",
        tax_id="12-3456789",
    )
    assert brand.name == "Acme Brands"
    assert brand.legal_name == "Acme Brands Inc."
    assert brand.address == "123 Commerce Blvd"
    assert brand.country == "US"
    assert brand.tax_id == "12-3456789"
    assert brand.status is BrandStatus.ACTIVE
    assert brand.id is not None
    assert brand.created_at is not None
    assert brand.updated_at is not None


def test_create_brand_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="name"):
        Brand.create(
            name="",
            legal_name="Legal Name",
            address="123 St",
            country="US",
        )


def test_create_brand_rejects_whitespace_only_legal_name() -> None:
    with pytest.raises(ValueError, match="legal_name"):
        Brand.create(
            name="Brand A",
            legal_name="   ",
            address="123 St",
            country="US",
        )


def test_create_brand_rejects_unknown_country() -> None:
    with pytest.raises(ValueError, match="invalid country"):
        Brand.create(
            name="Brand A",
            legal_name="Brand A Legal",
            address="123 St",
            country="XX",
        )


def test_create_brand_defaults_status_active() -> None:
    brand = Brand.create(
        name="Brand B",
        legal_name="Brand B Ltd",
        address="456 Ave",
        country="DE",
    )
    assert brand.status is BrandStatus.ACTIVE


def test_deactivate_active_brand_succeeds() -> None:
    brand = Brand.create(
        name="Brand C",
        legal_name="Brand C Ltd",
        address="789 Rd",
        country="GB",
    )
    brand.deactivate()
    assert brand.status is BrandStatus.INACTIVE


def test_deactivate_already_inactive_raises() -> None:
    brand = Brand.create(
        name="Brand D",
        legal_name="Brand D Ltd",
        address="101 Blvd",
        country="US",
    )
    brand.deactivate()
    with pytest.raises(ValueError, match="already INACTIVE"):
        brand.deactivate()


def test_reactivate_inactive_brand_succeeds() -> None:
    brand = Brand.create(
        name="Brand E",
        legal_name="Brand E Ltd",
        address="202 Ln",
        country="US",
    )
    brand.deactivate()
    brand.reactivate()
    assert brand.status is BrandStatus.ACTIVE


def test_reactivate_already_active_raises() -> None:
    brand = Brand.create(
        name="Brand F",
        legal_name="Brand F Ltd",
        address="303 Way",
        country="US",
    )
    with pytest.raises(ValueError, match="already ACTIVE"):
        brand.reactivate()


def test_update_applies_partial_fields() -> None:
    brand = Brand.create(
        name="Brand G",
        legal_name="Brand G Ltd",
        address="404 St",
        country="US",
    )
    brand.update(legal_name="Updated Legal Name", tax_id="99-9999999")
    assert brand.legal_name == "Updated Legal Name"
    assert brand.tax_id == "99-9999999"
    # Unchanged fields stay the same
    assert brand.name == "Brand G"
    assert brand.country == "US"


def test_update_advances_updated_at() -> None:
    brand = Brand.create(
        name="Brand H",
        legal_name="Brand H Ltd",
        address="505 Ave",
        country="US",
    )
    before = brand.updated_at
    time.sleep(0.01)
    brand.update(name="Brand H Updated")
    assert brand.updated_at > before


def test_update_rejects_empty_legal_name() -> None:
    brand = Brand.create(
        name="Brand I",
        legal_name="Brand I Ltd",
        address="606 Rd",
        country="US",
    )
    with pytest.raises(ValueError, match="legal_name"):
        brand.update(legal_name="")
