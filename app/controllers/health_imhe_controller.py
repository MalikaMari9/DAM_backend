from app.repositories.health_imhe_repo import (
    list_imhe,
    list_locations,
    summary,
    country_summary,
    list_ages,
    list_sexes,
    list_causes,
)


def get_imhe_list(filters, limit: int, offset: int):
    return list_imhe(filters, limit=limit, offset=offset)


def get_imhe_locations(filters):
    return list_locations(filters)


def get_imhe_summary():
    return summary()


def get_imhe_country_summary(filters):
    return country_summary(filters)


def get_imhe_ages(filters):
    return list_ages(filters)


def get_imhe_sexes(filters):
    return list_sexes(filters)


def get_imhe_causes(filters):
    return list_causes(filters)
