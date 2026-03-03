"""Scoring engine — ported from Potencjal backend/app/services/scoring.py.

IMPORTANT: This must stay in sync with the frontend offScore() if the
Potencjal HTML SPA is still used.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── Default config (mirrors Potencjal JS CONFIG) ─────────────────────

DEFAULT_WEIGHTS = {
    "employees": 0.24,
    "revenue_band": 0.26,
    "years_active": 0.10,
    "vat_status": 0.08,
    "pkd_fit": 0.16,
    "basket_signal": 0.10,
    "locality": 0.06,
}

REVENUE_BANDS = [
    {"key": "micro", "min": 0, "max": 2_000_000, "score": 25},
    {"key": "small", "min": 2_000_000, "max": 10_000_000, "score": 55},
    {"key": "medium", "min": 10_000_000, "max": 50_000_000, "score": 75},
    {"key": "large", "min": 50_000_000, "max": float("inf"), "score": 92},
]

EMPLOYEES_SCALE = [
    {"max": 9, "score": 20},
    {"max": 49, "score": 55},
    {"max": 249, "score": 78},
    {"max": float("inf"), "score": 92},
]

YEARS_SCALE = [
    {"max": 1, "score": 20},
    {"max": 3, "score": 40},
    {"max": 7, "score": 60},
    {"max": 12, "score": 75},
    {"max": float("inf"), "score": 88},
]

BASKET_CALIBRATION = {"alpha": 0.65, "pivot": 8000}

LOCALITY_CITIES = ["Warszawa", "Kraków", "Wrocław", "Poznań", "Gdańsk", "Katowice", "Łódź"]

PKD_TO_CATEGORIES: dict[str, list[str]] = {
    "41": ["materiały konstrukcyjne", "stal", "chemia bud.", "narzędzia PRO"],
    "42": ["kruszywa", "beton", "geowłókniny"],
    "43": ["wykończeniówka", "chemia bud.", "elektryka", "HVAC"],
    "46.73": ["hurt budowlany", "współpraca B2B", "rabaty wolumenowe"],
    "47.52": ["detal budowlany", "POS", "szybkie dostawy"],
    "FALLBACK": ["materiały uniwersalne", "transport", "usługi cięcia/rozładunku"],
}

POTENTIAL_MODEL = {"base_arpu": 18_000, "multiplier_by_tier": {"S": 30, "A": 12, "B": 5, "C": 2}}


# ── Scoring functions ─────────────────────────────────────────────────

def revenue_band_of(revenue: float) -> str:
    for b in REVENUE_BANDS:
        if b["min"] <= revenue < b["max"]:
            return b["key"]
    return "micro"


def _scale_lookup(scale: list[dict], value: float) -> int:
    for entry in scale:
        if value <= entry["max"]:
            return entry["score"]
    return 50


def _fit_score(pkd: str, employees: int) -> int:
    base = 70 if pkd else 50
    size_adj = 12 if employees > 200 else (6 if employees > 50 else 0)
    return min(92, base + size_adj)


def categories_for_pkd(pkd: str) -> list[str]:
    if not pkd:
        return PKD_TO_CATEGORIES["FALLBACK"]
    # Try exact match, then 4-char prefix, then 2-char section
    if pkd in PKD_TO_CATEGORIES:
        return PKD_TO_CATEGORIES[pkd]
    prefix4 = pkd[:5]  # e.g. "46.73"
    if prefix4 in PKD_TO_CATEGORIES:
        return PKD_TO_CATEGORIES[prefix4]
    prefix2 = pkd[:2]  # e.g. "43"
    if prefix2 in PKD_TO_CATEGORIES:
        return PKD_TO_CATEGORIES[prefix2]
    return PKD_TO_CATEGORIES["FALLBACK"]


def estimate_annual(tier: str) -> int:
    m = POTENTIAL_MODEL
    return round(m["base_arpu"] * m["multiplier_by_tier"].get(tier, 1))


@dataclass
class ScoringInput:
    employees: int = 0
    revenue_pln: float = 0
    years_active: float = 0
    vat_status: str = "Niepewny"
    pkd: str = ""
    basket_pln: float = 0
    locality_hit: bool = False
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))


@dataclass
class FactorBreakdown:
    factor: str
    label: str
    raw_score: float
    weight: float
    weighted_score: float


@dataclass
class ScoringOutput:
    score: int
    tier: str
    annual_potential: int
    revenue_band: str
    categories: list[str]
    recommended_actions: list[str]
    breakdown: list[FactorBreakdown] | None = None


def calculate_score(inp: ScoringInput) -> ScoringOutput:
    w = inp.weights

    emp_score = _scale_lookup(EMPLOYEES_SCALE, inp.employees)
    rev_band = revenue_band_of(inp.revenue_pln)
    rev_score = next((b["score"] for b in REVENUE_BANDS if b["key"] == rev_band), 50)
    yrs_score = _scale_lookup(YEARS_SCALE, inp.years_active)

    vat_map = {"Czynny VAT": 80, "Zwolniony": 55}
    vat_score = vat_map.get(inp.vat_status, 35)

    fit = _fit_score(inp.pkd, inp.employees)

    pivot = BASKET_CALIBRATION["pivot"]
    alpha = BASKET_CALIBRATION["alpha"]
    basket_signal = min(1.0, inp.basket_pln / pivot) ** alpha if pivot > 0 else 0
    basket_score = 30 + basket_signal * 60

    loc_score = 75 if inp.locality_hit else 55

    raw = (
        emp_score * w.get("employees", 0)
        + rev_score * w.get("revenue_band", 0)
        + yrs_score * w.get("years_active", 0)
        + vat_score * w.get("vat_status", 0)
        + fit * w.get("pkd_fit", 0)
        + basket_score * w.get("basket_signal", 0)
        + loc_score * w.get("locality", 0)
    )

    score = round(raw)
    tier = "S" if score >= 85 else ("A" if score >= 70 else ("B" if score >= 55 else "C"))
    annual = estimate_annual(tier)
    categories = categories_for_pkd(inp.pkd)
    actions = _recommended_actions(tier, inp)

    breakdown = [
        FactorBreakdown("employees", "Pracownicy", emp_score, w.get("employees", 0), emp_score * w.get("employees", 0)),
        FactorBreakdown("revenue_band", "Przychód", rev_score, w.get("revenue_band", 0), rev_score * w.get("revenue_band", 0)),
        FactorBreakdown("pkd_fit", "Branża (PKD)", fit, w.get("pkd_fit", 0), fit * w.get("pkd_fit", 0)),
        FactorBreakdown("years_active", "Lata działalności", yrs_score, w.get("years_active", 0), yrs_score * w.get("years_active", 0)),
        FactorBreakdown("basket_signal", "Sygnał koszyka", round(basket_score, 1), w.get("basket_signal", 0), basket_score * w.get("basket_signal", 0)),
        FactorBreakdown("vat_status", "Status VAT", vat_score, w.get("vat_status", 0), vat_score * w.get("vat_status", 0)),
        FactorBreakdown("locality", "Lokalizacja", loc_score, w.get("locality", 0), loc_score * w.get("locality", 0)),
    ]

    return ScoringOutput(
        score=score,
        tier=tier,
        annual_potential=annual,
        revenue_band=rev_band,
        categories=categories,
        recommended_actions=actions,
        breakdown=breakdown,
    )


def _recommended_actions(tier: str, inp: ScoringInput) -> list[str]:
    steps: list[str] = []
    tier_actions = {
        "S": "Zadzwoń dziś i zaproponuj spotkanie onsite z opiekunem.",
        "A": "Wyślij ofertę z rabatem wolumenowym i transportem 24–48h.",
        "B": "Dodaj do kampanii remarketingowej. Follow-up za 7 dni.",
        "C": "Oznacz jako lead do obserwacji. Follow-up za 30 dni.",
    }
    if tier in tier_actions:
        steps.append(tier_actions[tier])
    if inp.pkd:
        cats = categories_for_pkd(inp.pkd)
        desc = cats[0] if cats and cats != PKD_TO_CATEGORIES["FALLBACK"] else ""
        steps.append(f"Dopasuj ofertę do PKD {inp.pkd}" + (f" – {desc}." if desc else "."))
    if inp.vat_status != "Czynny VAT":
        steps.append("Zweryfikuj status VAT na Białej Liście MF przed fakturą.")
    if 0 < inp.basket_pln < 3000:
        steps.append("Propozycja upsell: pakiet startowy PRO + darmowy transport powyżej 5k.")
    if inp.employees > 50:
        steps.append("Zaproponuj umowę ramową i ceny projektowe.")
    return steps
