"""Lead CRUD with tenant isolation and region-based access."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import UserRole
from src.leads.filters import LeadFilters
from src.leads.models import Lead, LeadAction
from src.users.models import User


async def list_leads(
    db: AsyncSession,
    user: User,
    filters: LeadFilters,
) -> tuple[list[Lead], int]:
    """List leads with tenant isolation and role-based filtering."""
    stmt = select(Lead).where(Lead.tenant_id == user.tenant_id)
    count_stmt = select(func.count()).select_from(Lead).where(Lead.tenant_id == user.tenant_id)

    # Salesperson sees only their region; viewer too
    if user.role in (UserRole.SALESPERSON.value, UserRole.VIEWER.value) and user.region_id:
        stmt = stmt.where(Lead.region_id == user.region_id)
        count_stmt = count_stmt.where(Lead.region_id == user.region_id)

    # Apply filters
    if filters.status:
        stmt = stmt.where(Lead.status == filters.status)
        count_stmt = count_stmt.where(Lead.status == filters.status)
    if filters.category:
        stmt = stmt.where(Lead.category == filters.category)
        count_stmt = count_stmt.where(Lead.category == filters.category)
    if filters.source:
        stmt = stmt.where(Lead.source == filters.source)
        count_stmt = count_stmt.where(Lead.source == filters.source)
    if filters.tier:
        stmt = stmt.where(Lead.tier == filters.tier.upper())
        count_stmt = count_stmt.where(Lead.tier == filters.tier.upper())
    if filters.city:
        stmt = stmt.where(Lead.city.ilike(f"%{filters.city}%"))
        count_stmt = count_stmt.where(Lead.city.ilike(f"%{filters.city}%"))
    if filters.pkd:
        stmt = stmt.where(Lead.pkd.startswith(filters.pkd))
        count_stmt = count_stmt.where(Lead.pkd.startswith(filters.pkd))
    if filters.region_id:
        stmt = stmt.where(Lead.region_id == filters.region_id)
        count_stmt = count_stmt.where(Lead.region_id == filters.region_id)
    if filters.score_min is not None:
        stmt = stmt.where(Lead.score >= filters.score_min)
        count_stmt = count_stmt.where(Lead.score >= filters.score_min)
    if filters.score_max is not None:
        stmt = stmt.where(Lead.score <= filters.score_max)
        count_stmt = count_stmt.where(Lead.score <= filters.score_max)
    if filters.date_from:
        stmt = stmt.where(Lead.created_at >= filters.date_from)
        count_stmt = count_stmt.where(Lead.created_at >= filters.date_from)
    if filters.date_to:
        stmt = stmt.where(Lead.created_at <= filters.date_to)
        count_stmt = count_stmt.where(Lead.created_at <= filters.date_to)
    if filters.q:
        pattern = f"%{filters.q}%"
        flt = Lead.name.ilike(pattern) | Lead.nip.ilike(pattern)
        stmt = stmt.where(flt)
        count_stmt = count_stmt.where(flt)

    total = (await db.execute(count_stmt)).scalar() or 0
    result = await db.execute(
        stmt.order_by(Lead.created_at.desc())
        .offset(filters.offset)
        .limit(filters.per_page)
    )
    return list(result.scalars().all()), total


async def get_lead(db: AsyncSession, lead_id: uuid.UUID, user: User) -> Lead | None:
    lead = await db.get(Lead, lead_id)
    if not lead or lead.tenant_id != user.tenant_id:
        return None
    # Salesperson/viewer can only see leads in their region
    if user.role in (UserRole.SALESPERSON.value, UserRole.VIEWER.value):
        if user.region_id and lead.region_id != user.region_id:
            return None
    return lead


async def create_lead(db: AsyncSession, user: User, **kwargs) -> Lead:
    lead = Lead(tenant_id=user.tenant_id, **kwargs)
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead


async def update_lead(db: AsyncSession, lead: Lead, **kwargs) -> Lead:
    for key, val in kwargs.items():
        if val is not None:
            setattr(lead, key, val)
    await db.commit()
    await db.refresh(lead)
    return lead


async def delete_lead(db: AsyncSession, lead: Lead) -> None:
    await db.delete(lead)
    await db.commit()


async def add_action(
    db: AsyncSession,
    lead_id: uuid.UUID,
    user_id: uuid.UUID,
    action: str,
    note: str | None = None,
) -> LeadAction:
    la = LeadAction(lead_id=lead_id, user_id=user_id, action=action, note=note)
    db.add(la)
    await db.commit()
    await db.refresh(la)
    return la


async def list_actions(db: AsyncSession, lead_id: uuid.UUID) -> list[LeadAction]:
    result = await db.execute(
        select(LeadAction)
        .where(LeadAction.lead_id == lead_id)
        .order_by(LeadAction.created_at.desc())
    )
    return list(result.scalars().all())
