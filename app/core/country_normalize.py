import re

_ALIASES = {
    "united states of america": "United States",
    "usa": "United States",
    "u.s.a.": "United States",
    "u.s.": "United States",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "united kingdom of great britain and northern ireland": "United Kingdom",
    "hong kong sar": "Hong Kong",
    "hong kong, china": "Hong Kong",
    "viet nam": "Vietnam",
    "lao people's democratic republic": "Laos",
    "cote d'ivoire": "Ivory Coast",
    "c\u00f4te d'ivoire": "Ivory Coast",
    "c\u00f4te d\u2019ivoire": "Ivory Coast",
    "republic of korea": "South Korea",
    "democratic people's republic of korea": "North Korea",
    "russian federation": "Russia",
    "iran (islamic republic of)": "Iran",
    "bolivia (plurinational state of)": "Bolivia",
    "venezuela (bolivarian republic of)": "Venezuela",
    "tanzania, united republic of": "Tanzania",
    "czechia": "Czech Republic",
    "democratic republic of the congo": "Republic of the Congo",
    "republic of the congo": "Republic of the Congo",
    "republic of moldova": "Moldova",
    "syrian arab republic": "Syria",
    "t\u00fcrkiye": "Turkey",
    "t\u221a\u00bcrkiye": "Turkey",
    "turkiye": "Turkey",
    "serbia": "Republic of Serbia",
    "north macedonia": "Macedonia",
    "netherlands (kingdom of the)": "Netherlands",
    "united republic of tanzania": "Tanzania",
    "occupied palestinian territory, including east jerusalem": "Palestine",
}


def normalize_country_name(value: str) -> str:
    base = " ".join(value.strip().lower().split())
    return _ALIASES.get(base, value.strip())


def normalize_country_key(value: str) -> str:
    return " ".join(normalize_country_name(value).strip().lower().split())


def country_aliases(value: str) -> list[str]:
    raw = value.strip()
    if not raw:
        return []
    base = " ".join(raw.lower().split())
    canonical = _ALIASES.get(base, raw).strip()
    candidates: list[str] = []

    def _add(candidate: str):
        candidate = candidate.strip()
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    _add(canonical)
    _add(raw)
    for alias, target in _ALIASES.items():
        if target == canonical:
            _add(alias)
    return candidates


def exact_country_regex(value: str) -> dict:
    normalized = normalize_country_name(value)
    return {"$regex": f"^{re.escape(normalized)}$", "$options": "i"}
