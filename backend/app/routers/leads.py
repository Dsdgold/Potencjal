import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Lead
from app.schemas import LeadCreate, LeadList, LeadOut, LeadUpdate

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.post("", response_model=LeadOut, status_code=201)
async def create_lead(body: LeadCreate, db: AsyncSession = Depends(get_db)):
    lead = Lead(**body.model_dump(exclude_unset=True))
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead


@router.get("", response_model=LeadList)
async def list_leads(
    tier: str | None = None,
    city: str | None = None,
    pkd: str | None = None,
    q: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Lead)
    count_stmt = select(func.count()).select_from(Lead)

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
async def get_lead(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead


@router.put("/{lead_id}", response_model=LeadOut)
async def update_lead(lead_id: uuid.UUID, body: LeadUpdate, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(lead, key, val)
    await db.commit()
    await db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    await db.delete(lead)
    await db.commit()
