"""Rule-based intent router + entity extractor for the chat API.

Replaces fragile semantic-only matching with keyword rules that fire first.
Falls back to sentence-transformer similarity only when no rule matches.

Intents:
    PM25_FORECAST, PM25_CHANGE, HEALTH_DEATHS, HEALTH_RATE, HEALTH_DALYS,
    TOP_DISEASES, SCENARIO_PM25_CHANGE, COMPARE_HEALTH,
    TREND_PM25, RISK_LEVEL, RISK_RANKING, HIGHEST_RISK_COUNTRY,
    EXPLAINABILITY, BEST_MONTH, WORST_MONTH, UNKNOWN
"""

import re
from typing import Optional

try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    SentenceTransformer = None
    util = None


# ═══════════════════════════════════════════════════════════════════
#  ASEAN COUNTRY LIST
# ═══════════════════════════════════════════════════════════════════

ASEAN_COUNTRIES = [
    "Brunei", "Cambodia", "Indonesia", "Laos", "Malaysia",
    "Myanmar", "Philippines", "Singapore", "Thailand", "Vietnam",
]


# ═══════════════════════════════════════════════════════════════════
#  SCENARIO DIRECTION KEYWORDS
# ═══════════════════════════════════════════════════════════════════

INCREASE_KEYWORDS = [
    "rise", "rises", "rising", "increase", "increases", "increasing",
    "higher", "go up", "goes up", "up by", "worsen", "worsens",
    "worse", "spike", "spikes", "grow", "grows",
]

DECREASE_KEYWORDS = [
    "reduce", "reduces", "reduction", "decrease", "decreases",
    "lower", "lowered", "go down", "goes down", "down by",
    "cut", "cuts", "drop", "drops", "prevent", "save",
    "meet", "meets", "guideline",
]


# ═══════════════════════════════════════════════════════════════════
#  INTENT RULES — keyword patterns (checked in priority order)
# ═══════════════════════════════════════════════════════════════════

INTENT_RULES: list[tuple[str, list[str], list[str] | None]] = [

    # ══════════════════════════════════════════════════════
    #  PRIORITY A — must override everything else
    # ══════════════════════════════════════════════════════

    # 1) Scenario (has %, "what if", reduce/increase by)
    ("SCENARIO_PM25_CHANGE", [
        r"\d+\s*%",                            # "15%"
        r"\d+\s+percent",                      # "15 percent"
        r"\b(rise|increase|grow)[sd]?\s+by\s+\d(?!\d{3})",
        r"\b(reduce|decrease|drop|cut|lower)\w*\s+by\s+\d(?!\d{3})",
        r"\breduce\b", r"\breduction\b",
        r"\bcuts?\s+(pm|pollution)\b",
        r"\bdrop\s+(pm|pollution)\b",
        r"\blower\s*by\b", r"\braise\s*by\b",
        r"\bif\b.*\bredu", r"\bwhat\s+if\b",
        r"\bwhat\s+happens?\b",
        r"\bhow\s+many\s+(deaths?|lives?)\s+(saved|prevented|happen)",
        r"\bbaseline\s+vs\b",
        r"\bsensitive\s+to\s+a\s+\d",          # "sensitive to a 5% reduction"
        r"\bmarginal\s+death",
        r"\bwho\s+guideline\b",
        r"\bstays?\s+at\b",
        r"\bdrops?\s+below\b",
    ], None),

    # 2) Sensitivity (no specific %, asks about elasticity/sensitivity globally)
    ("SENSITIVITY_PM25_DEATHS", [
        r"\bsensitiv\w*\s+(?:to|of)\s+pm",
        r"\bsensitiv\w*\s+(?:to|of)\s+pollution",
        r"\bmost\s+sensitive\b",
        r"\belasticity\b",
        r"\bper\s+1\s*(?:ug|µg|microgram)",
        r"\bmarginal\s+effect\b",
        r"\bdeaths?\s+per\s+(?:ug|µg|unit)\b",
    ], None),

    # 3) Lowest health burden
    ("LOWEST_HEALTH_BURDEN", [
        r"\blowest\s+(?:health\s+)?burden\b",
        r"\bleast\s+(?:health\s+)?burden\b",
        r"\blowest\s+deaths?\b",
        r"\bleast\s+deaths?\b",
        r"\bfewest\s+deaths?\b",
        r"\blowest\s+mortality\b",
        r"\blowest\s+dalys?\b",
        r"\bleast\s+dalys?\b",
    ], None),

    # 4) Fastest improvement
    ("FASTEST_IMPROVEMENT_PM25", [
        r"\bimproving\s+fastest\b",
        r"\bfastest\s+improv",
        r"\bmost\s+improved\b",
        r"\bimproved?\s+most\b",
        r"\bcleaner\s+fastest\b",
        r"\bgetting\s+cleaner\s+fast",
        r"\b(worse|worsening)\s+fastest\b",
        r"\bgetting\s+worse\s+fast",
    ], None),

    # 5) Stability / volatility ranking
    ("STABILITY_PM25", [
        r"\bmost\s+stable\b",
        r"\bleast\s+stable\b",
        r"\bstable\s+(?:pollution\s+)?pattern\b",
        r"\bmost\s+volatile\b",
        r"\bleast\s+volatile\b",
        r"\bvolatil",
        r"\bstable\s+or\s+volatile\b",
    ], None),

    # 6) PM2.5 ranking (by level, not risk score)
    ("RANK_PM25", [
        r"\btop\s+\d+\s+(most\s+)?polluted\b",
        r"\bhighest\s+pm2\.?5\b",
        r"\blowest\s+pm2\.?5\b",
        r"\brank\w*\s+by\s+pm2?\.?5?\b",
        r"\brank\w*\s+by\s+pollution\b",
        r"\bmost\s+polluted\b",
        r"\bleast\s+polluted\b",
        r"\bcleanest\b",
    ], None),

    # 7) Deaths change year-over-year
    ("DEATHS_CHANGE_YOY", [
        r"\bdeaths?\s+(increase|decrease|change|grew|dropped)\w*\s+(compared|vs|versus|from)\b",
        r"\b(increase|decrease|change)\w*\s+in\s+deaths?\b",
        r"\byoy\s+deaths?\b",
        r"\bdeaths?\s+yoy\b",
        r"\bdeaths?\s+this\s+year\s+vs\b",
        r"\bpollution\s+deaths?\s+(increase|decrease)\w*\s+(compared|vs)\b",
        r"\bdeaths?\s+(increase|decrease)\w*.*\b(compared|last\s+year)\b",
    ], None),

    # ══════════════════════════════════════════════════════
    #  PRIORITY B — standard intents
    # ══════════════════════════════════════════════════════

    # 8) Risk ranking (by risk SCORE, not PM2.5 level)
    ("RISK_RANKING", [
        r"\branke?d?\s+by\s+risk\b",
        r"\branking\b",
        r"\brisk\s+ranking\b",
        r"\bregional\s+risk\b",
        r"\bacross\s+all\b",
        r"\bshow\s+countries\b",
        r"\branke?d?\b",
        r"\brank\w*\s+by\s+(?:death|mortality)\b",
        r"\brank\w*\s+by\s+death\s+rate\b",
    ], None),

    # 9) Highest risk country (risk score ONLY — no "most polluted")
    ("HIGHEST_RISK_COUNTRY", [
        r"\bhighest\s+risk(?:\s+score)?\b",
        r"\bhighest\s+pollution\s+risk\b",
        r"\blowest\s+risk(?:\s+score)?\b",
        r"\bmost\s+dangerous\b",
        r"\bgetting\s+(cleaner|worse)\b.*\bregion\b",
        r"\boverall\b.*\bregion\b",
    ], None),

    # 10) DALYs
    ("HEALTH_DALYS", [
        r"\bdalys?\b",
        r"\bdisability[- ]adjusted\b",
    ], None),

    # 11) Explainability
    ("EXPLAINABILITY", [
        r"\bwhy\s+is\b",
        r"\bwhat\s+(are\s+the\s+)?main\s+drivers?\b",
        r"\bfactors?\s+contribut",
        r"\bwhat\s+features?\b",
        r"\bwhat\s+assumptions?\b",
        r"\bhow\s+reliable\b",
        r"\bhow\s+certain\b",
        r"\bwhy\s+does\b",
        r"\bwhy\s+(is\s+)?confidence\b",
        r"\bnonlinear\b",
        r"\bdiminishing\s+returns\b",
        r"\bstructural\s+break\b",
    ], None),

    # 12) Risk Level (single country)
    ("RISK_LEVEL", [
        r"\brisk\s+level\b",
        r"\brisk\s+tier\b",
        r"\bhigh\s+risk\b",
        r"\bmoderate\s+risk\b",
        r"\bred\s+zone\b",
        r"\brisk\s+score\b",
    ], None),

    # 13) Trend (direction over time — NO "stable/volatile" triggers)
    ("TREND_PM25", [
        r"\btrend\b", r"\btrajectory\b",
        r"\bimproving\b", r"\bimproved\b",
        r"\bworsening\b",
        r"\bimproving\s+or\s+worsening\b",
        r"\bincreasing\b", r"\bdecreasing\b",
        r"\bgetting\s+(better|worse|cleaner)\b",
        r"\bover\s+the\s+years?\b",
        r"\bover\s+time\b",
        r"\bover\s+the\s+next\b",
        r"\byear\s+over\s+year\b",
        r"\bprojection\b", r"\bprojected\b",
        r"\bgrowth\s+rate\b",
        r"\b\d+[- ]year\b",
        r"\bphase\b",
        r"\bregime\b",
        r"\bpercentage\s+(increase|decrease)\b",
        r"20\d{2}[\u2013-]20\d{2}\b",
    ], None),

    # 14) PM2.5 change year-to-year (MUST be before COMPARE — year vs year is more specific)
    ("PM25_CHANGE", [
        r"\bfrom\s+20\d{2}\s+to\s+20\d{2}\b",
        r"\bbetween\s+20\d{2}\s+and\s+20\d{2}\b",
        r"\bsince\s+20\d{2}\b",
        r"\bchange\b",
        r"\bdifference\b",
        r"\b20\d{2}\s+vs\s+20\d{2}\b",
        r"\boutlook\b",
    ], None),

    # 15) Compare (needs 2 countries)
    ("COMPARE_HEALTH", [
        r"\bcompare\b", r"\bvs\b", r"\bversus\b",
    ], None),

    # 16) Health rate (MUST be before HEALTH_DEATHS — "death rate" is more specific)
    ("HEALTH_RATE", [
        r"\bper\s+100[,.]?000\b",
        r"\bdeath\s+rate\b", r"\bmortality\s+rate\b",
        r"\bper\s+capita\b", r"\bper\s+lakh\b",
    ], None),

    # 17) Health deaths (broad — catches "deaths", "mortality")
    ("HEALTH_DEATHS", [
        r"\bdeaths?\b", r"\bmortality\b",
        r"\battribut", r"\bdie\b", r"\bkill",
        r"\bhow\s+many\s+(people\s+)?die",
        r"\bhealth\s+(risk|impact|burden|effect)\b",
        r"\bconfidence\s+interval\b",
    ], None),

    # 18) Top diseases
    ("TOP_DISEASES", [
        r"\btop\s+\d*\s*diseases?\b",
        r"\bbreakdown\b",
        r"\bcaused\s+by\b",
        r"\bwhich\s+diseases?\b",
        r"\bdisease\s+list\b",
        r"\bdisease\s+burden\b",
        r"\bcontribute\s+most\b",
        r"\blinked\s+to\s+pollution\b",
        r"\bsensitive\b.*\bdisease\b",
        r"\bdisease\b.*\bsensitive\b",
    ], None),

    # ── Best / worst month ──
    ("BEST_MONTH", [
        r"\bbest\s+(month|time|period)\b",
        r"\bcleanest\s+(month|air)\b",
        r"\bwhen\s+to\s+(visit|travel)\b",
        r"\bsafest\s+month\b",
        r"\bmonthly\s+(breakdown|data|prediction)\b",
    ], None),

    ("WORST_MONTH", [
        r"\bworst\s+(month|time|period)\b",
        r"\bmost\s+polluted\s+month\b",
        r"\bavoid\s+visiting\b",
        r"\bpeak\s+pollution\b",
    ], None),
]


# ── Semantic fallback intent examples ──

INTENT_EXAMPLES = {
    'PM25_FORECAST': [
        "What is the PM2.5 level?",
        "Air pollution forecast",
        "Predict air quality",
        "How polluted will it be?",
        "PM2.5 concentration?",
        "AQI forecast",
    ],
    'HEALTH_DEATHS': [
        "How many people die from pollution?",
        "Health impact of PM2.5",
        "Mortality from air quality",
        "Death toll from air pollution",
    ],
    'SCENARIO_PM25_CHANGE': [
        "What if PM2.5 reduces by 15%?",
        "How many deaths if pollution drops 20%?",
    ],
    'TREND_PM25': [
        "Is air quality improving?",
        "Pollution trend over time",
    ],
}


# ═══════════════════════════════════════════════════════════════════
#  ENTITY EXTRACTION
# ═══════════════════════════════════════════════════════════════════

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

# Intents that do NOT require a country
COUNTRY_OPTIONAL_INTENTS = {
    "RISK_RANKING", "HIGHEST_RISK_COUNTRY", "list_countries",
    "SCENARIO_PM25_CHANGE", "EXPLAINABILITY", "HEALTH_DALYS",
    "RANK_PM25", "STABILITY_PM25", "FASTEST_IMPROVEMENT_PM25",
    "LOWEST_HEALTH_BURDEN", "SENSITIVITY_PM25_DEATHS", "DEATHS_CHANGE_YOY",
}


class QueryParser:
    """Rule-based intent router with semantic fallback."""

    def __init__(self, available_countries: list):
        # Sentence-transformer for fallback only
        self.model = None
        if SentenceTransformer is not None:
            print("  [INFO] Loading sentence-transformer model...")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            print("  [OK] Sentence-transformer loaded!")
        else:
            print("  [WARN] sentence_transformers not installed; using rule-based routing only.")

        # Pre-compute intent embeddings for fallback
        self.intent_embeddings = {}
        self.intent_examples = {}
        for intent, examples in INTENT_EXAMPLES.items():
            self.intent_examples[intent] = examples
            if self.model is not None:
                self.intent_embeddings[intent] = self.model.encode(examples, convert_to_tensor=True)

        # Build country lookup
        self.country_map = {}
        for c in available_countries:
            self.country_map[c.lower()] = c
            parts = c.lower().split()
            for part in parts:
                if len(part) > 3:
                    self.country_map[part] = c

        print(f"  [OK] Query parser ready ({len(INTENT_RULES)} rule intents, {len(available_countries)} countries)")

    def parse(self, message: str, history: Optional[list] = None) -> dict:
        """Parse natural language → structured query with intent + entities."""
        msg_lower = message.lower().strip()

        # ── Extract entities ──
        countries = self._extract_countries(msg_lower)
        years = self._extract_years(msg_lower)
        year = years[-1] if years else None
        year_range = (years[0], years[1]) if len(years) >= 2 else None
        month = self._extract_month(msg_lower)
        percent = self._extract_percent(msg_lower)
        percent_sign = self._extract_percent_sign(msg_lower, percent)
        age_group = self._extract_age_group(msg_lower)
        disease = self._extract_disease(msg_lower)
        region = self._extract_region(msg_lower)

        # ── Detect intent (rules first, then semantic fallback) ──
        intent, confidence, matched_rule = self._detect_intent_rules(msg_lower, countries)

        if intent is None:
            intent, confidence, matched_rule = self._detect_intent_semantic(message)

        # ── Special overrides ──
        # PM25_CHANGE needs 2 years; if only 1 year, fall to PM25_FORECAST
        if intent == "PM25_CHANGE" and year_range is None:
            intent = "PM25_FORECAST"

        # COMPARE_HEALTH needs 2 countries
        if intent == "COMPARE_HEALTH" and len(countries) < 2:
            pass  # handler will ask for clarification

        # Monthly override
        if intent == "PM25_FORECAST" and month is not None:
            intent = "PM25_FORECAST_MONTHLY"

        # ── Backfill from history ──
        if history:
            for hist_msg in reversed(history):
                if hist_msg.get('role') == 'user':
                    h_text = hist_msg.get('content', '').lower().strip()
                    if not countries:
                        countries = self._extract_countries(h_text)
                    if year is None:
                        h_years = self._extract_years(h_text)
                        if h_years:
                            year = h_years[-1]
                    if month is None:
                        month = self._extract_month(h_text)
                    if percent is None:
                        percent = self._extract_percent(h_text)
                    break

        # Default year → 2026
        if year is None:
            year = 2026

        return {
            'intent': intent,
            'intent_confidence': round(confidence, 3),
            'matched_rule': matched_rule,
            'countries': countries,
            'country': countries[0] if countries else None,
            'year': year,
            'year_range': year_range,
            'month': month,
            'percent': percent,
            'percent_sign': percent_sign,          # +1 or -1
            'age_group': age_group,
            'disease': disease,
            'region': region,
            'raw_message': message,
        }

    # ── Rule-based detection ──────────────────────────────────────

    def _detect_intent_rules(
        self, msg: str, countries: list
    ) -> tuple[str | None, float, str]:
        for intent, patterns, requires in INTENT_RULES:
            matched_pattern = None
            for pat in patterns:
                if re.search(pat, msg, re.IGNORECASE):
                    matched_pattern = pat
                    break

            if matched_pattern is None:
                continue

            if requires:
                if not all(re.search(r, msg, re.IGNORECASE) for r in requires):
                    continue

            # COMPARE_HEALTH needs 2 countries
            if intent == "COMPARE_HEALTH" and len(countries) < 2:
                return intent, 0.6, matched_pattern

            return intent, 0.95, matched_pattern

        return None, 0.0, ""

    # ── Semantic fallback ─────────────────────────────────────────

    def _detect_intent_semantic(self, message: str) -> tuple[str, float, str]:
        if self.model is None:
            return "PM25_FORECAST", 0.3, ""

        query_emb = self.model.encode(message, convert_to_tensor=True)
        best_intent = "PM25_FORECAST"
        best_score = 0.0
        best_example = ""

        for intent, embeddings in self.intent_embeddings.items():
            scores = util.cos_sim(query_emb, embeddings)[0]
            max_idx = int(scores.argmax())
            max_score = float(scores[max_idx])
            if max_score > best_score:
                best_score = max_score
                best_intent = intent
                best_example = self.intent_examples[intent][max_idx]

        if best_score < 0.25:
            best_intent = "PM25_FORECAST"

        return best_intent, best_score, best_example

    # ── Entity extractors ─────────────────────────────────────────

    def _extract_countries(self, msg: str) -> list:
        found = []
        sorted_keys = sorted(self.country_map.keys(), key=len, reverse=True)
        masked_msg = msg
        for key in sorted_keys:
            pattern = r'\b' + re.escape(key) + r'\b'
            if re.search(pattern, masked_msg):
                proper_name = self.country_map[key]
                if proper_name not in found:
                    found.append(proper_name)
                masked_msg = re.sub(pattern, " [MATCHED] ", masked_msg)
        return found

    def _extract_years(self, msg: str) -> list[int]:
        from datetime import datetime
        current_year = datetime.now().year

        years = [int(y) for y in re.findall(r'\b(20[0-4]\d)\b', msg)]

        # Relative year references
        if re.search(r'\bnext\s+year\b', msg):
            years.append(current_year + 1)
        if re.search(r'\bthis\s+year\b', msg):
            years.append(current_year)
        if re.search(r'\blast\s+year\b', msg):
            years.append(current_year - 1)

        # "in N years" → current_year + N
        m_in = re.search(r'\bin\s+(\d+)\s+years?\b', msg)
        if m_in:
            years.append(current_year + int(m_in.group(1)))

        # "since 20XX" → year range from 20XX to current_year
        m_since = re.search(r'\bsince\s+(20[0-4]\d)\b', msg)
        if m_since:
            years.append(int(m_since.group(1)))
            years.append(current_year)

        return sorted(set(years))

    def _extract_month(self, msg: str) -> Optional[int]:
        for name, num in MONTH_MAP.items():
            if re.search(r'\b' + re.escape(name) + r'\b', msg):
                return num
        return None

    def _extract_percent(self, msg: str) -> Optional[float]:
        """Extract percentage value (always positive). Sign determined separately."""
        m = re.search(r'(\d+(?:\.\d+)?)\s*%', msg)
        if m:
            return float(m.group(1))
        m = re.search(r'by\s+(\d+(?:\.\d+)?)\s+percent', msg)
        if m:
            return float(m.group(1))
        return None

    def _extract_percent_sign(self, msg: str, percent: Optional[float]) -> int:
        """Determine if the scenario is an increase (+1) or decrease (-1).

        Uses proximity of direction keywords to the percent token.
        Default: -1 (decrease) only if explicit decrease keyword present.
        """
        if percent is None:
            # No percent — still check for direction words
            for kw in DECREASE_KEYWORDS:
                if kw in msg:
                    return -1
            for kw in INCREASE_KEYWORDS:
                if kw in msg:
                    return +1
            return -1  # default

        # Find positions of keywords relative to the percent token
        pct_match = re.search(r'\d+(?:\.\d+)?\s*(?:%|percent)', msg)
        pct_pos = pct_match.start() if pct_match else len(msg) // 2

        inc_dist = float('inf')
        dec_dist = float('inf')

        for kw in INCREASE_KEYWORDS:
            idx = msg.find(kw)
            if idx >= 0:
                inc_dist = min(inc_dist, abs(idx - pct_pos))

        for kw in DECREASE_KEYWORDS:
            idx = msg.find(kw)
            if idx >= 0:
                dec_dist = min(dec_dist, abs(idx - pct_pos))

        if inc_dist < dec_dist:
            return +1
        elif dec_dist < inc_dist:
            return -1
        else:
            # Both same distance or neither found — check for any keyword
            for kw in INCREASE_KEYWORDS:
                if kw in msg:
                    return +1
            for kw in DECREASE_KEYWORDS:
                if kw in msg:
                    return -1
            return -1  # default to decrease

    def _extract_region(self, msg: str) -> Optional[str]:
        """Extract region name using region_resolver.normalize_region()."""
        from region_resolver import normalize_region
        return normalize_region(msg)

    def _extract_age_group(self, msg: str) -> Optional[str]:
        for group, keywords in AGE_KEYWORDS.items():
            for kw in keywords:
                if kw in msg:
                    return group
        return None

    def _extract_disease(self, msg: str) -> Optional[str]:
        for disease_name, keywords in DISEASE_KEYWORDS.items():
            for kw in keywords:
                if kw in msg:
                    return disease_name
        return None
