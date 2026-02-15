from app.repositories.health_imhe_repo import (
    list_imhe,
    list_locations,
    summary,
    country_summary,
    list_ages,
    list_sexes,
    list_causes,
    list_measures,
    list_metrics,
    value_percentiles,
    value_percentiles_dense_years,
    trend_by_year,
)
from app.repositories.pollution_openaq_repo import country_coverage_avg


_COUNTRY_ALIASES = {
    "united states of america": "united states",
    "russian federation": "russia",
    "iran (islamic republic of)": "iran",
    "bolivia (plurinational state of)": "bolivia",
    "venezuela (bolivarian republic of)": "venezuela",
    "tanzania, united republic of": "tanzania",
    "viet nam": "vietnam",
    "lao people's democratic republic": "laos",
    "cote d'ivoire": "ivory coast",
    "republic of korea": "south korea",
    "democratic people's republic of korea": "north korea",
    "hong kong sar": "hong kong",
    "hong kong, china": "hong kong",
}


def _normalize_country_name(value: str) -> str:
    base = " ".join(value.strip().lower().split())
    return _COUNTRY_ALIASES.get(base, base)


def get_imhe_list(filters, limit: int, offset: int):
    return list_imhe(filters, limit=limit, offset=offset)


def get_imhe_locations(filters):
    return list_locations(filters)


def get_imhe_summary():
    return summary()


def get_imhe_country_summary(filters):
    return country_summary(filters)


def get_imhe_country_summary_with_pollution(filters, pollutant: str = "PM2.5"):
    health_items = country_summary(filters)
    year = filters.get("year")
    if year is None:
        return health_items
    openaq_items = country_coverage_avg(year=year, pollutant=pollutant)
    openaq_map = {
        _normalize_country_name(item["country"]): item.get("pollution_pm25")
        for item in openaq_items
        if item.get("country")
    }
    for item in health_items:
        name = _normalize_country_name(item.get("country", ""))
        item["pollution_pm25"] = openaq_map.get(name)
    return health_items


def get_imhe_ages(filters):
    return list_ages(filters)


def get_imhe_sexes(filters):
    return list_sexes(filters)


def get_imhe_causes(filters):
    return list_causes(filters)


def get_imhe_measures(filters):
    return list_measures(filters)


def get_imhe_metrics(filters):
    return list_metrics(filters)


def get_imhe_value_percentiles(filters, pcts: list[float]):
    return value_percentiles(filters, pcts)


def get_imhe_value_percentiles_dense(filters, pcts: list[float], min_countries: int):
    return value_percentiles_dense_years(filters, pcts, min_countries)


def get_imhe_trend(filters):
    return trend_by_year(filters)
