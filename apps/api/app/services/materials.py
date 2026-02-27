"""
Construction material recommendation engine.
Maps PKD codes, keywords, and company profile to material categories.
"""

import yaml
from pathlib import Path

TAXONOMY_PATH = Path(__file__).parent.parent.parent.parent.parent / "packages" / "shared" / "material_taxonomy"

# Construction material categories
CATEGORIES = {
    "cement": {"name_pl": "Cement i spoiwa", "keywords": ["cement", "beton", "spoiwo", "zaprawa"]},
    "insulation": {"name_pl": "Izolacje termiczne", "keywords": ["izolacja", "styropian", "wełna", "termoizolacja", "ocieplenie"]},
    "drywall": {"name_pl": "Systemy suchej zabudowy", "keywords": ["gips", "karton-gips", "sucha zabudowa", "regips", "knauf"]},
    "rebar": {"name_pl": "Stal zbrojeniowa", "keywords": ["stal", "zbrojenie", "pręty", "siatka"]},
    "aggregates": {"name_pl": "Kruszywa i piasek", "keywords": ["kruszywo", "piasek", "żwir", "kamień"]},
    "roofing": {"name_pl": "Pokrycia dachowe", "keywords": ["dach", "dachówka", "blachodachówka", "papa", "pokrycie dachowe"]},
    "facade": {"name_pl": "Systemy elewacyjne", "keywords": ["elewacja", "tynk", "fasada", "okładzina"]},
    "windows_doors": {"name_pl": "Okna i drzwi", "keywords": ["okno", "drzwi", "stolarka", "PCV", "aluminium"]},
    "waterproofing": {"name_pl": "Hydroizolacja", "keywords": ["hydroizolacja", "folia", "membrana", "uszczelnienie"]},
    "adhesives": {"name_pl": "Kleje i chemia budowlana", "keywords": ["klej", "chemia", "silikon", "pianka", "preparat"]},
    "paints": {"name_pl": "Farby i lakiery", "keywords": ["farba", "lakier", "emulsja", "grunt", "malowanie"]},
    "pipes": {"name_pl": "Instalacje wod-kan", "keywords": ["rura", "instalacja", "wod-kan", "kanalizacja", "woda"]},
    "electrical": {"name_pl": "Instalacje elektryczne", "keywords": ["kabel", "elektryka", "przewód", "instalacja elektryczna"]},
    "hvac": {"name_pl": "Ogrzewanie i wentylacja", "keywords": ["ogrzewanie", "wentylacja", "klimatyzacja", "pompa ciepła", "grzejnik"]},
    "tools": {"name_pl": "Narzędzia budowlane", "keywords": ["narzędzie", "elektronarzędzie", "wiertarka", "szlifierka"]},
}

# PKD code to category mapping
PKD_CATEGORY_MAP = {
    "41.10": ["cement", "rebar", "aggregates", "insulation", "drywall", "roofing", "windows_doors"],
    "41.20": ["cement", "rebar", "aggregates", "insulation", "drywall", "roofing", "facade", "windows_doors", "paints"],
    "42.11": ["aggregates", "rebar", "cement", "pipes"],
    "42.12": ["rebar", "aggregates", "cement", "pipes"],
    "42.13": ["pipes", "rebar", "aggregates"],
    "42.21": ["pipes", "waterproofing", "aggregates"],
    "42.22": ["electrical", "pipes", "rebar"],
    "42.91": ["waterproofing", "rebar", "aggregates"],
    "42.99": ["cement", "rebar", "aggregates"],
    "43.11": ["aggregates", "cement"],
    "43.12": ["aggregates", "pipes"],
    "43.21": ["electrical", "tools"],
    "43.22": ["pipes", "hvac", "tools"],
    "43.29": ["pipes", "hvac", "insulation"],
    "43.31": ["facade", "paints", "adhesives", "insulation"],
    "43.32": ["windows_doors", "adhesives"],
    "43.33": ["facade", "paints", "adhesives"],
    "43.34": ["paints", "adhesives", "facade"],
    "43.39": ["adhesives", "paints", "tools"],
    "43.91": ["roofing", "insulation", "waterproofing"],
    "43.99": ["cement", "adhesives", "tools", "paints"],
    "23.51": ["cement"],
    "23.52": ["cement", "aggregates"],
    "23.61": ["cement", "rebar", "aggregates"],
    "23.63": ["cement", "aggregates"],
    "23.69": ["cement", "aggregates"],
    "46.73": ["cement", "insulation", "drywall", "roofing", "facade", "adhesives", "paints", "pipes", "tools"],
    "46.74": ["pipes", "rebar", "tools"],
    "47.52": ["tools", "paints", "adhesives"],
    "71.11": ["insulation", "facade", "windows_doors"],
    "71.12": ["cement", "rebar", "aggregates", "insulation"],
}


def recommend_materials(snapshot: dict) -> dict:
    """
    Predict which construction material categories the company might buy.
    Returns categorized recommendations with confidence and explanation.
    """
    scores: dict[str, float] = {cat: 0.0 for cat in CATEGORIES}
    reasons: dict[str, list[str]] = {cat: [] for cat in CATEGORIES}

    # 1. PKD-based matching (highest weight)
    pkd_main = snapshot.get("pkd_main_code", "") or ""
    pkd_all_raw = snapshot.get("pkd_codes") or []
    pkd_codes = [p.get("code", "") if isinstance(p, dict) else str(p) for p in pkd_all_raw]
    if pkd_main and pkd_main not in pkd_codes:
        pkd_codes.insert(0, pkd_main)

    for pkd in pkd_codes:
        # Try exact match, then prefix match
        matched_cats = PKD_CATEGORY_MAP.get(pkd, [])
        if not matched_cats:
            prefix = pkd[:5] if len(pkd) >= 5 else pkd
            matched_cats = PKD_CATEGORY_MAP.get(prefix, [])
        if not matched_cats:
            prefix = pkd[:2]
            for key, cats in PKD_CATEGORY_MAP.items():
                if key.startswith(prefix):
                    matched_cats = cats
                    break

        is_main = (pkd == pkd_main)
        for cat in matched_cats:
            boost = 0.5 if is_main else 0.3
            scores[cat] = min(1.0, scores[cat] + boost)
            pkd_name = _find_pkd_name(pkd, pkd_all_raw)
            reasons[cat].append(f"PKD {pkd}" + (f" ({pkd_name})" if pkd_name else ""))

    # 2. Keyword matching from company name, PKD names, tenders
    text_sources = [
        snapshot.get("name", ""),
        snapshot.get("pkd_main_name", ""),
    ]
    for p in pkd_all_raw:
        if isinstance(p, dict) and p.get("name"):
            text_sources.append(p["name"])
    for t in (snapshot.get("recent_tenders") or []):
        if isinstance(t, dict) and t.get("title"):
            text_sources.append(t["title"])

    combined_text = " ".join(text_sources).lower()

    for cat, info in CATEGORIES.items():
        for kw in info["keywords"]:
            if kw.lower() in combined_text:
                scores[cat] = min(1.0, scores[cat] + 0.2)
                reasons[cat].append(f"Słowo kluczowe: '{kw}'")

    # 3. Construction company general boost
    is_construction = any(
        pkd.startswith(p) for pkd in pkd_codes for p in ["41", "42", "43"]
    )
    if is_construction:
        for cat in CATEGORIES:
            if scores[cat] == 0:
                scores[cat] = 0.1  # Minimal baseline for construction companies
                reasons[cat].append("Firma budowlana — potencjalny odbiorca")

    # Build result
    results = []
    for cat, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        if score > 0:
            results.append({
                "code": cat,
                "name_pl": CATEGORIES[cat]["name_pl"],
                "confidence": round(score, 2),
                "reason": "; ".join(dict.fromkeys(reasons[cat]))[:200],  # Deduplicate
            })

    # Explanation summary
    if results:
        top3 = [r["name_pl"] for r in results[:3]]
        explanation = f"Najwyższy potencjał zakupowy: {', '.join(top3)}."
        if is_construction:
            explanation += " Firma z branży budowlanej — szeroki zakres potrzeb materiałowych."
    else:
        explanation = "Brak danych do określenia kategorii materiałów. Firma spoza branży budowlanej."

    return {
        "categories": results,
        "explanation": explanation,
    }


def _find_pkd_name(code: str, pkd_list: list) -> str | None:
    for p in pkd_list:
        if isinstance(p, dict) and p.get("code") == code:
            return p.get("name")
    return None
