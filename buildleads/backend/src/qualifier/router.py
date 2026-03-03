"""Scoring endpoints — stateless calc + persist, scoring history.

Ported from Potencjal /api/scoring.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.permissions import get_current_user
from src.database import get_db
from src.leads.models import Lead, ScoringHistory
from src.leads.schemas import ScoringHistoryOut
from src.leads.service import get_lead
from src.qualifier.scoring import (
    LOCALITY_CITIES,
    ScoringInput,
    calculate_score,
)
from src.qualifier.service import score_lead
from src.users.models import User

router = APIRouter(prefix="/api/v1/scoring", tags=["scoring"])


class ScoringRequest(BaseModel):
    employees: int = Field(0, ge=0)
    revenue_pln: float = Field(0, ge=0)
    years_active: float = Field(0, ge=0)
    vat_status: str = "Niepewny"
    pkd: str = ""
    basket_pln: float = Field(0, ge=0)
    locality_hit: bool = False


@router.post("/calculate")
async def stateless_score(body: ScoringRequest):
    """Calculate score without persisting — no auth required."""
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
    return {
        "score": out.score,
        "tier": out.tier,
        "annual_potential": out.annual_potential,
        "revenue_band": out.revenue_band,
        "categories": out.categories,
        "recommended_actions": out.recommended_actions,
        "breakdown": [
            {
                "factor": b.factor,
                "label": b.label,
                "raw_score": round(b.raw_score, 1),
                "weight": b.weight,
                "weighted_score": round(b.weighted_score, 1),
            }
            for b in (out.breakdown or [])
        ],
    }


@router.post("/leads/{lead_id}")
async def score_and_persist(
    lead_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lead = await get_lead(db, lead_id, user)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return await score_lead(db, lead)


@router.get("/leads/{lead_id}/history", response_model=list[ScoringHistoryOut])
async def scoring_history(
    lead_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lead = await get_lead(db, lead_id, user)
    if not lead:
        raise HTTPException(404, "Lead not found")
    result = await db.execute(
        select(ScoringHistory)
        .where(ScoringHistory.lead_id == lead_id)
        .order_by(ScoringHistory.scored_at.desc())
    )
    return list(result.scalars().all())
