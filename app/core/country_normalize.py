import re

_ALIASES = {
    "united states of america": "United States",
    "usa": "United States",
    "u.s.a.": "United States",
    "u.s.": "United States",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "hong kong sar": "Hong Kong",
    "hong kong, china": "Hong Kong",
    "viet nam": "Vietnam",
    "lao people's democratic republic": "Laos",
    "cote d'ivoire": "Ivory Coast",
    "republic of korea": "South Korea",
    "democratic people's republic of korea": "North Korea",
    "russian federation": "Russia",
    "iran (islamic republic of)": "Iran",
    "bolivia (plurinational state of)": "Bolivia",
    "venezuela (bolivarian republic of)": "Venezuela",
    "tanzania, united republic of": "Tanzania",
}


def normalize_country_name(value: str) -> str:
    base = " ".join(value.strip().lower().split())
    return _ALIASES.get(base, value.strip())


def normalize_country_key(value: str) -> str:
    return " ".join(normalize_country_name(value).strip().lower().split())


def exact_country_regex(value: str) -> dict:
    normalized = normalize_country_name(value)
    return {"$regex": f"^{re.escape(normalized)}$", "$options": "i"}
