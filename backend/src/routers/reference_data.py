from __future__ import annotations

from fastapi import APIRouter, Depends

from src.auth.dependencies import require_auth
from src.domain.reference_data import (
    COUNTRIES,
    CURRENCIES,
    INCOTERMS,
    PAYMENT_TERMS,
    PAYMENT_TERMS_METADATA,
    PO_TYPES,
    PORTS,
    VENDOR_TYPES,
)
from src.domain.user import User

router = APIRouter(prefix="/api/v1/reference-data", tags=["reference-data"])


def _to_list(data: tuple[tuple[str, str], ...]) -> list[dict[str, str]]:
    return [{"code": code, "label": label} for code, label in data]


def _payment_terms_to_list() -> list[dict[str, object]]:
    # Iter 059: `has_advance` rides alongside code/label so the frontend can
    # conditionally show the advance-paid toggle without a second fetch.
    result: list[dict[str, object]] = []
    for code, label in PAYMENT_TERMS:
        metadata = PAYMENT_TERMS_METADATA.get(code, {})
        result.append(
            {
                "code": code,
                "label": label,
                "has_advance": bool(metadata.get("has_advance", False)),
            }
        )
    return result


@router.get("/")
async def get_reference_data(_user: User = require_auth) -> dict[str, list[dict[str, object]]]:
    return {
        "currencies": [dict(x) for x in _to_list(CURRENCIES)],
        "incoterms": [dict(x) for x in _to_list(INCOTERMS)],
        "payment_terms": _payment_terms_to_list(),
        "countries": [dict(x) for x in _to_list(COUNTRIES)],
        "ports": [dict(x) for x in _to_list(PORTS)],
        "vendor_types": [dict(x) for x in _to_list(VENDOR_TYPES)],
        "po_types": [dict(x) for x in _to_list(PO_TYPES)],
    }
