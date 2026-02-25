"""Standalone XGBoost PM2.5 inference engine (no MongoDB required)."""

import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path

MONTH_NAMES = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
    'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}

# Seasonal PM2.5 multipliers by region (from UniversalPredictor)
SEASONAL_PATTERNS = {
    "Southeast Asia": {
        1: 1.20, 2: 1.25, 3: 1.20, 4: 1.10, 5: 0.90, 6: 0.80,
        7: 0.75, 8: 0.80, 9: 0.85, 10: 0.95, 11: 1.10, 12: 1.15
    },
    "South Asia": {
        1: 1.30, 2: 1.25, 3: 1.15, 4: 1.10, 5: 1.05, 6: 0.90,
        7: 0.85, 8: 0.85, 9: 0.90, 10: 1.10, 11: 1.25, 12: 1.30
    },
    "East Asia": {
        1: 1.25, 2: 1.20, 3: 1.10, 4: 1.00, 5: 0.95, 6: 0.90,
        7: 0.90, 8: 0.95, 9: 1.00, 10: 1.10, 11: 1.20, 12: 1.25
    },
    "Default": {
        1: 1.15, 2: 1.15, 3: 1.10, 4: 1.05, 5: 0.95, 6: 0.90,
        7: 0.90, 8: 0.90, 9: 0.95, 10: 1.05, 11: 1.10, 12: 1.15
    }
}

REGION_MAP = {
    "Southeast Asia": ["Myanmar", "Thailand", "Vietnam", "Laos", "Cambodia", "Malaysia", "Singapore", "Indonesia", "Philippines"],
    "South Asia": ["India", "Bangladesh", "Pakistan", "Sri Lanka", "Nepal", "Afghanistan", "Bhutan"],
    "East Asia": ["China", "Japan", "Korea", "Taiwan", "Mongolia"],
}

class PM25Predictor:
    """XGBoost PM2.5 prediction engine."""

    TMREL = 5.0

    def __init__(self, model_path: str, history_path: str):
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)

        with open(history_path, 'r') as f:
            self.history = json.load(f)

        self.countries = sorted(self.history.keys())

    def get_countries(self):
        """Return list of available countries with their data range."""
        result = []
        for c in self.countries:
            data = self.history[c]
            if data:
                years = [d['year'] for d in data]
                result.append({
                    'name': c,
                    'start_year': min(years),
                    'end_year': max(years),
                    'data_points': len(years)
                })
        return result

    def _calculate_features(self, history_list, target_year):
        """Calculate 7 features for a target year."""
        unique = {}
        for h in history_list:
            unique[h['year']] = h['pm25']

        df = pd.DataFrame([
            {'year': y, 'pm25': v} for y, v in sorted(unique.items())
        ]).set_index('year')

        if len(df) < 3:
            return None

        try:
            lag_1y = float(df.loc[target_year - 1, 'pm25'])
            lag_3y = float(df.loc[target_year - 3, 'pm25']) if (target_year - 3) in df.index else lag_1y

            if (target_year - 2) in df.index:
                lag_2y = float(df.loc[target_year - 2, 'pm25'])
                yoy_change = lag_1y - lag_2y
                yoy_pct = (yoy_change / lag_2y) if abs(lag_2y) > 0.001 else 0.0
            else:
                yoy_change = 0.0
                yoy_pct = 0.0

            last_3 = df.loc[target_year-3:target_year-1]['pm25']
            roll_3y = float(last_3.mean()) if len(last_3) > 0 else lag_1y

            last_5 = df.loc[target_year-5:target_year-1]['pm25']
            roll_5y = float(last_5.mean()) if len(last_5) > 0 else lag_1y

            features = [lag_1y, lag_3y, yoy_change, yoy_pct, roll_3y, roll_5y, target_year]
            features = [0.0 if pd.isna(x) else float(x) for x in features]
            return np.array([features])

        except KeyError:
            return None

    def predict(self, country: str, target_year: int = 2027):
        """Predict PM2.5 for a country up to target_year using recursive forecasting."""
        if country not in self.history:
            return None

        history = [dict(d) for d in self.history[country]]
        predictions = {}

        for year in range(2020, target_year + 1):
            X = self._calculate_features(history, year)
            if X is None:
                pred = history[-1]['pm25'] if history else 25.0
            else:
                pred = float(self.model.predict(X)[0])
                pred = max(self.TMREL, pred)

            predictions[year] = round(pred, 2)
            history.append({'year': year, 'pm25': pred})

        confidence = self._confidence_level(target_year)

        return {
            'country': country,
            'target_year': target_year,
            'predicted_pm25': predictions[target_year],
            'prediction_path': predictions,
            'unit': 'ug/m3',
            'confidence': confidence,
        }

    def predict_monthly(self, country: str, year: int, month: int):
        """Predict PM2.5 for a specific month using annual prediction + seasonal factor."""
        annual = self.predict(country, year)
        if annual is None:
            return None

        region = self._get_region(country)
        pattern = SEASONAL_PATTERNS[region]
        factor = pattern.get(month, 1.0)
        monthly_pm25 = round(annual['predicted_pm25'] * factor, 2)

        month_name = list(MONTH_NAMES.keys())[month - 1].capitalize()

        return {
            'country': country,
            'year': year,
            'month': month,
            'month_name': month_name,
            'predicted_pm25': monthly_pm25,
            'annual_pm25': annual['predicted_pm25'],
            'seasonal_factor': factor,
            'region': region,
            'unit': 'ug/m3',
            'confidence': annual['confidence'],
        }

    def predict_range(self, country: str, start_year: int, end_year: int):
        """Predict PM2.5 for a range of years."""
        result = self.predict(country, end_year)
        if result is None:
            return None

        filtered = {y: v for y, v in result['prediction_path'].items() if y >= start_year}
        return {
            'country': country,
            'start_year': start_year,
            'end_year': end_year,
            'predictions': filtered,
            'unit': 'ug/m3',
        }

    def _get_region(self, country: str) -> str:
        """Get geographic region for seasonal patterns."""
        for region, countries in REGION_MAP.items():
            if country in countries:
                return region
        return "Default"

    def _confidence_level(self, target_year: int) -> dict:
        """Return confidence metadata — degrades for distant predictions."""
        years_ahead = target_year - 2025  # last known data year
        if years_ahead <= 3:
            return {'level': 'high', 'score': 0.90, 'note': 'Near-term forecast based on recent data'}
        elif years_ahead <= 7:
            return {'level': 'moderate', 'score': 0.70, 'note': 'Medium-term forecast; compounding uncertainty'}
        elif years_ahead <= 12:
            return {'level': 'low', 'score': 0.50, 'note': 'Long-term projection; treat as indicative trend'}
        else:
            return {'level': 'speculative', 'score': 0.30, 'note': 'Very long-range; high uncertainty'}
