"""Formatter — produces exact-template executive output strings.

Each function takes a payload dict and emits a multi-line text block
matching the strict specification.
"""


def format_output(output_type: str, payload: dict) -> str:
    """Dispatch to the correct formatter."""
    formatters = {
        "pollution_forecast": _fmt_pollution,
        "pm25_change": _fmt_pm25_change,
        "health_deaths": _fmt_health_deaths,
        "health_impact": _fmt_health_deaths,
        "health_rate": _fmt_health_rate,
        "top_diseases": _fmt_top_diseases,
        "scenario": _fmt_scenario,
        "compare_health": _fmt_compare_health,
        "trend": _fmt_trend,
        "risk_level": _fmt_risk,
        "risk_ranking": _fmt_risk_ranking,
        "highest_risk": _fmt_highest_risk,
        "health_dalys": _fmt_health_dalys,
        "explainability": _fmt_explainability,
        # New analytics formatters
        "rank_pm25": _fmt_rank_pm25,
        "stability": _fmt_stability,
        "fastest_improving": _fmt_fastest_improving,
        "lowest_health_burden": _fmt_lowest_health_burden,
        "sensitivity": _fmt_sensitivity,
        "deaths_yoy": _fmt_deaths_yoy,
    }
    fn = formatters.get(output_type)
    if fn is None:
        raise ValueError(f"Unknown output type: {output_type}")
    return fn(payload)


# ═══════════════════════════════════════════════════════════════════
#  A) PM25_FORECAST
# ═══════════════════════════════════════════════════════════════════

def _fmt_pollution(p: dict) -> str:
    arrow = p.get("arrow", "\u2192")
    return (
        f"Country: {p['country']}\n"
        f"Pollutant: PM2.5\n"
        f"Forecast Period: {p['year']}\n"
        f"Predicted Level: {p['pm25']:.2f} \u00b5g/m\u00b3\n"
        f"Change vs Last Year: {p['pct_change']:+.1f}% {arrow}\n"
        f"Confidence: {p['confidence_label']} (\u00b1{p['interval']:.1f} \u00b5g/m\u00b3)"
    )


# ═══════════════════════════════════════════════════════════════════
#  B) PM25_CHANGE
# ═══════════════════════════════════════════════════════════════════

def _fmt_pm25_change(p: dict) -> str:
    arrow = p.get("arrow", "\u2192")
    return (
        f"Country: {p['country']}\n"
        f"PM2.5 in {p['year1']}: {p['pm25_y1']:.2f} \u00b5g/m\u00b3\n"
        f"PM2.5 in {p['year2']}: {p['pm25_y2']:.2f} \u00b5g/m\u00b3\n"
        f"Change: {p['abs_change']:+.2f} \u00b5g/m\u00b3 ({p['pct_change']:+.1f}% {arrow})"
    )


# ═══════════════════════════════════════════════════════════════════
#  C) HEALTH_DEATHS
# ═══════════════════════════════════════════════════════════════════

def _fmt_health_deaths(p: dict) -> str:
    lines = [
        f"Country: {p['country']}",
        f"Outcome: Attributable Deaths (Air Pollution)",
        f"Forecast Year: {p['year']}",
        f"PM2.5: {p['pm25']:.2f} \u00b5g/m\u00b3",
        f"Total attributable deaths: {p['deaths']:,.0f} "
        f"(95% CI: {p['ci_low']:,.0f}\u2013{p['ci_high']:,.0f})",
    ]
    diseases = p.get("diseases", [])
    if diseases:
        lines.append("")
        lines.append("Top diseases:")
        for d in diseases[:3]:
            lines.append(f"\u2022 {d['disease']}: {d['deaths']:,.0f} deaths")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
#  D) HEALTH_RATE
# ═══════════════════════════════════════════════════════════════════

def _fmt_health_rate(p: dict) -> str:
    return (
        f"Country: {p['country']}\n"
        f"Year: {p['year']}\n"
        f"Pollution-related death rate per 100,000: {p['rate']:.1f}\n"
        f"(Deaths: {p['deaths']:,.0f}, Baseline deaths pool: {p['population_proxy']:,.0f})"
    )


# ═══════════════════════════════════════════════════════════════════
#  E) TOP_DISEASES
# ═══════════════════════════════════════════════════════════════════

def _fmt_top_diseases(p: dict) -> str:
    lines = [
        f"Country: {p['country']}",
        f"Year: {p['year']}",
        f"Top {len(p['diseases'])} diseases attributable to air pollution:",
    ]
    for d in p["diseases"]:
        lines.append(f"\u2022 {d['disease']}: {d['deaths']:,.0f} deaths")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
#  F) SCENARIO (increase + decrease)
# ═══════════════════════════════════════════════════════════════════

def _fmt_scenario(p: dict) -> str:
    is_increase = p.get("is_increase", False)
    pct = abs(p.get("percent_change", p.get("reduction_pct", 15)))

    if is_increase:
        lines = [
            f"Scenario: PM2.5 increased by {pct:.0f}%",
            f"Country: {p['country']}",
            f"Year: {p['year']}",
            "",
            f"Baseline PM2.5: {p['baseline_pm25']:.2f} \u00b5g/m\u00b3",
            f"Increased PM2.5: {p['scenario_pm25']:.2f} \u00b5g/m\u00b3",
            "",
            f"Baseline Deaths: {p['baseline_deaths']:,.0f}",
            f"Scenario Deaths: {p['scenario_deaths']:,.0f}",
            f"Additional Deaths: {p.get('additional_deaths', 0):,.0f}",
            "",
            f"Confidence: {p['confidence']} (based on pollution CI)",
        ]
    else:
        lines = [
            f"Scenario: PM2.5 reduced by {pct:.0f}%",
            f"Country: {p['country']}",
            f"Year: {p['year']}",
            "",
            f"Baseline PM2.5: {p['baseline_pm25']:.2f} \u00b5g/m\u00b3",
            f"Reduced PM2.5: {p['scenario_pm25']:.2f} \u00b5g/m\u00b3",
            "",
            f"Current Predicted Deaths: {p['baseline_deaths']:,.0f}",
            f"With {pct:.0f}% Reduction: {p['scenario_deaths']:,.0f}",
            f"Estimated Prevented Deaths: {p['prevented_deaths']:,.0f}",
            "",
            f"Confidence: {p['confidence']} (based on pollution CI)",
        ]

    top_diseases = p.get("top_diseases", [])
    if top_diseases:
        lines.append("")
        lines.append("Top diseases still driving burden:")
        for disease in top_diseases:
            lines.append(f"\u2022 {disease}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
#  G) COMPARE_HEALTH
# ═══════════════════════════════════════════════════════════════════

def _fmt_compare_health(p: dict) -> str:
    return (
        f"Comparison for {p['year']}:\n"
        f"\u2022 {p['countryA']}: {p['deathsA']:,.0f} deaths (PM2.5: {p['pm25A']:.2f} \u00b5g/m\u00b3)\n"
        f"\u2022 {p['countryB']}: {p['deathsB']:,.0f} deaths (PM2.5: {p['pm25B']:.2f} \u00b5g/m\u00b3)\n"
        f"Difference: {p['diff']:,.0f} deaths"
    )


# ═══════════════════════════════════════════════════════════════════
#  H) TREND_PM25
# ═══════════════════════════════════════════════════════════════════

def _fmt_trend(p: dict) -> str:
    direction = p.get("direction", "Stable")
    pct = p.get("pct_change", 0)

    if direction == "Decreasing":
        dir_word = "improving"
    elif direction == "Increasing":
        dir_word = "worsening"
    else:
        dir_word = "stable"

    start = p.get("start_year", "?")
    end = p.get("end_year", "?")
    predictions = p.get("predictions", {})

    lines = [
        f"PM2.5 trend for {p['country']} ({start}\u2013{end}):",
        f"Direction: {dir_word}",
    ]

    if predictions:
        years_sorted = sorted(predictions.keys())
        start_val = predictions[years_sorted[0]]
        end_val = predictions[years_sorted[-1]]
        abs_change = end_val - start_val
        lines.append(f"\u2022 {years_sorted[0]}: {start_val:.2f} \u00b5g/m\u00b3")
        lines.append(f"\u2022 {years_sorted[-1]}: {end_val:.2f} \u00b5g/m\u00b3")
        lines.append(f"Change: {abs_change:+.2f} \u00b5g/m\u00b3 ({pct:+.1f}%)")
    else:
        lines.append(f"Change: {pct:+.1f}%")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
#  RISK_LEVEL (single country)
# ═══════════════════════════════════════════════════════════════════

def _fmt_risk(p: dict) -> str:
    return (
        f"Risk Level Classification\n"
        f"Country: {p['country']}\n"
        f"Year: {p['year']}\n"
        f"Predicted PM2.5: {p['pm25']:.2f} \u00b5g/m\u00b3\n"
        f"Risk Level: {p['emoji']} {p['risk_text']}\n"
        f"Expected Health Burden Impact: {p['health_summary']}\n"
        f"Risk Scale: \U0001f7e2 Low, \U0001f7e1 Moderate, \U0001f7e0 High, \U0001f534 Very High"
    )


# ═══════════════════════════════════════════════════════════════════
#  RISK_RANKING (multi-country)
# ═══════════════════════════════════════════════════════════════════

def _fmt_risk_ranking(p: dict) -> str:
    region = p.get("region", "ASEAN")
    year = p.get("year", 2026)
    lines = [f"Top {region} risk scores for {year}:"]
    for i, r in enumerate(p["rankings"], 1):
        lines.append(
            f"  {i}. {r['country']} \u2014 Score: {r['risk_score']:.1f} "
            f"\u2014 PM2.5: {r['pm25']:.2f} \u00b5g/m\u00b3 "
            f"\u2014 {r['emoji']} {r['risk_text']}"
        )
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
#  HIGHEST_RISK_COUNTRY
# ═══════════════════════════════════════════════════════════════════

def _fmt_highest_risk(p: dict) -> str:
    r = p["top"]
    region = p.get("region", "ASEAN")
    year = p.get("year", 2026)
    return (
        f"Highest {region} pollution risk in {year}:\n"
        f"{r['country']} (Score: {r['risk_score']:.1f}, "
        f"PM2.5: {r['pm25']:.2f} \u00b5g/m\u00b3, "
        f"Risk: {r['emoji']} {r['risk_text']})"
    )


# ═══════════════════════════════════════════════════════════════════
#  HEALTH_DALYS (fallback to deaths)
# ═══════════════════════════════════════════════════════════════════

def _fmt_health_dalys(p: dict) -> str:
    if p.get("dalys_available", False):
        return (
            f"Country: {p['country']}\n"
            f"Year: {p['year']}\n"
            f"Predicted DALYs due to PM2.5: {p['dalys']:,.0f}"
        )
    # Fallback
    lines = [
        f"Country: {p['country']}",
        f"Year: {p['year']}",
        "",
        "DALYs are not available in the current dataset.",
        "Here are attributable deaths and rate per 100k instead:",
        "",
        f"Total attributable deaths: {p['deaths']:,.0f} "
        f"(95% CI: {p['ci_low']:,.0f}\u2013{p['ci_high']:,.0f})",
    ]
    diseases = p.get("diseases", [])
    if diseases:
        lines.append("")
        lines.append("Top diseases:")
        for d in diseases[:3]:
            lines.append(f"\u2022 {d['disease']}: {d['deaths']:,.0f} deaths")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
#  EXPLAINABILITY
# ═══════════════════════════════════════════════════════════════════

def _fmt_explainability(p: dict) -> str:
    lines = [
        f"Country: {p['country']}",
        f"Year: {p['year']}",
        "",
    ]

    # Pollution drivers
    poll_drivers = p.get("pollution_drivers", [])
    if poll_drivers:
        lines.append("Main pollution drivers (model feature importances):")
        for d in poll_drivers:
            lines.append(f"\u2022 {d['feature']}: {d['importance']:.1%}")
        lines.append("")

    # Health drivers
    health_drivers = p.get("health_drivers", [])
    if health_drivers:
        lines.append("Health burden drivers (disease breakdown):")
        for d in health_drivers:
            lines.append(f"\u2022 {d['disease']}: {d['deaths']:,.0f} deaths")
        lines.append("")

    # Confidence info
    if p.get("confidence_note"):
        lines.append(f"Confidence: {p['confidence_note']}")

    return "\n".join(lines)


# ═════════════════════════════════════════════════════════════════
#  NEW ANALYTICS FORMATTERS
# ═════════════════════════════════════════════════════════════════

def _fmt_rank_pm25(p: dict) -> str:
    region = p.get("region", "Global")
    year = p.get("year", 2026)
    rankings = p.get("rankings", [])
    top_n = p.get("top_n")
    header = f"Top {top_n} most polluted" if top_n else "PM2.5 ranking"
    lines = [f"{header} in {region} ({year}):"]
    for i, r in enumerate(rankings, 1):
        lines.append(f"  {i}. {r['country']} \u2014 PM2.5: {r['pm25']:.2f} \u00b5g/m\u00b3")
    return "\n".join(lines)


def _fmt_stability(p: dict) -> str:
    region = p.get("region", "Global")
    start = p.get("start_year", 2020)
    end = p.get("end_year", 2030)
    rankings = p.get("rankings", [])
    lines = [f"Pollution stability ranking ({region}, {start}-{end}):"]
    for i, r in enumerate(rankings[:10], 1):
        lines.append(
            f"  {i}. {r['country']} \u2014 CV: {r['cv']:.1f}% "
            f"(mean: {r['mean_pm25']:.1f} \u00b5g/m\u00b3) [{r['label']}]"
        )
    return "\n".join(lines)


def _fmt_fastest_improving(p: dict) -> str:
    region = p.get("region", "Global")
    start = p.get("start_year", 2020)
    end = p.get("end_year", 2030)
    rankings = p.get("rankings", [])
    lines = [f"Fastest improving countries ({region}, {start}-{end}):"]
    for i, r in enumerate(rankings[:10], 1):
        arrow = "\u2193" if r['pct_change'] < 0 else "\u2191"
        lines.append(
            f"  {i}. {r['country']} \u2014 {r['pct_change']:+.1f}% {arrow} "
            f"({r['pm25_start']:.1f} \u2192 {r['pm25_end']:.1f} \u00b5g/m\u00b3)"
        )
    return "\n".join(lines)


def _fmt_lowest_health_burden(p: dict) -> str:
    region = p.get("region", "Global")
    year = p.get("year", 2026)
    metric = p.get("metric", "deaths")
    rankings = p.get("rankings", [])
    lines = [f"Lowest health burden in {region} ({year}, by {metric}):"]
    for i, r in enumerate(rankings[:10], 1):
        lines.append(
            f"  {i}. {r['country']} \u2014 {r['value']:,.0f} {metric} "
            f"(PM2.5: {r['pm25']:.1f} \u00b5g/m\u00b3)"
        )
    return "\n".join(lines)


def _fmt_sensitivity(p: dict) -> str:
    year = p.get("year", 2026)
    delta = p.get("delta_percent", -5)
    avg = p.get("avg_prevented_per_1pct", 0)
    top = p.get("top_sensitive", [])
    lines = [
        f"Sensitivity analysis: deaths per 1% PM2.5 reduction ({year})",
        f"Average across scope: {avg:,.1f} deaths prevented per 1% reduction",
        "",
        "Top 3 most sensitive countries:",
    ]
    for i, r in enumerate(top, 1):
        lines.append(
            f"  {i}. {r['country']} \u2014 {r['prevented_per_1pct']:,.1f} deaths/1% "
            f"(baseline: {r['baseline_deaths']:,.0f} deaths)"
        )
    return "\n".join(lines)


def _fmt_deaths_yoy(p: dict) -> str:
    if p.get("error"):
        return f"Country: {p['country']}\nYear: {p['year']}\n\n{p['error']}"
    lines = [
        f"Deaths year-over-year comparison: {p['country']}",
        f"Current year ({p['year']}): {p['deaths_current']:,.0f} attributed deaths",
        f"Previous year ({p['prev_year']}): {p['deaths_previous']:,.0f} attributed deaths",
        "",
        f"Change: {p['delta']:+,.0f} deaths ({p['pct_change']:+.1f}%)",
        f"Direction: {p['direction']}",
    ]
    return "\n".join(lines)
