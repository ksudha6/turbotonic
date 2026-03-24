from __future__ import annotations

from .reference_data import CURRENCIES, INCOTERMS, PAYMENT_TERMS, COUNTRIES, PORTS

# Code-to-label lookup dicts built from the canonical reference tuples.
_CURRENCY_LABELS: dict[str, str] = {code: label for code, label in CURRENCIES}
_INCOTERM_LABELS: dict[str, str] = {code: label for code, label in INCOTERMS}
_PAYMENT_TERM_LABELS: dict[str, str] = {code: label for code, label in PAYMENT_TERMS}
_COUNTRY_LABELS: dict[str, str] = {code: label for code, label in COUNTRIES}
_PORT_LABELS: dict[str, str] = {code: label for code, label in PORTS}


def currency_label(code: str) -> str:
    return _CURRENCY_LABELS.get(code, code)


def incoterm_label(code: str) -> str:
    return _INCOTERM_LABELS.get(code, code)


def payment_terms_label(code: str) -> str:
    return _PAYMENT_TERM_LABELS.get(code, code)


def country_label(code: str) -> str:
    return _COUNTRY_LABELS.get(code, code)


def port_label(code: str) -> str:
    # Port codes are 5 chars: 2-char country prefix + 3-char port code (e.g. "CNSHA").
    # Derives "City, Country" by combining the port city name with the country name
    # resolved from the 2-char prefix.
    city = _PORT_LABELS.get(code, code)
    if len(code) >= 2:
        country = _COUNTRY_LABELS.get(code[:2], "")
        if country:
            return f"{city}, {country}"
    return city
