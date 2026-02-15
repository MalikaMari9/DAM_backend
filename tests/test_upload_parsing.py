import pytest

from app.controllers import upload_controller as uc


def _pollution_row(**overrides):
    base = {
        "country_name": "Japan",
        "location_name": "Tokyo",
        "pollutant": "PM2.5",
        "units": "µg/m³",
        "year": 2022.0,
        "value": 8.2,
        "sensor_id": 6518333.0,
        "location_id": 1214466.0,
        "coverage_percent": 37.0,
    }
    base.update(overrides)
    return base


def _imhe_row(**overrides):
    base = {
        "population_group_id": 1.0,
        "population_group_name": "All Population",
        "measure_id": 2.0,
        "measure_name": "Deaths",
        "location_id": 3.0,
        "location_name": "Japan",
        "sex_id": 1.0,
        "sex_name": "Both",
        "age_id": 5.0,
        "age_name": "All ages",
        "cause_id": 7.0,
        "cause_name": "All causes",
        "metric_id": 9.0,
        "metric_name": "Rate",
        "year": 2020.0,
        "val": 12.5,
        "upper": 13.0,
        "lower": 12.0,
    }
    base.update(overrides)
    return base


def test_parse_pollution_rows_accepts_excel_ints():
    rows = [_pollution_row()]
    docs, _label = uc._parse_pollution_rows(rows, expected_country="Japan", row_offset=2)
    assert docs[0]["year"] == 2022
    assert docs[0]["sensor_id"] == 6518333
    assert docs[0]["location_id"] == 1214466


def test_parse_pollution_rows_rejects_non_integer_year():
    rows = [_pollution_row(year=2022.5)]
    with pytest.raises(ValueError) as exc:
        uc._parse_pollution_rows(rows, expected_country="Japan", row_offset=2)
    msg = str(exc.value)
    assert "invalid numeric value" in msg
    assert "year must be an integer" in msg


def test_parse_imhe_rows_accepts_excel_ints():
    rows = [_imhe_row()]
    docs, _label = uc._parse_imhe_rows(rows, expected_country="Japan", row_offset=2)
    assert docs[0]["population_group_id"] == 1
    assert docs[0]["measure_id"] == 2
    assert docs[0]["location_id"] == 3
