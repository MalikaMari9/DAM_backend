"""Semantic query parser for the chat API.

Uses sentence-transformers (all-MiniLM-L6-v2) for intent detection via
cosine similarity, replacing fragile keyword matching.

Entity extraction (country, year, month, age group, disease) remains
regex/keyword-based since those are structured fields.
"""

import re
import numpy as np
from typing import Optional
from sentence_transformers import SentenceTransformer, util


# ═══════════════════════════════════════════
#  INTENT EXAMPLES — add more for better coverage
# ═══════════════════════════════════════════

INTENT_EXAMPLES = {
    'best_month': [
        "What month is the best to travel?",
        "When is the best time to visit?",
        "Which month has the cleanest air?",
        "What is the best time to travel according to air quality?",
        "When should I go there for the least pollution?",
        "Safest month to visit for air quality",
        "Best period to travel based on pollution levels",
        "What time of year has the lowest PM2.5?",
        "When is the air the cleanest?",
        "Ideal month to visit for health reasons",
        "Good time to travel for someone with asthma?",
        "Recommended month to visit with children",
        "Monthly prediction of air pollution",
        "Monthly breakdown of pollution",
        "Show me the monthly data",
        "What is the air quality each month?",
    ],
    'worst_month': [
        "Which month has the worst air quality?",
        "When is pollution the highest?",
        "Most polluted month of the year",
        "What time of year should I avoid visiting?",
        "Worst time to travel because of air pollution",
        "When is the air most dangerous?",
        "Peak pollution period",
        "Months you should avoid traveling due to smog",
    ],
    'trend': [
        "Is air quality improving?",
        "Is pollution getting worse or better?",
        "How has PM2.5 changed over the years?",
        "Air quality trend over time",
        "Is the air getting cleaner?",
        "Year over year pollution change",
        "Historical air quality progression",
        "Has pollution gone up or down?",
        "What is the trajectory of air quality?",
    ],
    'predict_pm25': [
        "What is the PM2.5 level?",
        "Air pollution forecast",
        "Predict air quality for next year",
        "How polluted will it be?",
        "What is the air pollution level?",
        "PM2.5 concentration?",
        "Air quality prediction",
        "What is the expected pollution level?",
        "AQI forecast",
        "How bad is the air?",
        "Particulate matter level",
        "What is the smog level?",
        "What is the PM2.5 in Thailand for 2028?",
        "Show me the PM 2.5 prediction for next year",
    ],
    'predict_pm25_monthly': [
        "What is the PM2.5 level in April?",
        "Air quality in January",
        "Pollution level for March",
        "How bad is the air in July?",
        "PM2.5 for a specific month",
        "Expected pollution in December",
    ],
    'health_risk': [
        "What is the health risk from pollution?",
        "How does air pollution affect health?",
        "Death toll from air quality?",
        "Health impact of PM2.5",
        "How many people die from air pollution?",
        "Disease burden from pollution",
        "Mortality from air quality",
        "Risk of getting sick from pollution",
        "How dangerous is the air for health?",
        "Pollution related health problems",
        "What diseases are caused by pollution?",
        "How does pollution affect children?",
        "Health risk for elderly from air quality",
        "Stroke risk from pollution",
        "Heart disease from air pollution",
        "Respiratory health impact",
        "Cancer risk from PM2.5",
        "Is the air safe for kids?",
    ],
    'list_countries': [
        "Which countries do you have data for?",
        "List all available countries",
        "What countries are covered?",
        "Show me the countries",
        "What data do you have?",
        "Available regions or countries",
    ],
}


# ═══════════════════════════════════════════
#  ENTITY EXTRACTION (regex-based — stays clean)
# ═══════════════════════════════════════════

MONTH_MAP = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
    'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}

AGE_KEYWORDS = {
    'children': ['children', 'child', 'kids', 'kid', 'infant', 'baby', 'babies',
                 'toddler', 'young', 'pediatric', 'under 15', 'under 14'],
    'adults': ['adults', 'adult', 'working age', 'middle age', 'middle-aged'],
    'elderly': ['elderly', 'old people', 'senior', 'seniors', 'aged',
                'over 65', 'retiree', 'geriatric'],
}

DISEASE_KEYWORDS = {
    'Ischemic heart disease': ['heart disease', 'ihd', 'ischemic', 'heart attack', 'cardiac', 'coronary'],
    'Stroke': ['stroke', 'cerebrovascular'],
    'Chronic obstructive pulmonary disease': ['copd', 'chronic obstructive', 'emphysema'],
    'Lower respiratory infections': ['lower respiratory', 'pneumonia', 'lri'],
    'Upper respiratory infections': ['upper respiratory', 'uri', 'sinusitis'],
    'Tracheal, bronchus, and lung cancer': ['lung cancer', 'tracheal cancer', 'bronchus cancer'],
    'Larynx cancer': ['larynx cancer', 'throat cancer', 'laryngeal'],
    'Tuberculosis': ['tuberculosis', 'tb'],
    'Diabetes mellitus': ['diabetes', 'diabetic'],
    'Asthma': ['asthma', 'asthmatic', 'wheezing'],
}


class QueryParser:
    """Semantic query parser using sentence embeddings for intent detection."""

    def __init__(self, available_countries: list):
        print("  [INFO] Loading sentence-transformer model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        print("  [OK] Sentence-transformer loaded!")

        # Pre-compute intent embeddings
        self.intent_embeddings = {}   # {intent: [embeddings]}
        self.intent_examples = {}     # {intent: [example strings]}
        for intent, examples in INTENT_EXAMPLES.items():
            self.intent_embeddings[intent] = self.model.encode(examples, convert_to_tensor=True)
            self.intent_examples[intent] = examples

        # Build country lookup
        self.country_map = {}
        for c in available_countries:
            self.country_map[c.lower()] = c
            parts = c.lower().split()
            for part in parts:
                if len(part) > 3:
                    self.country_map[part] = c

        print(f"  [OK] Query parser ready ({len(INTENT_EXAMPLES)} intents, {len(available_countries)} countries)")

    def parse(self, message: str, history: Optional[list] = None) -> dict:
        """Parse a natural language message into structured query parameters, using history for context."""
        msg_lower = message.lower().strip()

        # Detect intent using semantic similarity
        intent, confidence, matched_example = self._detect_intent(message)

        # Override: if a month is explicitly mentioned and intent is predict_pm25, use monthly
        month = self._extract_month(msg_lower)
        if intent == 'predict_pm25' and month is not None:
            intent = 'predict_pm25_monthly'

        countries = self._extract_countries(msg_lower)
        year = self._extract_year(msg_lower)
        age_group = self._extract_age_group(msg_lower)
        disease = self._extract_disease(msg_lower)

        # Backfill missing entities from history
        if history:
            # Look backwards through user messages
            found_past_user_msg = None
            for hist_msg in reversed(history):
                if hist_msg.get('role') == 'user':
                    found_past_user_msg = hist_msg.get('content', '').lower().strip()
                    h_text = found_past_user_msg
                    
                    if not countries:
                        countries = self._extract_countries(h_text)
                    if year is None:
                        year = self._extract_year(h_text)
                    if month is None:
                        month = self._extract_month(h_text)
                    if age_group is None:
                        age_group = self._extract_age_group(h_text)
                    if disease is None:
                        disease = self._extract_disease(h_text)
                    break  # Only backfill from the IMMEDIATE last user message

            # Inherit intent if the current message is a short follow-up
            if found_past_user_msg and len(msg_lower.split()) <= 8 and confidence < 0.75:
                past_intent, past_conf, past_matched = self._detect_intent(found_past_user_msg)
                # Apply same monthly override for past intent to make sure it carries over
                past_month = self._extract_month(found_past_user_msg)
                if past_intent == 'predict_pm25' and (month is not None or past_month is not None):
                    past_intent = 'predict_pm25_monthly'

                if past_conf > confidence:
                    intent = past_intent
                    confidence = past_conf
                    matched_example = f"(Inherited) {past_matched}"

        result = {
            'intent': intent,
            'intent_confidence': round(confidence, 3),
            'matched_example': matched_example,
            'countries': countries,
            'country': countries[0] if countries else None,  # Legacy support
            'year': year,
            'month': month,
            'age_group': age_group,
            'disease': disease,
            'raw_message': message,
        }

        # Default year if not found
        if result['year'] is None:
            result['year'] = 2027

        return result

    def _detect_intent(self, message: str) -> tuple:
        """Detect intent using cosine similarity against example embeddings.

        Returns (intent_name, confidence_score, closest_example)
        """
        query_embedding = self.model.encode(message, convert_to_tensor=True)

        best_intent = 'predict_pm25'
        best_score = 0.0
        best_example = ''

        for intent, embeddings in self.intent_embeddings.items():
            # Compute cosine similarity with all examples for this intent
            scores = util.cos_sim(query_embedding, embeddings)[0]
            max_idx = int(scores.argmax())
            max_score = float(scores[max_idx])

            if max_score > best_score:
                best_score = max_score
                best_intent = intent
                best_example = self.intent_examples[intent][max_idx]

        # Penalize best_month/worst_month if the user didn't mention 'month' or 'time' or specific months
        month_keywords = ['month', 'when', 'time', 'period', 'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
        if best_intent in ('best_month', 'worst_month'):
            msg_lower = message.lower()
            if not any(k in msg_lower for k in month_keywords):
                best_score -= 0.3  # Heavy penalty
                if best_score < 0.4:
                    best_intent = 'predict_pm25'

        # If confidence is too low, fall back to predict_pm25
        if best_score < 0.25:
            best_intent = 'predict_pm25'

        return best_intent, best_score, best_example

    def _extract_countries(self, msg: str) -> list:
        """Extract ALL country names found in message."""
        found = []
        # Sort countries by length (longest first)
        sorted_keys = sorted(self.country_map.keys(), key=len, reverse=True)
        
        masked_msg = msg
        for key in sorted_keys:
            pattern = r'\b' + re.escape(key) + r'\b'
            if re.search(pattern, masked_msg):
                proper_name = self.country_map[key]
                if proper_name not in found:
                    found.append(proper_name)
                # Mask to avoid double matching
                masked_msg = re.sub(pattern, " [MATCHED] ", masked_msg)
        
        return found

    def _extract_year(self, msg: str) -> Optional[int]:
        """Extract year from message."""
        years = re.findall(r'\b(20[2-4]\d)\b', msg)
        if years:
            return int(years[-1])
        return None

    def _extract_month(self, msg: str) -> Optional[int]:
        """Extract month from message."""
        for name, num in MONTH_MAP.items():
            pattern = r'\b' + re.escape(name) + r'\b'
            if re.search(pattern, msg):
                return num
        return None

    def _extract_age_group(self, msg: str) -> Optional[str]:
        """Extract age group from message."""
        for group, keywords in AGE_KEYWORDS.items():
            for kw in keywords:
                if kw in msg:
                    return group
        return None

    def _extract_disease(self, msg: str) -> Optional[str]:
        """Extract disease name from message."""
        for disease_name, keywords in DISEASE_KEYWORDS.items():
            for kw in keywords:
                if kw in msg:
                    return disease_name
        return None
