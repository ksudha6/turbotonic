from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


class QualificationType:
    # id owns the aggregate identity; name owns the business reference
    def __init__(
        self,
        *,
        id: str,
        name: str,
        description: str,
        target_market: str,
        applies_to_category: str,
        created_at: datetime,
    ) -> None:
        self._id = id
        self.name = name
        self.description = description
        self.target_market = target_market
        self.applies_to_category = applies_to_category
        self._created_at = created_at

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
        name: str,
        description: str = "",
        target_market: str,
        applies_to_category: str = "",
    ) -> QualificationType:
        if not name or not name.strip():
            raise ValueError("name must not be empty or whitespace-only")
        if not target_market or not target_market.strip():
            raise ValueError("target_market must not be empty or whitespace-only")
        return cls(
            id=str(uuid4()),
            name=name,
            description=description,
            target_market=target_market,
            applies_to_category=applies_to_category,
            created_at=datetime.now(UTC),
        )

    def update(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        target_market: str | None = None,
        applies_to_category: str | None = None,
    ) -> None:
        if name is not None:
            if not name.strip():
                raise ValueError("name must not be empty or whitespace-only")
            self.name = name
        if description is not None:
            self.description = description
        if target_market is not None:
            if not target_market.strip():
                raise ValueError("target_market must not be empty or whitespace-only")
            self.target_market = target_market
        if applies_to_category is not None:
            self.applies_to_category = applies_to_category
