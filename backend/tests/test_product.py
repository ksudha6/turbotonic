from __future__ import annotations

import pytest

from src.domain.product import Product


# ---------------------------------------------------------------------------
# Product.create
# ---------------------------------------------------------------------------


def test_create_product_defaults() -> None:
    product = Product.create(vendor_id="v-1", part_number="PN-001")
    assert product.vendor_id == "v-1"
    assert product.part_number == "PN-001"
    assert product.description == ""
    assert product.manufacturing_address == ""


def test_create_product_generates_uuid() -> None:
    product = Product.create(vendor_id="v-1", part_number="PN-001")
    assert isinstance(product.id, str)
    assert len(product.id) == 36


def test_create_product_sets_timestamps() -> None:
    product = Product.create(vendor_id="v-1", part_number="PN-001")
    assert product.created_at == product.updated_at


def test_create_product_with_manufacturing_address() -> None:
    product = Product.create(
        vendor_id="v-1", part_number="PN-001",
        description="Widget", manufacturing_address="123 Factory Rd",
    )
    assert product.description == "Widget"
    assert product.manufacturing_address == "123 Factory Rd"


def test_create_product_rejects_empty_vendor_id() -> None:
    with pytest.raises(ValueError, match="vendor_id"):
        Product.create(vendor_id="", part_number="PN-001")


def test_create_product_rejects_whitespace_vendor_id() -> None:
    with pytest.raises(ValueError, match="vendor_id"):
        Product.create(vendor_id="   ", part_number="PN-001")


def test_create_product_rejects_empty_part_number() -> None:
    with pytest.raises(ValueError, match="part_number"):
        Product.create(vendor_id="v-1", part_number="")


def test_create_product_rejects_whitespace_part_number() -> None:
    with pytest.raises(ValueError, match="part_number"):
        Product.create(vendor_id="v-1", part_number="   ")


# ---------------------------------------------------------------------------
# Product.update
# ---------------------------------------------------------------------------


def test_update_description() -> None:
    product = Product.create(vendor_id="v-1", part_number="PN-001")
    old_updated = product.updated_at
    product.update(description="New desc")
    assert product.description == "New desc"
    assert product.updated_at >= old_updated


def test_update_manufacturing_address() -> None:
    product = Product.create(vendor_id="v-1", part_number="PN-001")
    product.update(manufacturing_address="456 Plant Ave")
    assert product.manufacturing_address == "456 Plant Ave"


def test_update_noop_preserves_values() -> None:
    product = Product.create(
        vendor_id="v-1", part_number="PN-001",
        description="Original", manufacturing_address="789 Works Blvd",
    )
    product.update()
    assert product.description == "Original"
    assert product.manufacturing_address == "789 Works Blvd"
