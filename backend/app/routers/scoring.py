import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Lead, ScoringHistory, User
from app.schemas import ScoringHistoryOut, ScoringRequest, ScoringResult
from app.services.scoring import (
    DEFAULT_WEIGHTS,
    LOCALITY_CITIES,
    ScoringInput,
    calculate_score,
    revenue_band_of,
)

router = APIRouter(prefix="/api/scoring", tags=["scoring"])


@router.post("/calculate", response_model=ScoringResult)
async def calculate(body: ScoringRequest):
    """Stateless scoring – calculate score without persisting anything."""
    inp = ScoringInput(
        employees=body.employees,
        revenue_pln=body.revenue_pln,
        years_active=body.years_active,
        vat_status=body.vat_status,
        pkd=body.pkd,
        basket_pln=body.basket_pln,
        locality_hit=body.locality_hit,
    )
    out = calculate_score(inp)
    return ScoringResult(
        score=out.score,
        tier=out.tier,
        annual_potential=out.annual_potential,
        revenue_band=out.revenue_band,
        categories=out.categories,
        recommended_actions=out.recommended_actions,
    )


@router.post("/leads/{lead_id}", response_model=ScoringResult)
async def score_lead(lead_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Score an existing lead – persists result on the lead and in scoring history."""
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")

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

    # Update lead
    lead.score = out.score
    lead.tier = out.tier
    lead.annual_potential = out.annual_potential
    lead.revenue_band = out.revenue_band

    # Record history
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

    return ScoringResult(
        score=out.score,
        tier=out.tier,
        annual_potential=out.annual_potential,
        revenue_band=out.revenue_band,
        categories=out.categories,
        recommended_actions=out.recommended_actions,
    )


@router.get("/leads/{lead_id}/history", response_model=list[ScoringHistoryOut])
async def scoring_history(lead_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    stmt = (
        select(ScoringHistory)
        .where(ScoringHistory.lead_id == lead_id)
        .order_by(ScoringHistory.scored_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
