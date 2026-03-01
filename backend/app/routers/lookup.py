"""Unified NIP lookup – one call to fetch all OSINT data, create/update lead, score it."""

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Lead, ScoringHistory, User
from app.schemas import NipLookupResponse, ScoringResult
from app.services.osint import enrich_lead
from app.services.scoring import (
    DEFAULT_WEIGHTS,
    LOCALITY_CITIES,
    ScoringInput,
    calculate_score,
)

router = APIRouter(prefix="/api/lookup", tags=["lookup"])

NIP_RE = re.compile(r"^\d{10}$")


def _validate_nip(nip: str) -> str:
    nip = nip.strip().replace("-", "").replace(" ", "")
    if not NIP_RE.match(nip):
        raise HTTPException(400, "NIP musi miec dokladnie 10 cyfr")
    return nip


@router.post("/nip/{nip}", response_model=NipLookupResponse)
async def nip_lookup(
    nip: str,
    basket_pln: float = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full NIP lookup: fetch all OSINT sources, create/update lead, run scoring.

    This is the main "enter NIP and get everything" endpoint.
    If a lead with this NIP already exists for the user, it will be updated.
    """
    nip = _validate_nip(nip)

    # 1. Fetch all OSINT data
    osint_results, merged = await enrich_lead(nip)

    # 2. Find existing lead or create new one
    result = await db.execute(
        select(Lead).where(Lead.nip == nip, Lead.owner_id == user.id)
    )
    lead = result.scalar_one_or_none()

    if lead:
        # Update existing lead with new OSINT data
        for key, val in merged.model_dump(exclude_unset=True).items():
            if val is not None:
                setattr(lead, key, val)
    else:
        # Create new lead
        lead_data = merged.model_dump(exclude_unset=True)
        lead_data["nip"] = nip
        lead_data["name"] = lead_data.get("name") or f"Firma NIP {nip}"
        lead_data["basket_pln"] = basket_pln
        lead = Lead(**lead_data, owner_id=user.id)
        db.add(lead)

    # Track OSINT sources
    new_sources = [r.source for r in osint_results if not (r.raw or {}).get("error")]
    lead.sources = list(set((lead.sources or []) + new_sources))
    lead.osint_raw = {r.source: r.raw for r in osint_results}

    if basket_pln > 0:
        lead.basket_pln = basket_pln

    await db.flush()

    # 3. Run scoring
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
    scoring_out = calculate_score(inp)

    # Update lead with scoring
    lead.score = scoring_out.score
    lead.tier = scoring_out.tier
    lead.annual_potential = scoring_out.annual_potential
    lead.revenue_band = scoring_out.revenue_band

    # Record scoring history
    history = ScoringHistory(
        lead_id=lead.id,
        score=scoring_out.score,
        tier=scoring_out.tier,
        annual_potential=scoring_out.annual_potential,
        weights_snapshot=dict(DEFAULT_WEIGHTS),
    )
    db.add(history)

    await db.commit()
    await db.refresh(lead)

    scoring_result = ScoringResult(
        score=scoring_out.score,
        tier=scoring_out.tier,
        annual_potential=scoring_out.annual_potential,
        revenue_band=scoring_out.revenue_band,
        categories=scoring_out.categories,
        recommended_actions=scoring_out.recommended_actions,
    )

    return NipLookupResponse(
        lead=lead,
        osint_results=osint_results,
        scoring=scoring_result,
    )
