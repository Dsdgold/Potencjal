"""
Company lookup orchestrator.
Fetches data from multiple providers in parallel, merges, computes scoring.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.config import get_settings
from app.models.company import Company, CompanySnapshot
from app.models.scoring import ScoreResult, MaterialRecommendation
from app.services.providers import (
    VATWhitelistProvider, KRSProvider, GUSProvider,
    CEIDGProvider, MockProvider, ProviderResult,
)
from app.services.scoring import compute_score
from app.services.credit import compute_credit_limit
from app.services.materials import recommend_materials

logger = structlog.get_logger()


async def lookup_company(
    nip: str,
    db: AsyncSession,
    org_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    force_refresh: bool = False,
    use_mock: bool = False,
    org_credentials: dict | None = None,
    scoring_overrides: dict | None = None,
) -> dict:
    """
    Full company lookup pipeline:
    1. Check cache (fresh snapshot)
    2. Fetch from providers in parallel
    3. Merge normalized data
    4. Compute scoring + credit limit + material recommendations
    5. Persist snapshot + results
    6. Return complete profile
    """
    settings = get_settings()

    # 1. Check for existing company + fresh snapshot
    company = await _get_or_create_company(db, nip)

    if not force_refresh:
        fresh_snapshot = await _get_fresh_snapshot(db, company.id, settings.SNAPSHOT_TTL_SECONDS)
        if fresh_snapshot:
            logger.info("cache_hit", nip=nip, snapshot_id=str(fresh_snapshot.id))
            return await _build_profile_response(db, company, fresh_snapshot, scoring_overrides)

    # 2. Fetch from providers
    logger.info("fetching_providers", nip=nip)
    provider_results = await _fetch_all_providers(nip, company.krs, use_mock, org_credentials)

    # 3. Merge normalized data
    merged = _merge_provider_data(provider_results)
    sources = [
        {
            "provider": r.provider_name,
            "fetched_at": r.fetched_at,
            "status": "ok" if r.success else "error",
            "fields_count": r.fields_count,
            "error": r.error,
        }
        for r in provider_results
    ]

    # Quality assessment
    key_fields = [
        "name", "nip", "regon", "legal_form", "vat_status",
        "registered_address", "city", "registration_date",
        "pkd_main_code", "representatives", "bank_account_count",
    ]
    filled = sum(1 for f in key_fields if merged.get(f))
    quality = {
        "completeness_pct": round(filled / len(key_fields) * 100, 1),
        "sources_count": sum(1 for r in provider_results if r.success),
        "freshness_hours": 0,
        "confidence": "high" if filled >= 8 else "medium" if filled >= 5 else "low",
    }

    # Update company record
    if merged.get("name"):
        company.name = merged["name"]
    if merged.get("regon"):
        company.regon = merged["regon"]
    if merged.get("krs"):
        company.krs = merged["krs"]
    if merged.get("legal_form"):
        company.legal_form = merged["legal_form"]
    if merged.get("pkd_main_code"):
        company.pkd_main = merged["pkd_main_code"]
    if merged.get("pkd_codes"):
        company.pkd_codes = [p.get("code", "") if isinstance(p, dict) else p for p in merged["pkd_codes"]]

    # 4. Persist snapshot
    snapshot = CompanySnapshot(
        company_id=company.id,
        fetched_at=datetime.utcnow(),
        ttl_expires_at=datetime.utcnow() + timedelta(seconds=settings.SNAPSHOT_TTL_SECONDS),
        sources_json=sources,
        raw_json={r.provider_name: r.raw_data for r in provider_results if r.success},
        normalized_json=merged,
        quality_json=quality,
    )
    db.add(snapshot)
    await db.flush()

    # 5. Compute scoring
    score_result = compute_score(merged, scoring_overrides)
    credit_result = compute_credit_limit(
        score_result["score_0_100"],
        score_result["risk_band"],
        merged,
        score_result["components"],
    )
    material_result = recommend_materials(merged)

    # Persist score
    score_record = ScoreResult(
        company_id=company.id,
        snapshot_id=snapshot.id,
        score_0_100=score_result["score_0_100"],
        risk_band=score_result["risk_band"],
        credit_limit_suggested=credit_result["credit_limit_suggested"],
        credit_limit_min=credit_result["credit_limit_min"],
        credit_limit_max=credit_result["credit_limit_max"],
        payment_terms_days=credit_result["payment_terms_days"],
        discount_pct=credit_result["discount_pct"],
        components_json=score_result["components"],
        red_flags=score_result["red_flags"],
        green_flags=score_result["green_flags"],
        explanation_json={
            "summary": score_result["explanation_summary"],
            "credit": credit_result["explanation"],
        },
    )
    db.add(score_record)

    # Persist material recommendation
    mat_record = MaterialRecommendation(
        company_id=company.id,
        snapshot_id=snapshot.id,
        categories_json=material_result["categories"],
        explanation_json={"summary": material_result["explanation"]},
    )
    db.add(mat_record)

    await db.flush()

    # 6. Build response
    return {
        "company": _company_to_dict(company),
        "snapshot": merged,
        "sources": sources,
        "quality": quality,
        "score": {
            **score_result,
            **credit_result,
        },
        "materials": material_result,
    }


async def _get_or_create_company(db: AsyncSession, nip: str) -> Company:
    result = await db.execute(select(Company).where(Company.nip == nip))
    company = result.scalar_one_or_none()
    if not company:
        company = Company(nip=nip)
        db.add(company)
        await db.flush()
    return company


async def _get_fresh_snapshot(db: AsyncSession, company_id: uuid.UUID, ttl: int) -> CompanySnapshot | None:
    cutoff = datetime.utcnow() - timedelta(seconds=ttl)
    result = await db.execute(
        select(CompanySnapshot)
        .where(CompanySnapshot.company_id == company_id)
        .where(CompanySnapshot.fetched_at > cutoff)
        .order_by(CompanySnapshot.fetched_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _build_profile_response(
    db: AsyncSession, company: Company, snapshot: CompanySnapshot, scoring_overrides: dict | None
) -> dict:
    # Get latest score for this snapshot
    result = await db.execute(
        select(ScoreResult)
        .where(ScoreResult.snapshot_id == snapshot.id)
        .order_by(ScoreResult.created_at.desc())
        .limit(1)
    )
    score_record = result.scalar_one_or_none()

    result = await db.execute(
        select(MaterialRecommendation)
        .where(MaterialRecommendation.snapshot_id == snapshot.id)
        .order_by(MaterialRecommendation.created_at.desc())
        .limit(1)
    )
    mat_record = result.scalar_one_or_none()

    normalized = snapshot.normalized_json or {}
    score_data = None
    if score_record:
        score_data = {
            "score_0_100": score_record.score_0_100,
            "risk_band": score_record.risk_band,
            "risk_band_label": "",
            "components": score_record.components_json,
            "red_flags": score_record.red_flags,
            "green_flags": score_record.green_flags,
            "explanation_summary": (score_record.explanation_json or {}).get("summary", ""),
            "credit_limit_suggested": score_record.credit_limit_suggested,
            "credit_limit_min": score_record.credit_limit_min,
            "credit_limit_max": score_record.credit_limit_max,
            "payment_terms_days": score_record.payment_terms_days,
            "discount_pct": score_record.discount_pct,
            "explanation": (score_record.explanation_json or {}).get("credit", ""),
        }

    mat_data = None
    if mat_record:
        mat_data = {
            "categories": mat_record.categories_json,
            "explanation": (mat_record.explanation_json or {}).get("summary", ""),
        }

    return {
        "company": _company_to_dict(company),
        "snapshot": normalized,
        "sources": snapshot.sources_json or [],
        "quality": snapshot.quality_json or {},
        "score": score_data,
        "materials": mat_data,
    }


async def _fetch_all_providers(
    nip: str, krs_number: str | None, use_mock: bool, org_credentials: dict | None
) -> list[ProviderResult]:
    if use_mock:
        mock = MockProvider()
        return [await mock.fetch(nip)]

    settings = get_settings()
    tasks = []

    # Always try VAT Whitelist (public, no auth)
    vat = VATWhitelistProvider()
    tasks.append(vat.fetch(nip))

    # Try KRS if we have a KRS number
    if krs_number:
        krs = KRSProvider()
        tasks.append(krs.fetch(nip, krs_number=krs_number))

    # Try GUS if credentials available
    gus_creds = (org_credentials or {}).get("gus_regon")
    if gus_creds or settings.GUS_API_KEY:
        gus = GUSProvider()
        tasks.append(gus.fetch(nip, credentials=gus_creds))

    # Try CEIDG if credentials available
    ceidg_creds = (org_credentials or {}).get("ceidg")
    if ceidg_creds or settings.CEIDG_API_KEY:
        ceidg = CEIDGProvider()
        tasks.append(ceidg.fetch(nip, credentials=ceidg_creds))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results, handle exceptions
    provider_results = []
    for r in results:
        if isinstance(r, Exception):
            provider_results.append(ProviderResult(
                provider_name="unknown", success=False, error=str(r)
            ))
        else:
            provider_results.append(r)

    # If VAT gave us a KRS number and we didn't already have it, try KRS
    vat_result = next((r for r in provider_results if r.provider_name == "vat_whitelist" and r.success), None)
    if vat_result and not krs_number:
        vat_krs = vat_result.normalized_data.get("krs")
        if vat_krs:
            krs = KRSProvider()
            krs_result = await krs.fetch(nip, krs_number=vat_krs)
            provider_results.append(krs_result)

    return provider_results


def _merge_provider_data(results: list[ProviderResult]) -> dict:
    """
    Merge normalized data from all providers.
    Later providers override earlier ones for scalar fields.
    List fields are merged (deduplicated).
    """
    merged = {}
    # Priority order: vat_whitelist < gus_regon < ceidg < krs < mock
    priority = ["mock", "vat_whitelist", "gus_regon", "ceidg", "krs"]

    sorted_results = sorted(
        [r for r in results if r.success],
        key=lambda r: priority.index(r.provider_name) if r.provider_name in priority else 0,
    )

    for result in sorted_results:
        for key, val in result.normalized_data.items():
            if val is None:
                continue
            if key in ("pkd_codes", "representatives", "partners") and isinstance(val, list):
                existing = merged.get(key, [])
                if isinstance(existing, list):
                    # Merge lists, avoiding duplicates by name/code
                    existing_keys = set()
                    for item in existing:
                        if isinstance(item, dict):
                            existing_keys.add(item.get("code") or item.get("name", ""))
                    for item in val:
                        if isinstance(item, dict):
                            item_key = item.get("code") or item.get("name", "")
                            if item_key not in existing_keys:
                                existing.append(item)
                                existing_keys.add(item_key)
                        else:
                            if item not in existing:
                                existing.append(item)
                    merged[key] = existing
                else:
                    merged[key] = val
            else:
                merged[key] = val

    return merged


def _company_to_dict(company: Company) -> dict:
    return {
        "id": str(company.id),
        "nip": company.nip,
        "name": company.name,
        "regon": company.regon,
        "krs": company.krs,
        "country": company.country,
        "legal_form": company.legal_form,
        "pkd_main": company.pkd_main,
        "pkd_codes": company.pkd_codes,
        "created_at": company.created_at.isoformat() if company.created_at else None,
        "updated_at": company.updated_at.isoformat() if company.updated_at else None,
    }
