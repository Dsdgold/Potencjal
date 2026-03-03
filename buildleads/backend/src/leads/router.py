"""Lead endpoints — CRUD with tenant isolation, region-based access, filters."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.permissions import get_current_user, require_salesperson
from src.config import UserRole
from src.database import get_db
from src.leads.filters import LeadFilters
from src.leads.models import Lead
from src.leads.schemas import (
    LeadActionCreate,
    LeadActionOut,
    LeadCreate,
    LeadList,
    LeadOut,
    LeadUpdate,
)
from src.leads.service import (
    add_action,
    create_lead,
    delete_lead,
    get_lead,
    list_actions,
    list_leads,
    update_lead,
)
from src.users.models import User

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])


@router.get("", response_model=LeadList)
async def get_leads(
    filters: LeadFilters = Depends(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await list_leads(db, user, filters)
    return LeadList(items=items, total=total)


@router.get("/stats")
async def lead_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lead counts per status and per region."""
    base = select(Lead).where(Lead.tenant_id == user.tenant_id)
    if user.role in (UserRole.SALESPERSON.value, UserRole.VIEWER.value) and user.region_id:
        base = base.where(Lead.region_id == user.region_id)

    # Count per status
    status_stmt = (
        select(Lead.status, func.count())
        .where(Lead.tenant_id == user.tenant_id)
        .group_by(Lead.status)
    )
    status_result = await db.execute(status_stmt)
    by_status = {row[0]: row[1] for row in status_result}

    # Count per tier
    tier_stmt = (
        select(Lead.tier, func.count())
        .where(Lead.tenant_id == user.tenant_id)
        .where(Lead.tier.isnot(None))
        .group_by(Lead.tier)
    )
    tier_result = await db.execute(tier_stmt)
    by_tier = {row[0]: row[1] for row in tier_result}

    total = sum(by_status.values())
    return {"total": total, "by_status": by_status, "by_tier": by_tier}


@router.get("/{lead_id}", response_model=LeadOut)
async def get_single_lead(
    lead_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lead = await get_lead(db, lead_id, user)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead


@router.post("", response_model=LeadOut, status_code=201)
async def add_lead(
    body: LeadCreate,
    user: User = Depends(require_salesperson),
    db: AsyncSession = Depends(get_db),
):
    return await create_lead(db, user, **body.model_dump(exclude_unset=True))


@router.patch("/{lead_id}", response_model=LeadOut)
async def edit_lead(
    lead_id: uuid.UUID,
    body: LeadUpdate,
    user: User = Depends(require_salesperson),
    db: AsyncSession = Depends(get_db),
):
    lead = await get_lead(db, lead_id, user)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return await update_lead(db, lead, **body.model_dump(exclude_unset=True))


@router.patch("/{lead_id}/status")
async def change_status(
    lead_id: uuid.UUID,
    status: str,
    user: User = Depends(require_salesperson),
    db: AsyncSession = Depends(get_db),
):
    lead = await get_lead(db, lead_id, user)
    if not lead:
        raise HTTPException(404, "Lead not found")
    lead.status = status
    await db.commit()
    # Record the action
    await add_action(db, lead.id, user.id, "status_changed", f"Status → {status}")
    return {"status": "ok", "new_status": status}


@router.delete("/{lead_id}", status_code=204)
async def remove_lead(
    lead_id: uuid.UUID,
    user: User = Depends(require_salesperson),
    db: AsyncSession = Depends(get_db),
):
    lead = await get_lead(db, lead_id, user)
    if not lead:
        raise HTTPException(404, "Lead not found")
    await delete_lead(db, lead)


@router.post("/{lead_id}/actions", response_model=LeadActionOut, status_code=201)
async def add_lead_action(
    lead_id: uuid.UUID,
    body: LeadActionCreate,
    user: User = Depends(require_salesperson),
    db: AsyncSession = Depends(get_db),
):
    lead = await get_lead(db, lead_id, user)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return await add_action(db, lead.id, user.id, body.action, body.note)


@router.get("/{lead_id}/actions", response_model=list[LeadActionOut])
async def get_lead_actions(
    lead_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lead = await get_lead(db, lead_id, user)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return await list_actions(db, lead.id)
