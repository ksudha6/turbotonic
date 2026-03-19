from __future__ import annotations

from fastapi import APIRouter

from src.domain.reference_data import (
    COUNTRIES,
    CURRENCIES,
    INCOTERMS,
    PAYMENT_TERMS,
    PORTS,
)

router = APIRouter(prefix="/api/v1/reference-data", tags=["reference-data"])


def _to_list(data: tuple[tuple[str, str], ...]) -> list[dict[str, str]]:
    return [{"code": code, "label": label} for code, label in data]


@router.get("/")
async def get_reference_data() -> dict[str, list[dict[str, str]]]:
    return {
        "currencies": _to_list(CURRENCIES),
        "incoterms": _to_list(INCOTERMS),
        "payment_terms": _to_list(PAYMENT_TERMS),
        "countries": _to_list(COUNTRIES),
        "ports": _to_list(PORTS),
    }
