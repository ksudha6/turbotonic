from __future__ import annotations

import time

import pytest

from src.domain.packaging import PackagingSpec, PackagingSpecStatus

PRODUCT_ID = "prod-001"
MARKETPLACE = "AMAZON"
SPEC_NAME = "FNSKU Label"
DESCRIPTION = "Label requirements for FNSKU"
REQUIREMENTS_TEXT = "300 DPI, 1x2 inch, PDF format"


def test_create_valid():
    spec = PackagingSpec.create(
        product_id=PRODUCT_ID,
        marketplace=MARKETPLACE,
        spec_name=SPEC_NAME,
        description=DESCRIPTION,
        requirements_text=REQUIREMENTS_TEXT,
    )
    assert spec.product_id == PRODUCT_ID
    assert spec.marketplace == MARKETPLACE
    assert spec.spec_name == SPEC_NAME
    assert spec.description == DESCRIPTION
    assert spec.requirements_text == REQUIREMENTS_TEXT
    assert spec.status is PackagingSpecStatus.PENDING
    assert spec.id is not None
    assert spec.created_at is not None
    assert spec.updated_at is not None


def test_create_default_description_and_requirements():
    spec = PackagingSpec.create(
        product_id=PRODUCT_ID,
        marketplace=MARKETPLACE,
        spec_name=SPEC_NAME,
    )
    assert spec.description == ""
    assert spec.requirements_text == ""


def test_id_is_immutable():
    spec = PackagingSpec.create(
        product_id=PRODUCT_ID,
        marketplace=MARKETPLACE,
        spec_name=SPEC_NAME,
    )
    original_id = spec.id
    with pytest.raises(AttributeError):
        spec.id = "other"  # type: ignore[misc]
    assert spec.id == original_id


def test_created_at_is_immutable():
    spec = PackagingSpec.create(
        product_id=PRODUCT_ID,
        marketplace=MARKETPLACE,
        spec_name=SPEC_NAME,
    )
    original_created_at = spec.created_at
    with pytest.raises(AttributeError):
        spec.created_at = spec.updated_at  # type: ignore[misc]
    assert spec.created_at == original_created_at


def test_status_is_pending():
    spec = PackagingSpec.create(
        product_id=PRODUCT_ID,
        marketplace=MARKETPLACE,
        spec_name=SPEC_NAME,
    )
    assert spec.status is PackagingSpecStatus.PENDING


def test_reject_empty_product_id():
    with pytest.raises(ValueError, match="product_id"):
        PackagingSpec.create(product_id="", marketplace=MARKETPLACE, spec_name=SPEC_NAME)


def test_reject_whitespace_only_product_id():
    with pytest.raises(ValueError, match="product_id"):
        PackagingSpec.create(product_id="   ", marketplace=MARKETPLACE, spec_name=SPEC_NAME)


def test_reject_empty_marketplace():
    with pytest.raises(ValueError, match="marketplace"):
        PackagingSpec.create(product_id=PRODUCT_ID, marketplace="", spec_name=SPEC_NAME)


def test_reject_whitespace_only_marketplace():
    with pytest.raises(ValueError, match="marketplace"):
        PackagingSpec.create(product_id=PRODUCT_ID, marketplace="  ", spec_name=SPEC_NAME)


def test_reject_empty_spec_name():
    with pytest.raises(ValueError, match="spec_name"):
        PackagingSpec.create(product_id=PRODUCT_ID, marketplace=MARKETPLACE, spec_name="")


def test_reject_whitespace_only_spec_name():
    with pytest.raises(ValueError, match="spec_name"):
        PackagingSpec.create(product_id=PRODUCT_ID, marketplace=MARKETPLACE, spec_name="   ")


def test_update_changes_fields():
    spec = PackagingSpec.create(
        product_id=PRODUCT_ID,
        marketplace=MARKETPLACE,
        spec_name=SPEC_NAME,
        description=DESCRIPTION,
        requirements_text=REQUIREMENTS_TEXT,
    )
    new_spec_name = "Suffocation Warning"
    new_description = "Updated description"
    new_requirements = "New requirements text"

    spec.update(
        spec_name=new_spec_name,
        description=new_description,
        requirements_text=new_requirements,
    )

    assert spec.spec_name == new_spec_name
    assert spec.description == new_description
    assert spec.requirements_text == new_requirements


def test_update_advances_updated_at():
    spec = PackagingSpec.create(
        product_id=PRODUCT_ID,
        marketplace=MARKETPLACE,
        spec_name=SPEC_NAME,
    )
    original_updated_at = spec.updated_at
    # Small sleep to ensure time advances
    time.sleep(0.001)
    spec.update(description="changed")
    assert spec.updated_at > original_updated_at


def test_update_unchanged_fields_stay():
    spec = PackagingSpec.create(
        product_id=PRODUCT_ID,
        marketplace=MARKETPLACE,
        spec_name=SPEC_NAME,
        description=DESCRIPTION,
        requirements_text=REQUIREMENTS_TEXT,
    )
    spec.update(description="only description changed")
    assert spec.spec_name == SPEC_NAME
    assert spec.requirements_text == REQUIREMENTS_TEXT


def test_update_none_values_leave_fields_unchanged():
    spec = PackagingSpec.create(
        product_id=PRODUCT_ID,
        marketplace=MARKETPLACE,
        spec_name=SPEC_NAME,
        description=DESCRIPTION,
        requirements_text=REQUIREMENTS_TEXT,
    )
    spec.update(spec_name=None, description=None, requirements_text=None)
    assert spec.spec_name == SPEC_NAME
    assert spec.description == DESCRIPTION
    assert spec.requirements_text == REQUIREMENTS_TEXT
