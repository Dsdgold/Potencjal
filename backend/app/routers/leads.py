import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import PACKAGE_LIMITS
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Lead, User
from app.schemas import LeadCreate, LeadList, LeadOut, LeadUpdate

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.post("", response_model=LeadOut, status_code=201)
async def create_lead(
    body: LeadCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check package lead limit
    limits = PACKAGE_LIMITS.get(user.package, PACKAGE_LIMITS["starter"])
    count_stmt = select(func.count()).select_from(Lead).where(Lead.owner_id == user.id)
    current_count = (await db.execute(count_stmt)).scalar() or 0
    if current_count >= limits["max_leads"]:
        raise HTTPException(
            403,
            f"Lead limit reached ({limits['max_leads']}). Upgrade your package.",
        )

    lead = Lead(**body.model_dump(exclude_unset=True), owner_id=user.id)
    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    # Update user leads count
    user.leads_count = current_count + 1
    await db.commit()

    return lead


@router.get("", response_model=LeadList)
async def list_leads(
    tier: str | None = None,
    city: str | None = None,
    pkd: str | None = None,
    q: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Users see only their leads; admins/managers see all
    stmt = select(Lead)
    count_stmt = select(func.count()).select_from(Lead)

    if user.role not in ("admin", "manager"):
        stmt = stmt.where(Lead.owner_id == user.id)
        count_stmt = count_stmt.where(Lead.owner_id == user.id)

    if tier:
        stmt = stmt.where(Lead.tier == tier.upper())
        count_stmt = count_stmt.where(Lead.tier == tier.upper())
    if city:
        stmt = stmt.where(Lead.city.ilike(f"%{city}%"))
        count_stmt = count_stmt.where(Lead.city.ilike(f"%{city}%"))
    if pkd:
        stmt = stmt.where(Lead.pkd.startswith(pkd))
        count_stmt = count_stmt.where(Lead.pkd.startswith(pkd))
    if q:
        pattern = f"%{q}%"
        flt = Lead.name.ilike(pattern) | Lead.nip.ilike(pattern)
        stmt = stmt.where(flt)
        count_stmt = count_stmt.where(flt)

    total = (await db.execute(count_stmt)).scalar() or 0
    result = await db.execute(stmt.order_by(Lead.created_at.desc()).offset(offset).limit(limit))
    items = list(result.scalars().all())
    return LeadList(items=items, total=total)


@router.get("/{lead_id}", response_model=LeadOut)
async def get_lead(
    lead_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    if user.role not in ("admin", "manager") and lead.owner_id != user.id:
        raise HTTPException(403, "Not your lead")
    return lead


@router.put("/{lead_id}", response_model=LeadOut)
async def update_lead(
    lead_id: uuid.UUID,
    body: LeadUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    if user.role not in ("admin", "manager") and lead.owner_id != user.id:
        raise HTTPException(403, "Not your lead")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(lead, key, val)
    await db.commit()
    await db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(
    lead_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    if user.role not in ("admin", "manager") and lead.owner_id != user.id:
        raise HTTPException(403, "Not your lead")
    await db.delete(lead)
    await db.commit()
