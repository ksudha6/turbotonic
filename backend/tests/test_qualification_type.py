from __future__ import annotations

import pytest

from src.domain.qualification_type import QualificationType


# ---------------------------------------------------------------------------
# QualificationType.create
# ---------------------------------------------------------------------------


def test_create_with_valid_inputs() -> None:
    qt = QualificationType.create(name="CE Mark", target_market="EU")
    assert qt.name == "CE Mark"
    assert qt.target_market == "EU"
    assert qt.description == ""
    assert qt.applies_to_category == ""
    assert isinstance(qt.id, str)
    assert len(qt.id) == 36
    assert qt.created_at is not None


def test_create_with_all_fields() -> None:
    qt = QualificationType.create(
        name="FDA 510k",
        description="US FDA pre-market notification",
        target_market="US",
        applies_to_category="MEDICAL_DEVICES",
    )
    assert qt.name == "FDA 510k"
    assert qt.description == "US FDA pre-market notification"
    assert qt.target_market == "US"
    assert qt.applies_to_category == "MEDICAL_DEVICES"


def test_create_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="name"):
        QualificationType.create(name="", target_market="US")


def test_create_rejects_whitespace_only_name() -> None:
    with pytest.raises(ValueError, match="name"):
        QualificationType.create(name="   ", target_market="US")


def test_create_rejects_empty_target_market() -> None:
    with pytest.raises(ValueError, match="target_market"):
        QualificationType.create(name="CE Mark", target_market="")


def test_create_rejects_whitespace_only_target_market() -> None:
    with pytest.raises(ValueError, match="target_market"):
        QualificationType.create(name="CE Mark", target_market="   ")


def test_create_generates_unique_ids() -> None:
    qt1 = QualificationType.create(name="CE Mark", target_market="EU")
    qt2 = QualificationType.create(name="FDA 510k", target_market="US")
    assert qt1.id != qt2.id


# ---------------------------------------------------------------------------
# QualificationType.update
# ---------------------------------------------------------------------------


def test_update_name() -> None:
    qt = QualificationType.create(name="CE Mark", target_market="EU")
    qt.update(name="CE Mark v2")
    assert qt.name == "CE Mark v2"


def test_update_description() -> None:
    qt = QualificationType.create(name="CE Mark", target_market="EU")
    qt.update(description="Updated description")
    assert qt.description == "Updated description"


def test_update_target_market() -> None:
    qt = QualificationType.create(name="CE Mark", target_market="EU")
    qt.update(target_market="EEA")
    assert qt.target_market == "EEA"


def test_update_applies_to_category() -> None:
    qt = QualificationType.create(name="CE Mark", target_market="EU")
    qt.update(applies_to_category="ELECTRONICS")
    assert qt.applies_to_category == "ELECTRONICS"


def test_update_rejects_empty_name() -> None:
    qt = QualificationType.create(name="CE Mark", target_market="EU")
    with pytest.raises(ValueError, match="name"):
        qt.update(name="")


def test_update_rejects_whitespace_only_name() -> None:
    qt = QualificationType.create(name="CE Mark", target_market="EU")
    with pytest.raises(ValueError, match="name"):
        qt.update(name="   ")


def test_update_rejects_whitespace_only_target_market() -> None:
    qt = QualificationType.create(name="CE Mark", target_market="EU")
    with pytest.raises(ValueError, match="target_market"):
        qt.update(target_market="   ")


def test_update_noop_preserves_values() -> None:
    qt = QualificationType.create(
        name="CE Mark", target_market="EU",
        description="EU conformity", applies_to_category="ELECTRONICS",
    )
    qt.update()
    assert qt.name == "CE Mark"
    assert qt.target_market == "EU"
    assert qt.description == "EU conformity"
    assert qt.applies_to_category == "ELECTRONICS"


def test_id_and_created_at_are_immutable() -> None:
    qt = QualificationType.create(name="CE Mark", target_market="EU")
    original_id = qt.id
    original_created_at = qt.created_at
    qt.update(name="CE Mark v2", target_market="EEA")
    assert qt.id == original_id
    assert qt.created_at == original_created_at
