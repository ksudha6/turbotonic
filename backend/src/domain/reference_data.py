from __future__ import annotations

from decimal import Decimal

# Reference Data: system-managed value lists constraining PO fields.
# Frontend renders these as dropdowns; backend validates against them.

CURRENCIES: tuple[tuple[str, str], ...] = (
    ("AED", "UAE Dirham"),
    ("AUD", "Australian Dollar"),
    ("BDT", "Bangladeshi Taka"),
    ("BRL", "Brazilian Real"),
    ("CAD", "Canadian Dollar"),
    ("CHF", "Swiss Franc"),
    ("CNY", "Chinese Yuan"),
    ("DKK", "Danish Krone"),
    ("EUR", "Euro"),
    ("GBP", "British Pound"),
    ("HKD", "Hong Kong Dollar"),
    ("IDR", "Indonesian Rupiah"),
    ("INR", "Indian Rupee"),
    ("JPY", "Japanese Yen"),
    ("KRW", "South Korean Won"),
    ("MXN", "Mexican Peso"),
    ("MYR", "Malaysian Ringgit"),
    ("NOK", "Norwegian Krone"),
    ("NZD", "New Zealand Dollar"),
    ("PHP", "Philippine Peso"),
    ("PKR", "Pakistani Rupee"),
    ("SAR", "Saudi Riyal"),
    ("SEK", "Swedish Krona"),
    ("SGD", "Singapore Dollar"),
    ("THB", "Thai Baht"),
    ("TRY", "Turkish Lira"),
    ("TWD", "Taiwan Dollar"),
    ("USD", "US Dollar"),
    ("VND", "Vietnamese Dong"),
    ("ZAR", "South African Rand"),
)

INCOTERMS: tuple[tuple[str, str], ...] = (
    ("CFR", "Cost and Freight"),
    ("CIF", "Cost, Insurance and Freight"),
    ("CIP", "Carriage and Insurance Paid To"),
    ("CPT", "Carriage Paid To"),
    ("DAP", "Delivered at Place"),
    ("DDP", "Delivered Duty Paid"),
    ("DPU", "Delivered at Place Unloaded"),
    ("EXW", "Ex Works"),
    ("FAS", "Free Alongside Ship"),
    ("FCA", "Free Carrier"),
    ("FOB", "Free on Board"),
)

PAYMENT_TERMS: tuple[tuple[str, str], ...] = (
    ("DA", "Documents against Acceptance"),
    ("DP", "Documents against Payment"),
    ("LC", "Letter of Credit"),
    ("TT", "Telegraphic Transfer"),
)

COUNTRIES: tuple[tuple[str, str], ...] = (
    ("AE", "United Arab Emirates"),
    ("AU", "Australia"),
    ("BD", "Bangladesh"),
    ("BR", "Brazil"),
    ("CA", "Canada"),
    ("CH", "Switzerland"),
    ("CN", "China"),
    ("DE", "Germany"),
    ("DK", "Denmark"),
    ("EG", "Egypt"),
    ("ES", "Spain"),
    ("FR", "France"),
    ("GB", "United Kingdom"),
    ("HK", "Hong Kong"),
    ("ID", "Indonesia"),
    ("IN", "India"),
    ("IT", "Italy"),
    ("JP", "Japan"),
    ("KR", "South Korea"),
    ("MX", "Mexico"),
    ("MY", "Malaysia"),
    ("NL", "Netherlands"),
    ("PH", "Philippines"),
    ("PK", "Pakistan"),
    ("SA", "Saudi Arabia"),
    ("SG", "Singapore"),
    ("TH", "Thailand"),
    ("TR", "Turkey"),
    ("US", "United States"),
    ("VN", "Vietnam"),
)

PORTS: tuple[tuple[str, str], ...] = (
    ("AEAUH", "Abu Dhabi"),
    ("AEJEA", "Jebel Ali"),
    ("AUMEL", "Melbourne"),
    ("AUSYD", "Sydney"),
    ("BDDAC", "Chittagong"),
    ("BRPNG", "Paranagua"),
    ("BRSSZ", "Santos"),
    ("CAVAN", "Vancouver"),
    ("CNNGB", "Ningbo"),
    ("CNQIN", "Qingdao"),
    ("CNSHA", "Shanghai"),
    ("CNSZX", "Shenzhen"),
    ("CNTAO", "Qingdao"),
    ("CNTXG", "Tianjin"),
    ("CNXMN", "Xiamen"),
    ("DEBRV", "Bremerhaven"),
    ("DEHAM", "Hamburg"),
    ("EGALY", "Alexandria"),
    ("EGPSD", "Port Said"),
    ("ESBCN", "Barcelona"),
    ("ESVLC", "Valencia"),
    ("FRFOS", "Marseille"),
    ("FRLEH", "Le Havre"),
    ("GBFXT", "Felixstowe"),
    ("GBSOU", "Southampton"),
    ("GRGIT", "Gioia Tauro"),
    ("GRPIR", "Piraeus"),
    ("HKHKG", "Hong Kong"),
    ("IDTPP", "Tanjung Priok"),
    ("INMUN", "Mundra"),
    ("INNSA", "Nhava Sheva"),
    ("ITGOA", "Genoa"),
    ("JPKOB", "Kobe"),
    ("JPTYO", "Tokyo"),
    ("JPYOK", "Yokohama"),
    ("KRPUS", "Busan"),
    ("MXMAN", "Manzanillo"),
    ("MYPKG", "Port Klang"),
    ("MYTPP", "Tanjung Pelepas"),
    ("NLRTM", "Rotterdam"),
    ("PHMNL", "Manila"),
    ("PKKHI", "Karachi"),
    ("SAJED", "Jeddah"),
    ("SGSIN", "Singapore"),
    ("THBKK", "Bangkok"),
    ("THLCH", "Laem Chabang"),
    ("TRIST", "Istanbul"),
    ("TWKHH", "Kaohsiung"),
    ("USHOU", "Houston"),
    ("USLAX", "Los Angeles"),
    ("USLGB", "Long Beach"),
    ("USNYC", "New York"),
    ("USSAV", "Savannah"),
    ("VNHPH", "Hai Phong"),
    ("VNSGN", "Ho Chi Minh City"),
    ("ZADUR", "Durban"),
)

VENDOR_TYPES: tuple[tuple[str, str], ...] = (
    ("PROCUREMENT", "Procurement"),
    ("OPEX", "OpEx"),
    ("FREIGHT", "Freight"),
    ("MISCELLANEOUS", "Miscellaneous"),
)

PO_TYPES: tuple[tuple[str, str], ...] = (
    ("PROCUREMENT", "Procurement"),
    ("OPEX", "OpEx"),
)

# Lookup sets for fast validation
VALID_CURRENCIES: frozenset[str] = frozenset(code for code, _ in CURRENCIES)
VALID_INCOTERMS: frozenset[str] = frozenset(code for code, _ in INCOTERMS)
VALID_PAYMENT_TERMS: frozenset[str] = frozenset(code for code, _ in PAYMENT_TERMS)
VALID_COUNTRIES: frozenset[str] = frozenset(code for code, _ in COUNTRIES)
VALID_PORTS: frozenset[str] = frozenset(code for code, _ in PORTS)
VALID_VENDOR_TYPES: frozenset[str] = frozenset(code for code, _ in VENDOR_TYPES)
VALID_PO_TYPES: frozenset[str] = frozenset(code for code, _ in PO_TYPES)

# Static USD exchange rates: 1 unit of currency = this many USD.
# Approximate indicative rates; not for financial calculations.
USD_EXCHANGE_RATES: tuple[tuple[str, str], ...] = (
    ("AED", "0.2723"),
    ("AUD", "0.6500"),
    ("BDT", "0.0083"),
    ("BRL", "0.1700"),
    ("CAD", "0.7400"),
    ("CHF", "1.1300"),
    ("CNY", "0.1380"),
    ("DKK", "0.1450"),
    ("EUR", "1.0800"),
    ("GBP", "1.2700"),
    ("HKD", "0.1280"),
    ("IDR", "0.0000625"),
    ("INR", "0.0119"),
    ("JPY", "0.0067"),
    ("KRW", "0.000725"),
    ("MXN", "0.0580"),
    ("MYR", "0.2130"),
    ("NOK", "0.0920"),
    ("NZD", "0.6100"),
    ("PHP", "0.0175"),
    ("PKR", "0.0036"),
    ("SAR", "0.2667"),
    ("SEK", "0.0950"),
    ("SGD", "0.7500"),
    ("THB", "0.0280"),
    ("TRY", "0.0310"),
    ("TWD", "0.0320"),
    ("USD", "1.0000"),
    ("VND", "0.0000400"),
    ("ZAR", "0.0530"),
)

RATE_TO_USD: dict[str, Decimal] = {code: Decimal(rate) for code, rate in USD_EXCHANGE_RATES}
