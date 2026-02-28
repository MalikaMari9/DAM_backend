"""Region resolution — maps region names to country lists and resolves against available data.

Public API:
    normalize_region(text)               → canonical region name or None
    resolve_region_countries(region, ...) → list of country names in that region
    AVAILABLE_COUNTRIES                   → set of country names in pm25_history.json
"""

import json
import re
from pathlib import Path
from typing import Optional

# ═══════════════════════════════════════════════════════════════════
#  AVAILABLE COUNTRIES (loaded from pm25_history.json at import time)
# ═══════════════════════════════════════════════════════════════════

_HISTORY_PATH = Path(__file__).resolve().parent / "data" / "pm25_history.json"

try:
    with open(_HISTORY_PATH, "r", encoding="utf-8") as f:
        _history = json.load(f)
    AVAILABLE_COUNTRIES: set[str] = set(_history.keys())
except FileNotFoundError:
    AVAILABLE_COUNTRIES = set()


# ═══════════════════════════════════════════════════════════════════
#  COUNTRY SYNONYMS  (normalise variant names → canonical name)
# ═══════════════════════════════════════════════════════════════════

COUNTRY_SYNONYMS: dict[str, str] = {
    "Viet Nam": "Vietnam",
    "Lao PDR": "Laos",
    "Lao People's Dem. Rep.": "Laos",
    "Czechia": "Czech Republic",
    "Korea, Republic of": "South Korea",
    "Russian Federation": "Russia",
    "Moldova, Republic of": "Moldova",
    "Macedonia, The former Yugoslav Rep. of": "Macedonia",
    "Sudan, The Republic of": "Sudan",
    "Congo, Democratic Republic of the": "Democratic Republic of the Congo",
    "Hong Kong, China": "Hong Kong",
    "Taiwan, China": "Taiwan",
    "Serbia and Montenegro": "Serbia",
    "European Union": "EU",
    "USA": "United States",
    "UK": "United Kingdom",
    "UAE": "United Arab Emirates",
}


def _canonical(name: str) -> str:
    """Return canonical country name (applying synonyms)."""
    return COUNTRY_SYNONYMS.get(name, name)


# ═══════════════════════════════════════════════════════════════════
#  REGION → COUNTRY LISTS
# ═══════════════════════════════════════════════════════════════════

REGION_COUNTRIES: dict[str, list[str]] = {
    "ASEAN": [
        "Brunei", "Cambodia", "Indonesia", "Laos", "Malaysia",
        "Myanmar", "Philippines", "Singapore", "Thailand", "Vietnam",
        "Timor-Leste",
    ],
    "South Asia": [
        "Afghanistan", "Bangladesh", "Bhutan", "India", "Maldives",
        "Nepal", "Pakistan", "Sri Lanka",
    ],
    "East Asia": [
        "China", "Japan", "South Korea", "North Korea",
        "Mongolia", "Taiwan", "Hong Kong", "Macao",
    ],
    "Southeast Asia": [
        "Brunei", "Cambodia", "Indonesia", "Laos", "Malaysia",
        "Myanmar", "Philippines", "Singapore", "Thailand", "Vietnam",
        "Timor-Leste",
    ],
    "Europe": [
        "Albania", "Andorra", "Austria", "Belarus", "Belgium",
        "Bosnia and Herzegovina", "Bulgaria", "Croatia", "Cyprus",
        "Czech Republic", "Denmark", "Estonia", "Finland", "France",
        "Germany", "Greece", "Hungary", "Iceland", "Ireland", "Italy",
        "Kosovo", "Latvia", "Liechtenstein", "Lithuania", "Luxembourg",
        "Macedonia", "Malta", "Moldova", "Monaco", "Montenegro",
        "Netherlands", "Norway", "Poland", "Portugal", "Romania",
        "Russia", "San Marino", "Serbia", "Slovakia", "Slovenia",
        "Spain", "Sweden", "Switzerland", "Turkey", "Ukraine",
        "United Kingdom", "Vatican City",
    ],
    "Africa": [
        "Algeria", "Angola", "Benin", "Botswana", "Burkina Faso",
        "Burundi", "Cameroon", "Cape Verde", "Central African Republic",
        "Chad", "Comoros", "Democratic Republic of the Congo",
        "Republic of Congo", "Djibouti", "Egypt", "Equatorial Guinea",
        "Eritrea", "Ethiopia", "Gabon", "Gambia", "Ghana", "Guinea",
        "Guinea-Bissau", "Kenya", "Lesotho", "Liberia", "Libya",
        "Madagascar", "Malawi", "Mali", "Mauritania", "Mauritius",
        "Morocco", "Mozambique", "Namibia", "Niger", "Nigeria",
        "Rwanda", "Senegal", "Seychelles", "Sierra Leone", "Somalia",
        "South Africa", "South Sudan", "Sudan", "Swaziland",
        "Tanzania", "Togo", "Tunisia", "Uganda", "Zambia", "Zimbabwe",
    ],
    "North America": [
        "Canada", "United States", "Mexico",
    ],
    "South America": [
        "Argentina", "Bolivia", "Brazil", "Chile", "Colombia",
        "Ecuador", "Guyana", "Paraguay", "Peru", "Suriname",
        "Uruguay", "Venezuela",
    ],
    "Central America": [
        "Belize", "Costa Rica", "El Salvador", "Guatemala",
        "Honduras", "Nicaragua", "Panama",
    ],
    "Caribbean": [
        "Bahamas", "Barbados", "Cuba", "Dominica",
        "Dominican Republic", "Grenada", "Haiti", "Jamaica",
        "Saint Kitts and Nevis", "Saint Lucia",
        "Saint Vincent and the Grenadines",
        "Trinidad and Tobago",
    ],
    "Middle East": [
        "Bahrain", "Iran", "Iraq", "Israel", "Jordan", "Kuwait",
        "Lebanon", "Oman", "Qatar", "Saudi Arabia", "Syria",
        "United Arab Emirates", "Yemen",
    ],
    "Central Asia": [
        "Kazakhstan", "Kyrgyzstan", "Tajikistan", "Turkmenistan",
        "Uzbekistan",
    ],
    "Oceania": [
        "Australia", "Fiji", "Kiribati", "Marshall Islands",
        "Micronesia", "Nauru", "New Zealand", "Palau",
        "Papua New Guinea", "Samoa", "Solomon Islands", "Tonga",
        "Tuvalu", "Vanuatu",
    ],
}


# ═══════════════════════════════════════════════════════════════════
#  NORMALIZE REGION  (free-text → canonical region name)
# ═══════════════════════════════════════════════════════════════════

_REGION_PATTERNS: list[tuple[str, str]] = [
    # Order matters — more specific first
    (r"\basean\b", "ASEAN"),
    (r"\bsoutheast\s+asia(?:n)?\b", "ASEAN"),
    (r"\bsouth\s+asia(?:n)?\b", "South Asia"),
    (r"\beast\s+asia(?:n)?\b", "East Asia"),
    (r"\bcentral\s+asia(?:n)?\b", "Central Asia"),
    (r"\beurop(?:e|ean)\b", "Europe"),
    (r"\b(?:eu|european\s+union)\b", "Europe"),
    (r"\bafric(?:a|an)\b", "Africa"),
    (r"\bnorth\s+americ(?:a|an)\b", "North America"),
    (r"\bsouth\s+americ(?:a|an)\b", "South America"),
    (r"\bcentral\s+americ(?:a|an)\b", "Central America"),
    (r"\blatin\s+americ(?:a|an)\b", "South America"),
    (r"\bmiddle\s+east(?:ern)?\b", "Middle East"),
    (r"\boceani(?:a|an)\b", "Oceania"),
    (r"\bcaribbean\b", "Caribbean"),
    (r"\bglobal(?:ly)?\b", "Global"),
    (r"\bworld\s*wide\b", "Global"),
    (r"\ball\s+countr", "Global"),
    (r"\bantarctic(?:a|an)?\b", "Antarctica"),
    (r"\barctic\b", "Arctic"),
]


def normalize_region(text: str) -> Optional[str]:
    """Parse free-text and return canonical region name, or None.

    Examples:
        "European"     → "Europe"
        "South Asian"  → "South Asia"
        "ASEAN"        → "ASEAN"
        "EU"           → "Europe"
        "global"       → "Global"
        "Antarctica"   → "Antarctica"
    """
    text_lower = text.lower().strip()
    for pattern, name in _REGION_PATTERNS:
        if re.search(pattern, text_lower):
            return name
    return None


# ═══════════════════════════════════════════════════════════════════
#  RESOLVE REGION → AVAILABLE COUNTRY LIST
# ═══════════════════════════════════════════════════════════════════

def resolve_region_countries(
    region_name: Optional[str],
    available: set[str] | None = None,
) -> dict:
    """Resolve a region name to a list of countries in the dataset.

    Returns dict with:
        ok:        bool   — True if we have data for this region
        region:    str    — canonical region name
        countries: list   — country names in the dataset (may be empty)
        error:     str|None — human-readable error when ok=False

    Special cases:
        region_name is None  → returns ALL available countries ("Global")
        region_name is "Global" → same
        region not in mapping → error
        region mapped but no intersection with dataset → error
    """
    if available is None:
        available = AVAILABLE_COUNTRIES

    # Global / None → return everything
    if region_name is None or region_name == "Global":
        countries = sorted(available)
        return {
            "ok": True,
            "region": "Global",
            "countries": countries,
        }

    # Look up the region
    region_list = REGION_COUNTRIES.get(region_name)
    if region_list is None:
        return {
            "ok": False,
            "region": region_name,
            "countries": [],
            "error": (
                f"'{region_name}' is not a recognised region in our system.\n"
                f"Supported regions: {', '.join(sorted(REGION_COUNTRIES.keys()))}"
            ),
        }

    # Intersect with available data
    matched = sorted([c for c in region_list if c in available])
    if not matched:
        return {
            "ok": False,
            "region": region_name,
            "countries": [],
            "error": (
                f"No pollution data is available for any country in {region_name}.\n"
                f"Our dataset covers {len(available)} countries; "
                f"none match the {region_name} region list."
            ),
        }

    return {
        "ok": True,
        "region": region_name,
        "countries": matched,
    }
