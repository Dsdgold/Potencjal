"""
Deterministic rule-based scoring engine v1.
Produces a 0-100 score with full explainability.
Scoring weights are loaded from YAML config and can be overridden per-org.
"""

import yaml
import os
from datetime import datetime, date
from pathlib import Path

SCORING_RULES_PATH = Path(__file__).parent.parent.parent.parent.parent / "packages" / "shared" / "scoring_rules" / "v1.yaml"

# Default weights if YAML not found
DEFAULT_WEIGHTS = {
    "vat_status": {"max": 12, "label": "Status VAT"},
    "legal_form": {"max": 12, "label": "Forma prawna"},
    "company_age": {"max": 10, "label": "Wiek firmy"},
    "location": {"max": 8, "label": "Lokalizacja"},
    "bank_accounts": {"max": 8, "label": "Rachunki bankowe"},
    "registries": {"max": 10, "label": "Rejestry publiczne"},
    "management": {"max": 8, "label": "Zarząd / reprezentacja"},
    "share_capital": {"max": 10, "label": "Kapitał zakładowy"},
    "pkd_relevance": {"max": 7, "label": "Branża (PKD)"},
    "data_quality": {"max": 8, "label": "Kompletność danych"},
    "stability": {"max": 7, "label": "Stabilność działania"},
}

MAJOR_CITIES = [
    "warszawa", "kraków", "wrocław", "poznań", "gdańsk",
    "katowice", "łódź", "szczecin", "lublin", "bydgoszcz",
    "gdynia", "białystok", "częstochowa", "radom", "toruń",
]

# PKD codes relevant to construction materials buying
CONSTRUCTION_PKD_PREFIXES = [
    "41", "42", "43",  # Construction
    "71.1",            # Architecture and engineering
    "23.5", "23.6",    # Cement, concrete
    "46.73",           # Wholesale building materials
]

RISK_BANDS = {
    "A": {"min": 75, "label": "Niskie ryzyko", "color": "#22c55e"},
    "B": {"min": 55, "label": "Umiarkowane ryzyko", "color": "#3b82f6"},
    "C": {"min": 35, "label": "Podwyższone ryzyko", "color": "#f59e0b"},
    "D": {"min": 0,  "label": "Wysokie ryzyko", "color": "#ef4444"},
}


def load_scoring_config(org_overrides: dict | None = None) -> dict:
    """Load scoring config from YAML, with optional org-level overrides."""
    config = dict(DEFAULT_WEIGHTS)
    try:
        if SCORING_RULES_PATH.exists():
            with open(SCORING_RULES_PATH) as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config and "components" in yaml_config:
                    for key, val in yaml_config["components"].items():
                        if key in config:
                            config[key].update(val)
    except Exception:
        pass

    if org_overrides:
        for key, val in org_overrides.items():
            if key in config and isinstance(val, dict):
                config[key].update(val)

    return config


def compute_score(snapshot: dict, org_overrides: dict | None = None) -> dict:
    """
    Compute credit risk score from normalized company snapshot.
    Returns full scoring result with components, flags, and explanation.
    """
    config = load_scoring_config(org_overrides)
    components = []
    red_flags = []
    green_flags = []

    # 1. VAT Status
    vat = snapshot.get("vat_status", "")
    vat_pts = 0
    vat_max = config["vat_status"]["max"]
    vat_explanation = ""
    if vat == "Czynny":
        vat_pts = vat_max
        vat_explanation = "Firma jest czynnym podatnikiem VAT"
        green_flags.append("Czynny podatnik VAT")
    elif vat == "Zwolniony":
        vat_pts = vat_max * 0.5
        vat_explanation = "Firma zwolniona z VAT — niższe ryzyko, ale ograniczona współpraca B2B"
    else:
        vat_pts = 0
        vat_explanation = "Brak aktywnego statusu VAT — potencjalne ryzyko"
        red_flags.append("Brak czynnego statusu VAT")

    components.append({
        "name": "vat_status", "label_pl": config["vat_status"]["label"],
        "points": round(vat_pts, 1), "max_points": vat_max, "explanation": vat_explanation,
    })

    # 2. Legal Form
    form = (snapshot.get("legal_form") or "").upper()
    form_pts = 0
    form_max = config["legal_form"]["max"]
    if "AKCYJNA" in form or "S.A." in form:
        form_pts = form_max
        green_flags.append("Spółka akcyjna — wysoka wiarygodność")
    elif "Z O.O." in form or "Z OGRANICZONĄ" in form:
        form_pts = form_max * 0.85
        green_flags.append("Spółka z o.o. — standardowa forma prawna")
    elif "KOMANDYTOWA" in form:
        form_pts = form_max * 0.7
    elif "JAWNA" in form:
        form_pts = form_max * 0.6
    elif "JEDNOOSOBOWA" in form or "JDG" in form:
        form_pts = form_max * 0.4
    elif form:
        form_pts = form_max * 0.3
    else:
        form_pts = form_max * 0.1
        red_flags.append("Nieznana forma prawna")

    components.append({
        "name": "legal_form", "label_pl": config["legal_form"]["label"],
        "points": round(form_pts, 1), "max_points": form_max,
        "explanation": f"Forma prawna: {snapshot.get('legal_form', 'nieznana')}",
    })

    # 3. Company Age
    age_pts = 0
    age_max = config["company_age"]["max"]
    years = _calc_age_years(snapshot)
    if years is not None:
        if years > 15:
            age_pts = age_max
            green_flags.append(f"Firma działa od {years} lat")
        elif years > 10:
            age_pts = age_max * 0.85
        elif years > 5:
            age_pts = age_max * 0.65
        elif years > 2:
            age_pts = age_max * 0.4
        else:
            age_pts = age_max * 0.15
            red_flags.append(f"Młoda firma ({years} lat)")
    else:
        age_pts = age_max * 0.2

    components.append({
        "name": "company_age", "label_pl": config["company_age"]["label"],
        "points": round(age_pts, 1), "max_points": age_max,
        "explanation": f"Wiek firmy: {f'{years} lat' if years else 'nieznany'}",
    })

    # 4. Location
    loc_pts = 0
    loc_max = config["location"]["max"]
    city = (snapshot.get("city") or "").lower().strip()
    if any(c in city for c in MAJOR_CITIES[:5]):
        loc_pts = loc_max
    elif any(c in city for c in MAJOR_CITIES[5:]):
        loc_pts = loc_max * 0.75
    elif city:
        loc_pts = loc_max * 0.4
    else:
        loc_pts = 0

    components.append({
        "name": "location", "label_pl": config["location"]["label"],
        "points": round(loc_pts, 1), "max_points": loc_max,
        "explanation": f"Lokalizacja: {snapshot.get('city', 'nieznana')}",
    })

    # 5. Bank Accounts
    ba_pts = 0
    ba_max = config["bank_accounts"]["max"]
    ba_count = snapshot.get("bank_account_count", 0)
    if ba_count >= 10:
        ba_pts = ba_max
        green_flags.append(f"{ba_count} rachunków na Białej Liście — duża firma")
    elif ba_count >= 5:
        ba_pts = ba_max * 0.8
    elif ba_count >= 2:
        ba_pts = ba_max * 0.5
    elif ba_count >= 1:
        ba_pts = ba_max * 0.3
    else:
        ba_pts = 0
        red_flags.append("Brak rachunków na Białej Liście")

    components.append({
        "name": "bank_accounts", "label_pl": config["bank_accounts"]["label"],
        "points": round(ba_pts, 1), "max_points": ba_max,
        "explanation": f"Rachunki na Białej Liście: {ba_count}",
    })

    # 6. Registries
    reg_pts = 0
    reg_max = config["registries"]["max"]
    in_krs = snapshot.get("is_in_krs", False)
    in_ceidg = snapshot.get("is_in_ceidg", False)
    has_regon = bool(snapshot.get("regon"))
    has_vat = snapshot.get("has_vat_registration", False)
    reg_count = sum([in_krs, in_ceidg, has_regon, has_vat])
    reg_pts = min(reg_max, (reg_count / 4) * reg_max)
    if in_krs:
        green_flags.append("Wpis w KRS")
    if reg_count < 2:
        red_flags.append("Niska obecność w rejestrach publicznych")

    components.append({
        "name": "registries", "label_pl": config["registries"]["label"],
        "points": round(reg_pts, 1), "max_points": reg_max,
        "explanation": f"Obecność w {reg_count}/4 rejestrach (VAT, REGON, KRS, CEIDG)",
    })

    # 7. Management
    mgmt_pts = 0
    mgmt_max = config["management"]["max"]
    reps = snapshot.get("representatives") or []
    rep_count = len(reps)
    if rep_count >= 3:
        mgmt_pts = mgmt_max
    elif rep_count == 2:
        mgmt_pts = mgmt_max * 0.75
    elif rep_count == 1:
        mgmt_pts = mgmt_max * 0.45
    else:
        mgmt_pts = 0
        red_flags.append("Brak danych o zarządzie")

    components.append({
        "name": "management", "label_pl": config["management"]["label"],
        "points": round(mgmt_pts, 1), "max_points": mgmt_max,
        "explanation": f"Osób w zarządzie: {rep_count}",
    })

    # 8. Share Capital
    cap_pts = 0
    cap_max = config["share_capital"]["max"]
    capital = snapshot.get("share_capital", 0) or 0
    if capital >= 1_000_000:
        cap_pts = cap_max
        green_flags.append(f"Kapitał zakładowy: {capital:,.0f} PLN")
    elif capital >= 100_000:
        cap_pts = cap_max * 0.7
    elif capital >= 50_000:
        cap_pts = cap_max * 0.5
    elif capital >= 5_000:
        cap_pts = cap_max * 0.25
    elif capital > 0:
        cap_pts = cap_max * 0.1
        red_flags.append(f"Minimalny kapitał zakładowy: {capital:,.0f} PLN")
    else:
        cap_pts = 0

    components.append({
        "name": "share_capital", "label_pl": config["share_capital"]["label"],
        "points": round(cap_pts, 1), "max_points": cap_max,
        "explanation": f"Kapitał: {capital:,.0f} PLN" if capital else "Brak danych o kapitale",
    })

    # 9. PKD Relevance (to construction materials)
    pkd_pts = 0
    pkd_max = config["pkd_relevance"]["max"]
    pkd_main = snapshot.get("pkd_main_code", "") or ""
    pkd_all = [p.get("code", "") for p in (snapshot.get("pkd_codes") or [])]
    is_construction = any(
        any(pkd.startswith(prefix) for prefix in CONSTRUCTION_PKD_PREFIXES)
        for pkd in ([pkd_main] + pkd_all)
    )
    if is_construction:
        pkd_pts = pkd_max
        green_flags.append("Branża budowlana — wysoki potencjał zakupowy")
    elif pkd_main:
        pkd_pts = pkd_max * 0.3  # Some baseline for known industry
    else:
        pkd_pts = pkd_max * 0.15

    components.append({
        "name": "pkd_relevance", "label_pl": config["pkd_relevance"]["label"],
        "points": round(pkd_pts, 1), "max_points": pkd_max,
        "explanation": f"PKD: {pkd_main} {'(budownictwo)' if is_construction else ''}".strip(),
    })

    # 10. Data Quality / Completeness
    dq_pts = 0
    dq_max = config["data_quality"]["max"]
    key_fields = [
        "name", "nip", "regon", "legal_form", "vat_status",
        "registered_address", "city", "registration_date",
        "pkd_main_code", "representatives", "bank_account_count",
        "share_capital",
    ]
    filled = sum(1 for f in key_fields if snapshot.get(f))
    completeness = filled / len(key_fields)
    dq_pts = dq_max * completeness

    components.append({
        "name": "data_quality", "label_pl": config["data_quality"]["label"],
        "points": round(dq_pts, 1), "max_points": dq_max,
        "explanation": f"Kompletność danych: {completeness:.0%} ({filled}/{len(key_fields)} pól)",
    })

    # 11. Stability
    stab_pts = 0
    stab_max = config["stability"]["max"]
    is_active = snapshot.get("is_active")
    if is_active is True:
        stab_pts = stab_max * 0.7
        if years and years > 5:
            stab_pts = stab_max
    elif is_active is False:
        stab_pts = 0
        red_flags.append("Firma nieaktywna")
    else:
        stab_pts = stab_max * 0.3

    components.append({
        "name": "stability", "label_pl": config["stability"]["label"],
        "points": round(stab_pts, 1), "max_points": stab_max,
        "explanation": "Aktywna" if is_active else "Status nieznany/nieaktywna",
    })

    # Total
    total = round(sum(c["points"] for c in components))
    total = max(0, min(100, total))

    # Risk band
    band = "D"
    band_label = RISK_BANDS["D"]["label"]
    for b in ["A", "B", "C", "D"]:
        if total >= RISK_BANDS[b]["min"]:
            band = b
            band_label = RISK_BANDS[b]["label"]
            break

    # Summary
    summary_parts = []
    if total >= 75:
        summary_parts.append(f"Firma o niskim ryzyku ({total}/100).")
    elif total >= 55:
        summary_parts.append(f"Firma o umiarkowanym ryzyku ({total}/100).")
    elif total >= 35:
        summary_parts.append(f"Firma o podwyższonym ryzyku ({total}/100).")
    else:
        summary_parts.append(f"Firma o wysokim ryzyku ({total}/100).")

    if red_flags:
        summary_parts.append(f"Uwaga: {'; '.join(red_flags[:3])}.")
    if green_flags:
        summary_parts.append(f"Atuty: {'; '.join(green_flags[:3])}.")

    return {
        "score_0_100": total,
        "risk_band": band,
        "risk_band_label": band_label,
        "components": components,
        "red_flags": red_flags,
        "green_flags": green_flags,
        "explanation_summary": " ".join(summary_parts),
    }


def _calc_age_years(snapshot: dict) -> int | None:
    for field in ["registration_date", "start_date", "krs_registration_date"]:
        val = snapshot.get(field)
        if val:
            try:
                reg = datetime.strptime(val[:10], "%Y-%m-%d").date()
                return (date.today() - reg).days // 365
            except (ValueError, TypeError):
                continue
    return None
