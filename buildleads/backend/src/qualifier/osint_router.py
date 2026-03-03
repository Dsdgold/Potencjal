"""OSINT proxy endpoints — VAT, eKRS, CEIDG, GUS lookups + lead enrichment.

Ported from Potencjal /api/osint. All external lookups are proxied
through our API to avoid CORS issues on the frontend.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.permissions import get_current_user, get_optional_user
from src.database import get_db
from src.leads.service import get_lead, update_lead
from src.qualifier.osint import (
    enrich_lead,
    fetch_ceidg,
    fetch_ekrs,
    fetch_gus,
    fetch_vat_whitelist,
)
from src.users.models import User

router = APIRouter(prefix="/api/v1/osint", tags=["osint"])


@router.get("/vat/{nip}")
async def vat_lookup(nip: str):
    """VAT White List check — free, no auth required."""
    try:
        result = await fetch_vat_whitelist(nip)
        return {
            "source": result.source,
            "nip": result.nip,
            "name": result.name,
            "city": result.city,
            "vat_status": result.vat_status,
            "regon": result.regon,
            "krs": result.krs,
            "raw": result.raw,
        }
    except Exception as exc:
        raise HTTPException(502, f"VAT API error: {exc}")


@router.get("/ekrs/{nip}")
async def ekrs_lookup(nip: str, krs: str | None = None):
    """eKRS registry lookup — free, no auth required. Pass ?krs=XXXXXXXXXX for reliable lookup."""
    try:
        result = await fetch_ekrs(nip, krs_number=krs)
        return {
            "source": result.source,
            "nip": result.nip,
            "name": result.name,
            "city": result.city,
            "pkd": result.pkd,
            "pkd_desc": result.pkd_desc,
            "years_active": result.years_active,
            "krs": result.krs,
            "regon": result.regon,
            "raw": result.raw,
        }
    except Exception as exc:
        raise HTTPException(502, f"eKRS API error: {exc}")


@router.get("/ceidg/{nip}")
async def ceidg_lookup(nip: str):
    """CEIDG lookup — requires CEIDG_API_KEY."""
    try:
        result = await fetch_ceidg(nip)
        return {
            "source": result.source,
            "nip": result.nip,
            "name": result.name,
            "city": result.city,
            "pkd": result.pkd,
            "years_active": result.years_active,
            "website": result.website,
            "raw": result.raw,
        }
    except Exception as exc:
        raise HTTPException(502, f"CEIDG API error: {exc}")


@router.get("/gus/{nip}")
async def gus_lookup(nip: str):
    """GUS REGON lookup — requires GUS_API_KEY."""
    try:
        result = await fetch_gus(nip)
        return {
            "source": result.source,
            "nip": result.nip,
            "name": result.name,
            "city": result.city,
            "pkd": result.pkd,
            "regon": result.regon,
            "raw": result.raw,
        }
    except Exception as exc:
        raise HTTPException(502, f"GUS API error: {exc}")


@router.post("/enrich/{lead_id}")
async def enrich(
    lead_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Auto-enrich a lead from all available OSINT sources."""
    lead = await get_lead(db, lead_id, user)
    if not lead:
        raise HTTPException(404, "Lead not found")
    if not lead.nip:
        raise HTTPException(400, "Lead has no NIP — cannot enrich")

    results, merged = await enrich_lead(lead.nip)

    # Apply merged data to lead — fill empty fields, and update key fields
    # that might have been missing on initial quick-lookup creation
    update_data = {}
    merge_fields = ["name", "city", "employees", "revenue_pln", "pkd", "pkd_desc",
                    "years_active", "vat_status", "website", "voivodeship"]
    # Fields that should always be updated from OSINT (even if already set to
    # a default value) because the enrichment is more authoritative
    always_update_fields = {"employees", "revenue_pln", "pkd", "pkd_desc",
                            "years_active", "voivodeship"}
    for key in merge_fields:
        current = getattr(lead, key, None)
        new_val = merged.get(key)
        if new_val is not None:
            if current is None or key in always_update_fields:
                update_data[key] = new_val

    # Store raw OSINT data
    osint_raw = {r.source: r.raw for r in results if r.raw}
    update_data["osint_raw"] = osint_raw
    update_data["sources"] = [r.source for r in results if r.raw and "error" not in (r.raw or {})]

    lead = await update_lead(db, lead, **update_data)

    return {
        "lead_id": str(lead.id),
        "enriched_fields": list(update_data.keys()),
        "sources_checked": [r.source for r in results],
        "sources_with_data": [r.source for r in results if r.name],
        "merged": merged,
    }
