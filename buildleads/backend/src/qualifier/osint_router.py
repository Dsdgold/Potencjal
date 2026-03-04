"""OSINT proxy endpoints — VAT, eKRS, CEIDG, GUS lookups + lead enrichment.

Ported from Potencjal /api/osint. All external lookups are proxied
through our API to avoid CORS issues on the frontend.

Full enrichment flow: OSINT registries → website scraping → geocoding → description generation.
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
from src.qualifier.web_enrichment import (
    generate_description_from_data,
    google_search_description,
    scrape_website,
)
from src.qualifier.geocoding import geocode_address
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
    """Full enrichment: OSINT registries → website scraping → geocoding → description."""
    lead = await get_lead(db, lead_id, user)
    if not lead:
        raise HTTPException(404, "Lead not found")
    if not lead.nip:
        raise HTTPException(400, "Lead has no NIP — cannot enrich")

    results, merged = await enrich_lead(lead.nip)

    # Apply ALL merged data to lead — fill empty fields, always update authoritative fields
    update_data: dict = {}
    merge_fields = [
        "name", "city", "employees", "revenue_pln", "pkd", "pkd_desc",
        "years_active", "vat_status", "website", "regon", "krs", "voivodeship",
    ]
    # Fields that should always be updated from OSINT (even if already set)
    always_update_fields = {"employees", "revenue_pln", "pkd", "pkd_desc",
                            "years_active", "voivodeship", "regon", "krs"}
    for key in merge_fields:
        current = getattr(lead, key, None)
        new_val = merged.get(key)
        if new_val is not None:
            if current is None or key in always_update_fields:
                update_data[key] = new_val

    # Extract additional data from raw OSINT
    osint_raw = {r.source: r.raw for r in results if r.raw}
    update_data["osint_raw"] = osint_raw
    update_data["sources"] = [r.source for r in results if r.raw and "error" not in (r.raw or {})]

    # Extract voivodeship from GUS or eKRS
    if not lead.voivodeship:
        for r in results:
            parsed = (r.raw or {}).get("_parsed", {}) if isinstance(r.raw, dict) else {}
            voiv = parsed.get("voivodeship")
            if voiv:
                update_data["voivodeship"] = str(voiv)
                break

    # Extract address from GUS / eKRS / VAT
    if not lead.street:
        for r in results:
            parsed = (r.raw or {}).get("_parsed", {}) if isinstance(r.raw, dict) else {}
            street = parsed.get("street")
            if street:
                building = parsed.get("building", "")
                update_data["street"] = f"{street} {building}".strip() if building else str(street)
                break
        if "street" not in update_data:
            # Try eKRS full_address
            for r in results:
                if r.source == "ekrs":
                    parsed = (r.raw or {}).get("_parsed", {}) if isinstance(r.raw, dict) else {}
                    full_addr = parsed.get("full_address", {})
                    if isinstance(full_addr, dict) and full_addr.get("ulica"):
                        parts = [full_addr.get("ulica", "")]
                        if full_addr.get("nrDomu"):
                            parts.append(full_addr["nrDomu"])
                        update_data["street"] = " ".join(parts)
                        break

    if not lead.postal_code:
        for r in results:
            parsed = (r.raw or {}).get("_parsed", {}) if isinstance(r.raw, dict) else {}
            pc = parsed.get("postal_code") or parsed.get("kodPocztowy")
            if pc:
                update_data["postal_code"] = str(pc)
                break
        if "postal_code" not in update_data:
            for r in results:
                if r.source == "ekrs":
                    parsed = (r.raw or {}).get("_parsed", {}) if isinstance(r.raw, dict) else {}
                    full_addr = parsed.get("full_address", {})
                    if isinstance(full_addr, dict) and full_addr.get("kodPocztowy"):
                        update_data["postal_code"] = str(full_addr["kodPocztowy"])
                        break

    # Extract legal_form
    if not lead.legal_form:
        for r in results:
            parsed = (r.raw or {}).get("_parsed", {}) if isinstance(r.raw, dict) else {}
            lf = parsed.get("legal_form")
            if lf:
                update_data["legal_form"] = str(lf)
                break

    # Extract board members from eKRS + set contact_person to CEO
    board_members = []
    for r in results:
        if r.source == "ekrs":
            parsed = (r.raw or {}).get("_parsed", {}) if isinstance(r.raw, dict) else {}
            board = parsed.get("board", [])
            if board:
                board_members = board
                break
    if board_members:
        update_data["board_members"] = board_members
        if not lead.contact_person:
            ceo = next(
                (m for m in board_members if "prezes" in (m.get("function", "") or "").lower()),
                board_members[0] if board_members else None,
            )
            if ceo:
                update_data["contact_person"] = ceo.get("name", "")

    # Apply partial update before web scraping
    lead = await update_lead(db, lead, **update_data)

    # ── Web scraping for description, contacts, social media ──
    website_url = lead.website
    web_result = None
    if website_url:
        try:
            web_result = await scrape_website(website_url)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Web scraping failed: %s", exc)

    web_update: dict = {}

    if web_result and not web_result.error:
        # Extract emails from website → contact_email
        if not lead.contact_email and web_result.emails:
            web_update["contact_email"] = web_result.emails[0]

        # Extract phones from website → contact_phone
        if not lead.contact_phone and web_result.phones:
            web_update["contact_phone"] = web_result.phones[0]

        # Social media links
        if web_result.social_media and not lead.social_media:
            web_update["social_media"] = web_result.social_media

    # Generate company description
    if not lead.description:
        website_desc = web_result.description if web_result and not web_result.error else None

        # Try Google search for description
        google_desc = None
        try:
            google_desc = await google_search_description(lead.name, lead.city)
        except Exception:
            pass

        combined_desc = website_desc
        if google_desc and not combined_desc:
            combined_desc = google_desc

        description = generate_description_from_data(
            name=lead.name,
            city=lead.city,
            voivodeship=lead.voivodeship,
            pkd=lead.pkd,
            pkd_desc=lead.pkd_desc,
            years_active=lead.years_active,
            legal_form=lead.legal_form,
            employees=lead.employees,
            vat_status=lead.vat_status,
            board_members=lead.board_members,
            website_desc=combined_desc,
        )
        web_update["description"] = description

    # ── Geocoding ──
    if not lead.latitude and (lead.city or lead.street):
        try:
            geo = await geocode_address(
                city=lead.city,
                street=lead.street,
                postal_code=lead.postal_code,
            )
            if geo.latitude and geo.longitude:
                web_update["latitude"] = geo.latitude
                web_update["longitude"] = geo.longitude
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Geocoding failed: %s", exc)

    if web_update:
        lead = await update_lead(db, lead, **web_update)

    all_enriched = list(update_data.keys()) + list(web_update.keys())
    return {
        "lead_id": str(lead.id),
        "enriched_fields": all_enriched,
        "sources_checked": [r.source for r in results],
        "sources_with_data": [r.source for r in results if r.name],
        "merged": merged,
        "web_scraped": bool(web_result and not web_result.error),
        "geocoded": bool(web_update.get("latitude")),
        "description_generated": bool(web_update.get("description")),
    }
