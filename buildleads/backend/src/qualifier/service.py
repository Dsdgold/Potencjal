"""Lead qualification — scoring + (future) AI categorization via Ollama."""

from src.leads.models import Lead, ScoringHistory
from src.qualifier.scoring import (
    DEFAULT_WEIGHTS,
    LOCALITY_CITIES,
    ScoringInput,
    calculate_score,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def score_lead(db: AsyncSession, lead: Lead) -> dict:
    """Score a lead using the Potencjal scoring engine and persist results."""
    city_hit = (lead.city or "").strip() in LOCALITY_CITIES
    inp = ScoringInput(
        employees=lead.employees or 0,
        revenue_pln=lead.revenue_pln or 0,
        years_active=lead.years_active or 0,
        vat_status=lead.vat_status or "Niepewny",
        pkd=lead.pkd or "",
        basket_pln=lead.basket_pln or 0,
        locality_hit=city_hit,
    )
    out = calculate_score(inp)

    lead.score = out.score
    lead.tier = out.tier
    lead.annual_potential = out.annual_potential
    lead.revenue_band = out.revenue_band

    history = ScoringHistory(
        lead_id=lead.id,
        score=out.score,
        tier=out.tier,
        annual_potential=out.annual_potential,
        weights_snapshot=dict(DEFAULT_WEIGHTS),
    )
    db.add(history)
    await db.commit()
    await db.refresh(lead)

    return {
        "score": out.score,
        "tier": out.tier,
        "annual_potential": out.annual_potential,
        "revenue_band": out.revenue_band,
        "categories": out.categories,
        "recommended_actions": out.recommended_actions,
    }
