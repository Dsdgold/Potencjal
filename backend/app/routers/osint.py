import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Lead, User
from app.schemas import EnrichResponse, OsintResult
from app.services.osint import (
    enrich_lead,
    fetch_ceidg,
    fetch_ekrs,
    fetch_gus,
    fetch_vat_whitelist,
)

router = APIRouter(prefix="/api/osint", tags=["osint"])

NIP_RE = re.compile(r"^\d{10}$")


def _validate_nip(nip: str) -> str:
    nip = nip.strip().replace("-", "").replace(" ", "")
    if not NIP_RE.match(nip):
        raise HTTPException(400, "NIP must be exactly 10 digits")
    return nip


@router.get("/vat/{nip}", response_model=OsintResult)
async def vat_check(nip: str):
    nip = _validate_nip(nip)
    return await fetch_vat_whitelist(nip)


@router.get("/ekrs/{nip}", response_model=OsintResult)
async def ekrs_check(nip: str):
    nip = _validate_nip(nip)
    return await fetch_ekrs(nip)


@router.get("/ceidg/{nip}", response_model=OsintResult)
async def ceidg_check(nip: str):
    nip = _validate_nip(nip)
    return await fetch_ceidg(nip)


@router.get("/gus/{nip}", response_model=OsintResult)
async def gus_check(nip: str):
    nip = _validate_nip(nip)
    return await fetch_gus(nip)


@router.post("/enrich/{lead_id}", response_model=EnrichResponse)
async def enrich(lead_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Auto-enrich a lead from all OSINT sources by its NIP."""
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    if not lead.nip:
        raise HTTPException(400, "Lead has no NIP – cannot enrich without a tax ID")

    results, merged = await enrich_lead(lead.nip)

    # Apply merged data to lead (only fill in missing fields)
    for key, val in merged.model_dump(exclude_unset=True).items():
        if val is not None and getattr(lead, key, None) is None:
            setattr(lead, key, val)

    # Track sources
    new_sources = [r.source for r in results if not (r.raw or {}).get("error")]
    lead.sources = list(set((lead.sources or []) + new_sources))
    lead.osint_raw = {r.source: r.raw for r in results}

    await db.commit()
    await db.refresh(lead)

    return EnrichResponse(results=results, merged=merged)
