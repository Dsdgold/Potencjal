"""Dashboard API — KPI summaries, top leads, timeline."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
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
            "id": str(l.id),
            "name": l.name,
            "city": l.city,
            "score": l.score,
            "tier": l.tier,
            "annual_potential": l.annual_potential,
            "status": l.status,
        }
        for l in leads
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
