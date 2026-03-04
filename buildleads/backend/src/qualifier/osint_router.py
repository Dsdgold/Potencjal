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
    search_panoramafirm,
    search_aleo,
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

    # Extract address from GUS / eKRS / VAT (always refresh)
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

    # Extract legal_form (always refresh from OSINT)
    for r in results:
        parsed = (r.raw or {}).get("_parsed", {}) if isinstance(r.raw, dict) else {}
        lf = parsed.get("legal_form")
        if lf:
            update_data["legal_form"] = str(lf)
            break

    # ── Board members: merge eKRS (has functions) with VAT (has full names) ──
    # eKRS returns board with functions (Prezes, Członek) but RODO-masks names: "J**** K****"
    # VAT White List returns full names but only as flat "Reprezentant" / "Wspólnik"
    # Strategy: use eKRS functions + VAT names, matched by count/position

    ekrs_board = []
    ekrs_organ_name = "Zarząd"
    for r in results:
        if r.source == "ekrs":
            parsed = (r.raw or {}).get("_parsed", {}) if isinstance(r.raw, dict) else {}
            ekrs_board = parsed.get("board", [])
            ekrs_organ_name = parsed.get("board_organ_name", "Zarząd")
            break

    vat_representatives = []
    vat_partners = []
    for r in results:
        if r.source == "vat_whitelist" and r.raw:
            subject = (r.raw.get("result") or {}).get("subject") or {}
            for rep in (subject.get("representatives") or []):
                first = rep.get("firstName", "") or ""
                last = rep.get("lastName", "") or ""
                company = rep.get("companyName", "") or ""
                full = f"{first} {last}".strip() or company
                if full and "*" not in full:
                    vat_representatives.append(full)
            for p in (subject.get("partners") or []):
                first = p.get("firstName", "") or ""
                last = p.get("lastName", "") or ""
                company = p.get("companyName", "") or ""
                full = f"{first} {last}".strip() or company
                if full and "*" not in full:
                    vat_partners.append(full)
            break

    # Build final board: replace masked eKRS names with VAT names
    board_members = []
    any_masked = any("*" in (m.get("name", "") or "") for m in ekrs_board)

    if ekrs_board and not any_masked:
        # eKRS names are clean — use them directly (they have functions)
        board_members = ekrs_board
    elif ekrs_board and vat_representatives:
        # eKRS has functions but masked names — match with VAT names by position
        vat_idx = 0
        for member in ekrs_board:
            name = member.get("name", "")
            func = member.get("function", "")
            if "*" in name and vat_idx < len(vat_representatives):
                board_members.append({"name": vat_representatives[vat_idx], "function": func})
                vat_idx += 1
            elif "*" not in name:
                board_members.append({"name": name, "function": func})
            else:
                # No more VAT names to match — keep masked entry as-is
                board_members.append({"name": name, "function": func})
        # Add remaining VAT reps not matched to eKRS
        for i in range(vat_idx, len(vat_representatives)):
            board_members.append({"name": vat_representatives[i], "function": "Reprezentant"})
    elif vat_representatives:
        # No eKRS board — use VAT representatives
        board_members = [{"name": n, "function": "Reprezentant"} for n in vat_representatives]

    # Add VAT partners (wspólnicy) — always useful
    for p in vat_partners:
        if not any(m.get("name") == p for m in board_members):
            board_members.append({"name": p, "function": "Wspólnik"})

    # Save board members to DB (including masked — frontend shows them with RODO tag)
    if board_members:
        update_data["board_members"] = board_members
        # Set contact_person from clean (non-masked) board member
        clean_members = [m for m in board_members if "*" not in (m.get("name", "") or "")]
        if clean_members:
            ceo = next(
                (m for m in clean_members if "prezes" in (m.get("function", "") or "").lower()),
                clean_members[0],
            )
            if ceo:
                update_data["contact_person"] = ceo.get("name", "")

    # Apply partial update before web scraping
    lead = await update_lead(db, lead, **update_data)

    # ── Web scraping + external sources for contacts, description ──
    import asyncio as _aio

    website_url = lead.website
    web_result = None
    pano_result = None
    aleo_result = None

    # Run website scraping, panoramafirm and aleo in parallel
    async def _scrape_web():
        if website_url:
            return await scrape_website(website_url)
        return None

    async def _scrape_pano():
        return await search_panoramafirm(lead.nip, lead.name)

    async def _scrape_aleo():
        return await search_aleo(lead.nip)

    try:
        web_result, pano_result, aleo_result = await _aio.gather(
            _scrape_web(), _scrape_pano(), _scrape_aleo(),
            return_exceptions=True,
        )
        if isinstance(web_result, Exception):
            import logging
            logging.getLogger(__name__).warning("Web scraping failed: %s", web_result)
            web_result = None
        if isinstance(pano_result, Exception):
            pano_result = None
        if isinstance(aleo_result, Exception):
            aleo_result = None
    except Exception:
        pass

    web_update: dict = {}

    if web_result and not web_result.error:
        if web_result.emails:
            web_update["contact_email"] = web_result.emails[0]
        if web_result.phones:
            web_update["contact_phone"] = web_result.phones[0]
        if web_result.social_media:
            web_update["social_media"] = web_result.social_media

    # Fill gaps from panoramafirm / aleo — but validate emails belong to this company
    if not web_update.get("contact_phone"):
        for src in [pano_result, aleo_result]:
            if src and isinstance(src, dict) and src.get("phones"):
                web_update["contact_phone"] = src["phones"][0]
                break

    # Only use scraped email if it likely belongs to this company
    def _email_matches_company(email: str, company_name: str, website: str | None) -> bool:
        email_domain = email.split("@")[-1].lower()
        # If company has a website, email domain should match
        if website:
            site = website.lower().replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
            if email_domain == site or site.endswith(email_domain) or email_domain.endswith(site.split(".")[0]):
                return True
        # Check if company name words appear in email domain
        name_words = [w.lower() for w in company_name.split() if len(w) > 3]
        for w in name_words:
            if w in email_domain or w in email.split("@")[0].lower():
                return True
        # Generic business domains are OK only from company website
        return False

    if not web_update.get("contact_email"):
        for src in [pano_result, aleo_result]:
            if src and isinstance(src, dict) and src.get("emails"):
                candidate = src["emails"][0]
                if _email_matches_company(candidate, lead.name, lead.website):
                    web_update["contact_email"] = candidate
                    break

    # Employees from aleo (if we only have estimates)
    if aleo_result and isinstance(aleo_result, dict) and aleo_result.get("employees"):
        if not lead.employees or lead.employees < aleo_result["employees"]:
            web_update["employees"] = aleo_result["employees"]

    # Always (re-)generate company description on enrichment
    website_desc = web_result.description if web_result and not getattr(web_result, 'error', None) else None

    # Collect all description sources
    extra_descs = []
    if pano_result and isinstance(pano_result, dict) and pano_result.get("description"):
        extra_descs.append(pano_result["description"])
    if aleo_result and isinstance(aleo_result, dict) and aleo_result.get("description"):
        extra_descs.append(aleo_result["description"])

    # Try Google search for description
    google_desc = None
    try:
        google_desc = await google_search_description(lead.name, lead.city)
    except Exception:
        pass

    # Combine all description sources
    desc_parts = [d for d in [website_desc, google_desc] + extra_descs if d]
    combined_desc = "\n\n".join(desc_parts) if desc_parts else None

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

    # ── Geocoding (always refresh on enrichment) ──
    if lead.city or lead.street:
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
