"""Health risk calculation engine (standalone, no MongoDB)."""

import json
import numpy as np
from pathlib import Path


# GBD 2019 IER parameters
# RR = 1 + alpha * (1 - exp(-gamma * exposure^delta))
IER_PARAMS = {
    'Ischemic heart disease':                    {'alpha': 0.2969, 'gamma': 0.0133, 'delta': 1.0, 'category': 'Cardiovascular'},
    'Stroke':                                    {'alpha': 0.3120, 'gamma': 0.0098, 'delta': 1.0, 'category': 'Cardiovascular'},
    'Chronic obstructive pulmonary disease':      {'alpha': 0.2680, 'gamma': 0.0105, 'delta': 1.0, 'category': 'Respiratory'},
    'Lower respiratory infections':              {'alpha': 0.3570, 'gamma': 0.0154, 'delta': 1.0, 'category': 'Respiratory'},
    'Upper respiratory infections':              {'alpha': 0.1850, 'gamma': 0.0120, 'delta': 1.0, 'category': 'Respiratory'},
    'Tracheal, bronchus, and lung cancer':       {'alpha': 0.4050, 'gamma': 0.0185, 'delta': 1.0, 'category': 'Cancer'},
    'Larynx cancer':                             {'alpha': 0.3200, 'gamma': 0.0160, 'delta': 1.0, 'category': 'Cancer'},
    'Tuberculosis':                              {'alpha': 0.2200, 'gamma': 0.0095, 'delta': 1.0, 'category': 'Infectious'},
    'Diabetes mellitus':                         {'alpha': 0.1650, 'gamma': 0.0088, 'delta': 1.0, 'category': 'Metabolic'},
    'Asthma':                                    {'alpha': 0.2350, 'gamma': 0.0110, 'delta': 1.0, 'category': 'Respiratory'},
}

TMREL = 5.0

AGE_VULNERABILITY = {
    'children': {'label': 'Children (0-14)', 'range': range(0, 15), 'multiplier': 1.3},
    'adults':   {'label': 'Adults (15-64)',   'range': range(15, 65), 'multiplier': 1.0},
    'elderly':  {'label': 'Elderly (65+)',    'range': range(65, 150), 'multiplier': 1.5},
}

AGE_NAME_TO_START = {
    '<1 year': 0, '1-4 years': 1, '5-9 years': 5, '10-14 years': 10,
    '15-19 years': 15, '20-24 years': 20, '25-29 years': 25, '30-34 years': 30,
    '35-39 years': 35, '40-44 years': 40, '45-49 years': 45, '50-54 years': 50,
    '55-59 years': 55, '60-64 years': 60, '65-69 years': 65, '70-74 years': 70,
    '75-79 years': 75, '80-84 years': 80, '85-89 years': 85, '90-94 years': 90,
    '95+ years': 95,
}


# Country name aliases: maps parser names to IHME/GBD names
COUNTRY_ALIASES = {
    'Vietnam': 'Viet Nam',
    'Laos': "Lao People's Democratic Republic",
    'Brunei': 'Brunei Darussalam',
    'South Korea': 'Republic of Korea',
    'North Korea': "Democratic People's Republic of Korea",
    'Iran': 'Iran (Islamic Republic of)',
    'Syria': 'Syrian Arab Republic',
    'Russia': 'Russian Federation',
    'Bolivia': 'Bolivia (Plurinational State of)',
    'Venezuela': 'Venezuela (Bolivarian Republic of)',
    'Tanzania': 'United Republic of Tanzania',
    'Moldova': 'Republic of Moldova',
    'Czech Republic': 'Czechia',
    'Ivory Coast': "Cote d'Ivoire",
    'Congo': 'Democratic Republic of the Congo',
}


def _normalize_country(name: str) -> str:
    """Normalize country name using aliases."""
    return COUNTRY_ALIASES.get(name, name)


class HealthRiskEngine:
    """Health risk calculation engine using IER curves + IHME data."""

    def __init__(self, baseline_path: str, ihme_raw_path: str = None):
        with open(baseline_path, 'r') as f:
            self.baselines = json.load(f)

        self.ihme_raw_path = ihme_raw_path

    def _calc_rr(self, pm25, disease):
        """Calculate Relative Risk using IER curve."""
        params = IER_PARAMS.get(disease)
        if not params:
            return 1.0, 0.0

        exposure = max(0, pm25 - TMREL)
        if exposure <= 0:
            return 1.0, 0.0

        rr = 1.0 + params['alpha'] * (1 - np.exp(-params['gamma'] * (exposure ** params['delta'])))
        af = 1 - (1 / rr)
        return round(float(rr), 4), round(float(af), 4)

    def _get_age_group(self, age_name):
        start = AGE_NAME_TO_START.get(age_name)
        if start is None:
            return None
        for key, info in AGE_VULNERABILITY.items():
            if start in info['range']:
                return key
        return None

    def _get_raw_ihme_records(self, country):
        """Get raw IHME records for a country efficiently."""
        if not self.ihme_raw_path or not Path(self.ihme_raw_path).exists():
            return None

        norm = _normalize_country(country)
        search_names = {country.lower(), norm.lower()}

        records = []
        try:
            with open(self.ihme_raw_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for r in data:
                    loc = r.get('location_name', '')
                    loc_l = loc.lower()
                    if any(s in loc_l or loc_l in s for s in search_names):
                        records.append(r)
                del data
        except MemoryError:
            print("  [WARN] Hit MemoryError loading IHME dataset. Falling back to baselines.")
            return None

        return records if records else None

    def calculate(self, country: str, pm25_level: float, target_year: int):
        """Calculate health risk with age stratification and CIs."""
        result = {
            'country': country,
            'target_year': target_year,
            'pm25_level': pm25_level,
            'excess_exposure': round(max(0, pm25_level - TMREL), 2),
            'tmrel': TMREL,
            'aqi_category': self._aqi_category(pm25_level),
            'total_attributed_deaths': 0,
            'total_ci_lower': 0,
            'total_ci_upper': 0,
            'diseases': [],
            'age_groups': [],
        }

        # Try age-stratified calculation from raw IHME
        raw_records = self._get_raw_ihme_records(country)

        if raw_records:
            result = self._calc_age_stratified(result, raw_records, pm25_level, target_year)
        else:
            # Fallback to aggregated baselines
            result = self._calc_aggregated(result, country, pm25_level, target_year)

        return result

    def _calc_age_stratified(self, result, records, pm25, target_year):
        """Full age-stratified calculation."""
        available_years = sorted(set(r['year'] for r in records))
        closest = min(available_years, key=lambda y: abs(y - target_year))

        year_records = [r for r in records
                        if r['year'] == closest and r.get('measure_name') == 'Deaths']

        age_totals = {}
        disease_totals = {}

        for r in year_records:
            age_name = r.get('age_name', '')
            cause = r.get('cause_name', '')
            val = r.get('val', 0)
            upper = r.get('upper', val)
            lower = r.get('lower', val)

            age_group = self._get_age_group(age_name)
            if not age_group or not cause:
                continue

            rr, af = self._calc_rr(pm25, cause)
            vuln = AGE_VULNERABILITY[age_group]['multiplier']
            adj_af = min(af * vuln, 0.95)

            attr = val * adj_af
            attr_upper = upper * adj_af
            attr_lower = lower * adj_af

            # Age group totals
            if age_group not in age_totals:
                age_totals[age_group] = {
                    'label': AGE_VULNERABILITY[age_group]['label'],
                    'deaths': 0, 'upper': 0, 'lower': 0,
                    'vulnerability': vuln
                }
            age_totals[age_group]['deaths'] += attr
            age_totals[age_group]['upper'] += attr_upper
            age_totals[age_group]['lower'] += attr_lower

            # Disease totals
            if cause not in disease_totals:
                disease_totals[cause] = {
                    'disease': cause,
                    'category': IER_PARAMS.get(cause, {}).get('category', 'Other'),
                    'baseline': 0, 'attributed': 0,
                    'upper': 0, 'lower': 0,
                    'rr': rr, 'af': af
                }
            disease_totals[cause]['baseline'] += val
            disease_totals[cause]['attributed'] += attr
            disease_totals[cause]['upper'] += attr_upper
            disease_totals[cause]['lower'] += attr_lower

        # Build disease list sorted by deaths
        sorted_diseases = sorted(disease_totals.values(), key=lambda x: -x['attributed'])
        for d in sorted_diseases:
            result['diseases'].append({
                'disease': d['disease'],
                'category': d['category'],
                'attributed_deaths': round(d['attributed'], 1),
                'ci_lower': round(d['lower'], 1),
                'ci_upper': round(d['upper'], 1),
                'baseline_deaths': round(d['baseline'], 1),
                'relative_risk': d['rr'],
                'attributable_fraction': d['af'],
            })

        # Build age group list
        total = sum(a['deaths'] for a in age_totals.values())
        sorted_ages = sorted(age_totals.values(), key=lambda x: -x['deaths'])
        for a in sorted_ages:
            pct = (a['deaths'] / total * 100) if total > 0 else 0
            result['age_groups'].append({
                'age_group': a['label'],
                'attributed_deaths': round(a['deaths'], 1),
                'ci_lower': round(a['lower'], 1),
                'ci_upper': round(a['upper'], 1),
                'percentage': round(pct, 1),
                'vulnerability_multiplier': a['vulnerability'],
            })

        result['total_attributed_deaths'] = round(total, 0)
        result['total_ci_lower'] = round(sum(a['lower'] for a in age_totals.values()), 0)
        result['total_ci_upper'] = round(sum(a['upper'] for a in age_totals.values()), 0)
        result['data_note'] = f'Age-stratified (IHME baseline year: {closest})'

        return result

    def _calc_aggregated(self, result, country, pm25, target_year):
        """Fallback: use aggregated baselines."""
        norm = _normalize_country(country)
        baseline = self.baselines.get(country, {}).get(str(target_year))
        if not baseline:
            baseline = self.baselines.get(norm, {}).get(str(target_year))
        if not baseline:
            search_names = {country.lower(), norm.lower()}
            for c in self.baselines:
                c_lower = c.lower()
                if any(s in c_lower or c_lower in s for s in search_names):
                    baseline = self.baselines[c].get(str(target_year))
                    if baseline:
                        break

        # Fallback: try nearest available year
        if not baseline:
            for c_key in [country, norm]:
                year_data = self.baselines.get(c_key, {})
                if year_data:
                    available_years = sorted(year_data.keys(), key=lambda y: abs(int(y) - target_year))
                    if available_years:
                        baseline = year_data[available_years[0]]
                        break

        if not baseline:
            result['data_note'] = 'No health baseline data available'
            return result

        total = 0
        for disease, deaths in baseline.items():
            rr, af = self._calc_rr(pm25, disease)
            if af > 0:
                attr = deaths * af
                total += attr
                result['diseases'].append({
                    'disease': disease,
                    'category': IER_PARAMS.get(disease, {}).get('category', 'Other'),
                    'attributed_deaths': round(attr, 1),
                    'ci_lower': round(attr * 0.6, 1),
                    'ci_upper': round(attr * 1.5, 1),
                    'baseline_deaths': round(deaths, 1),
                    'relative_risk': rr,
                    'attributable_fraction': af,
                })

        result['diseases'].sort(key=lambda x: -x['attributed_deaths'])
        result['total_attributed_deaths'] = round(total, 0)
        result['total_ci_lower'] = round(total * 0.6, 0)
        result['total_ci_upper'] = round(total * 1.5, 0)
        result['data_note'] = 'Aggregated baseline (no age stratification)'

        return result

    def calculate_filtered(self, country: str, pm25_level: float, target_year: int,
                           age_group: str = None, disease_filter: str = None):
        """Calculate health risk with optional age group / disease filtering."""
        full_result = self.calculate(country, pm25_level, target_year)

        if age_group:
            age_label_map = {
                'children': 'Children (0-14)',
                'adults': 'Adults (15-64)',
                'elderly': 'Elderly (65+)',
            }
            target_label = age_label_map.get(age_group)
            if target_label and full_result.get('age_groups'):
                matched = [a for a in full_result['age_groups'] if a['age_group'] == target_label]
                full_result['age_groups'] = matched
                full_result['filter_applied'] = f'Age group: {target_label}'
                if matched:
                    full_result['filtered_deaths'] = matched[0]['attributed_deaths']
                    full_result['filtered_ci_lower'] = matched[0]['ci_lower']
                    full_result['filtered_ci_upper'] = matched[0]['ci_upper']

        if disease_filter:
            disease_lower = disease_filter.lower()
            matched = [d for d in full_result.get('diseases', [])
                       if disease_lower in d['disease'].lower()]
            if matched:
                full_result['diseases'] = matched
                full_result['filter_applied'] = full_result.get('filter_applied', '') + f' Disease: {disease_filter}'

        return full_result

    def get_available_countries(self):
        """Return list of countries with baseline data."""
        return sorted(self.baselines.keys())

    def fuzzy_match_country(self, query: str):
        """Fuzzy match a country name from user input."""
        query_lower = query.lower().strip()
        # Exact match first
        for c in self.baselines:
            if c.lower() == query_lower:
                return c
        # Partial match
        for c in self.baselines:
            if query_lower in c.lower() or c.lower() in query_lower:
                return c
        return None

    def _aqi_category(self, pm25):
        if pm25 < 12:
            return {'level': 'Good', 'color': '#4CAF50'}
        elif pm25 < 35.5:
            return {'level': 'Moderate', 'color': '#FFC107'}
        elif pm25 < 55.5:
            return {'level': 'Unhealthy for Sensitive Groups', 'color': '#FF9800'}
        elif pm25 < 150.5:
            return {'level': 'Unhealthy', 'color': '#F44336'}
        elif pm25 < 250.5:
            return {'level': 'Very Unhealthy', 'color': '#9C27B0'}
        else:
            return {'level': 'Hazardous', 'color': '#7B1FA2'}
