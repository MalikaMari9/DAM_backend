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
from app.core.country_normalize import normalize_country_key


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
        normalize_country_key(item["country"]): item.get("pollution_pm25")
        for item in openaq_items
        if item.get("country")
    }
    for item in health_items:
        name = normalize_country_key(item.get("country", ""))
        value = openaq_map.get(name)
        item["pollution_value"] = value
        item["pollutant"] = pollutant
        if pollutant.strip().upper() == "PM2.5":
            item["pollution_pm25"] = value
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
