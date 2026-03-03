"""Dashboard API — KPI summaries, top leads, conversion funnel, breakdowns."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import cast, func, select, Date
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.permissions import get_current_user
from src.config import UserRole
from src.database import get_db
from src.leads.models import Lead
from src.users.models import User

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _base_filter(user: User):
    """Base query filter: tenant + region for salesperson/viewer."""
    conditions = [Lead.tenant_id == user.tenant_id]
    if user.role in (UserRole.SALESPERSON.value, UserRole.VIEWER.value) and user.region_id:
        conditions.append(Lead.region_id == user.region_id)
    return conditions


@router.get("/summary")
async def summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conds = _base_filter(user)

    total = (await db.execute(
        select(func.count()).select_from(Lead).where(*conds)
    )).scalar() or 0

    new = (await db.execute(
        select(func.count()).select_from(Lead).where(*conds, Lead.status == "new")
    )).scalar() or 0

    contacted = (await db.execute(
        select(func.count()).select_from(Lead).where(*conds, Lead.status == "contacted")
    )).scalar() or 0

    won = (await db.execute(
        select(func.count()).select_from(Lead).where(*conds, Lead.status == "won")
    )).scalar() or 0

    pipeline = (await db.execute(
        select(func.coalesce(func.sum(Lead.annual_potential), 0))
        .where(*conds, Lead.annual_potential.isnot(None))
    )).scalar() or 0

    avg_score = (await db.execute(
        select(func.avg(Lead.score)).where(*conds, Lead.score.isnot(None))
    )).scalar()

    return {
        "total": total,
        "new": new,
        "contacted": contacted,
        "won": won,
        "pipeline_pln": pipeline,
        "avg_score": round(avg_score) if avg_score else 0,
    }


@router.get("/top-leads")
async def top_leads(
    limit: int = 10,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conds = _base_filter(user)
    result = await db.execute(
        select(Lead)
        .where(*conds, Lead.score.isnot(None))
        .order_by(Lead.score.desc())
        .limit(limit)
    )
    leads = result.scalars().all()
    return [
        {
            "id": str(lead.id),
            "name": lead.name,
            "city": lead.city,
            "score": lead.score,
            "tier": lead.tier,
            "annual_potential": lead.annual_potential,
            "status": lead.status,
            "source": lead.source,
        }
        for lead in leads
    ]


@router.get("/conversion")
async def conversion(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Funnel: new → contacted → offer_sent → won."""
    conds = _base_filter(user)
    stages = ["new", "contacted", "offer_sent", "won"]
    result = {}
    for stage in stages:
        count = (await db.execute(
            select(func.count()).select_from(Lead).where(*conds, Lead.status == stage)
        )).scalar() or 0
        result[stage] = count
    return result


@router.get("/by-source")
async def by_source(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lead counts grouped by source (bzp, gunb, manual, osint, etc.)."""
    conds = _base_filter(user)
    result = await db.execute(
        select(Lead.source, func.count())
        .where(*conds)
        .group_by(Lead.source)
        .order_by(func.count().desc())
    )
    return {row[0]: row[1] for row in result}


@router.get("/by-region")
async def by_region(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lead counts grouped by region."""
    from src.regions.models import Region

    conds = _base_filter(user)
    result = await db.execute(
        select(Region.name, func.count())
        .join(Lead, Lead.region_id == Region.id)
        .where(*conds)
        .group_by(Region.name)
        .order_by(func.count().desc())
    )
    return {row[0]: row[1] for row in result}


@router.get("/by-category")
async def by_category(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lead counts grouped by material category."""
    conds = _base_filter(user)
    result = await db.execute(
        select(Lead.category, func.count())
        .where(*conds, Lead.category.isnot(None))
        .group_by(Lead.category)
        .order_by(func.count().desc())
    )
    return {row[0]: row[1] for row in result}


@router.get("/by-tier")
async def by_tier(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lead counts grouped by tier (S/A/B/C)."""
    conds = _base_filter(user)
    result = await db.execute(
        select(Lead.tier, func.count())
        .where(*conds, Lead.tier.isnot(None))
        .group_by(Lead.tier)
        .order_by(Lead.tier)
    )
    return {row[0]: row[1] for row in result}


@router.get("/trends")
async def trends(
    days: int = Query(30, ge=7, le=90),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Daily new leads count over the past N days."""
    conds = _base_filter(user)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            cast(Lead.created_at, Date).label("day"),
            func.count().label("count"),
        )
        .where(*conds, Lead.created_at >= cutoff)
        .group_by("day")
        .order_by("day")
    )

    return [
        {"date": str(row.day), "count": row.count}
        for row in result
    ]


@router.get("/pipeline")
async def pipeline_value(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pipeline value breakdown by status."""
    conds = _base_filter(user)
    statuses = ["new", "contacted", "offer_sent"]
    result = {}
    for status in statuses:
        value = (await db.execute(
            select(func.coalesce(func.sum(Lead.annual_potential), 0))
            .where(*conds, Lead.status == status, Lead.annual_potential.isnot(None))
        )).scalar() or 0
        count = (await db.execute(
            select(func.count()).select_from(Lead)
            .where(*conds, Lead.status == status)
        )).scalar() or 0
        result[status] = {"count": count, "value_pln": value}
    return result
