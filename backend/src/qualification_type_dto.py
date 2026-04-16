from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

from src.domain.qualification_type import QualificationType


class QualificationTypeCreate(BaseModel):
    name: str
    description: str = ""
    target_market: str
    applies_to_category: str = ""

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name must not be empty or whitespace-only")
        return v

    @field_validator("target_market")
    @classmethod
    def target_market_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("target_market must not be empty or whitespace-only")
        return v


class QualificationTypeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    target_market: str | None = None
    applies_to_category: str | None = None


class QualificationTypeResponse(BaseModel):
    id: str
    name: str
    description: str
    target_market: str
    applies_to_category: str
    created_at: datetime


class QualificationTypeListItem(BaseModel):
    id: str
    name: str
    target_market: str
    applies_to_category: str


def qualification_type_to_response(qt: QualificationType) -> QualificationTypeResponse:
    return QualificationTypeResponse(
        id=qt.id,
        name=qt.name,
        description=qt.description,
        target_market=qt.target_market,
        applies_to_category=qt.applies_to_category,
        created_at=qt.created_at,
    )


def qualification_type_to_list_item(qt: QualificationType) -> QualificationTypeListItem:
    return QualificationTypeListItem(
        id=qt.id,
        name=qt.name,
        target_market=qt.target_market,
        applies_to_category=qt.applies_to_category,
    )
