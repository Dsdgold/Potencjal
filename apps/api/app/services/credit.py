"""
Credit limit suggestion engine.
Calculates recommended credit limit based on score, company data, and risk flags.
"""


# Base limits per risk band (in PLN)
BAND_LIMITS = {
    "A": {"base": 500_000, "min": 200_000, "max": 1_000_000, "terms_days": 60, "discount_pct": 15.0},
    "B": {"base": 200_000, "min": 50_000,  "max": 400_000,  "terms_days": 45, "discount_pct": 10.0},
    "C": {"base": 50_000,  "min": 10_000,  "max": 100_000,  "terms_days": 30, "discount_pct": 5.0},
    "D": {"base": 0,       "min": 0,       "max": 15_000,   "terms_days": 0,  "discount_pct": 0.0},
}


def compute_credit_limit(score: int, band: str, snapshot: dict, score_components: list) -> dict:
    """
    Compute suggested credit limit with min/max range and payment terms.
    """
    limits = BAND_LIMITS.get(band, BAND_LIMITS["D"]).copy()
    base = limits["base"]
    explanation_parts = [f"Bazowy limit dla pasma {band}: {base:,} PLN"]

    # Adjust by company age
    age = _get_age(snapshot)
    age_mult = 1.0
    if age is not None:
        if age > 15:
            age_mult = 1.25
            explanation_parts.append(f"+25% za staż firmy ({age} lat)")
        elif age > 10:
            age_mult = 1.15
            explanation_parts.append(f"+15% za staż firmy ({age} lat)")
        elif age > 5:
            age_mult = 1.05
        elif age < 2:
            age_mult = 0.6
            explanation_parts.append(f"-40% za krótki staż ({age} lat)")

    # Adjust by share capital
    capital = snapshot.get("share_capital", 0) or 0
    capital_mult = 1.0
    if capital >= 5_000_000:
        capital_mult = 1.3
        explanation_parts.append(f"+30% za wysoki kapitał ({capital:,.0f} PLN)")
    elif capital >= 1_000_000:
        capital_mult = 1.15
        explanation_parts.append(f"+15% za kapitał ({capital:,.0f} PLN)")
    elif capital >= 100_000:
        capital_mult = 1.05

    # Adjust by revenue estimate
    revenue = snapshot.get("annual_revenue_estimate", 0) or 0
    revenue_mult = 1.0
    if revenue > 100_000_000:
        revenue_mult = 1.2
        explanation_parts.append("+20% za szacowane przychody >100M PLN")
    elif revenue > 10_000_000:
        revenue_mult = 1.1

    # Adjust by bank accounts (proxy for size)
    accounts = snapshot.get("bank_account_count", 0) or 0
    if accounts > 20:
        explanation_parts.append("+10% za liczbę rachunków bankowych")
        accounts_mult = 1.1
    else:
        accounts_mult = 1.0

    # Check for red flags
    red_flag_mult = 1.0
    red_components = [c for c in score_components if c["points"] == 0 and c["max_points"] > 0]
    if len(red_components) >= 3:
        red_flag_mult = 0.7
        explanation_parts.append("-30% za liczne czynniki ryzyka")

    # Inactive company gets zero
    if snapshot.get("is_active") is False:
        return {
            "credit_limit_suggested": 0,
            "credit_limit_min": 0,
            "credit_limit_max": 0,
            "payment_terms_days": 0,
            "discount_pct": 0.0,
            "explanation": "Limit: 0 PLN — firma nieaktywna. Wymagana przedpłata.",
        }

    # Calculate
    adjusted = base * age_mult * capital_mult * revenue_mult * accounts_mult * red_flag_mult
    suggested = int(round(adjusted / 1000) * 1000)  # Round to nearest 1000
    limit_min = max(limits["min"], int(suggested * 0.5))
    limit_max = min(limits["max"], int(suggested * 1.5))
    suggested = max(limit_min, min(limit_max, suggested))

    # Prepayment for band D
    if band == "D":
        return {
            "credit_limit_suggested": 0,
            "credit_limit_min": 0,
            "credit_limit_max": limits["max"],
            "payment_terms_days": 0,
            "discount_pct": 0.0,
            "explanation": "Pasmo D — rekomendacja: przedpłata. "
                          f"Maksymalny limit po weryfikacji: {limits['max']:,} PLN. "
                          + " ".join(explanation_parts),
        }

    return {
        "credit_limit_suggested": suggested,
        "credit_limit_min": limit_min,
        "credit_limit_max": limit_max,
        "payment_terms_days": limits["terms_days"],
        "discount_pct": limits["discount_pct"],
        "explanation": f"Sugerowany limit: {suggested:,} PLN (zakres {limit_min:,}–{limit_max:,}). "
                      f"Termin płatności: {limits['terms_days']} dni. "
                      f"Rabat handlowy: {limits['discount_pct']}%. "
                      + " ".join(explanation_parts),
    }


def _get_age(snapshot: dict) -> int | None:
    from datetime import datetime, date as d
    for field in ["registration_date", "start_date"]:
        val = snapshot.get(field)
        if val:
            try:
                reg = datetime.strptime(val[:10], "%Y-%m-%d").date()
                return (d.today() - reg).days // 365
            except (ValueError, TypeError):
                continue
    return None
