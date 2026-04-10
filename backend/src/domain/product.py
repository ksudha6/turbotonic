from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


class Product:
    # id owns the aggregate identity; vendor_id + part_number own the business reference
    def __init__(
        self,
        *,
        id: str,
        vendor_id: str,
        part_number: str,
        description: str,
        requires_certification: bool,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id
        self.vendor_id = vendor_id
        self.part_number = part_number
        self.description = description
        self.requires_certification = requires_certification
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
        vendor_id: str,
        part_number: str,
        description: str = "",
        requires_certification: bool = False,
    ) -> Product:
        if not vendor_id or not vendor_id.strip():
            raise ValueError("vendor_id must not be empty or whitespace-only")
        if not part_number or not part_number.strip():
            raise ValueError("part_number must not be empty or whitespace-only")
        now = datetime.now(UTC)
        return cls(
            id=str(uuid4()),
            vendor_id=vendor_id,
            part_number=part_number,
            description=description,
            requires_certification=requires_certification,
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
        *,
        description: str | None = None,
        requires_certification: bool | None = None,
    ) -> None:
        if description is not None:
            self.description = description
        if requires_certification is not None:
            self.requires_certification = requires_certification
        self.updated_at = datetime.now(UTC)
