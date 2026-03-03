"""Region endpoints — CRUD for geographic regions within a tenant."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.permissions import get_current_user, require_manager
from src.database import get_db
from src.regions.models import Region
from src.regions.schemas import RegionCreate, RegionOut, RegionUpdate
from src.regions.service import create_region, delete_region, list_regions, update_region
from src.users.models import User

router = APIRouter(prefix="/api/v1/regions", tags=["regions"])


@router.get("", response_model=list[RegionOut])
async def get_regions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_regions(db, user.tenant_id)


@router.post("", response_model=RegionOut, status_code=201)
async def add_region(
    body: RegionCreate,
    user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    return await create_region(db, user.tenant_id, body.name, body.voivodeships)


@router.patch("/{region_id}", response_model=RegionOut)
async def edit_region(
    region_id: uuid.UUID,
    body: RegionUpdate,
    user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    region = await db.get(Region, region_id)
    if not region or region.tenant_id != user.tenant_id:
        raise HTTPException(404, "Region not found")
    return await update_region(db, region, **body.model_dump(exclude_unset=True))


@router.delete("/{region_id}", status_code=204)
async def remove_region(
    region_id: uuid.UUID,
    user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    region = await db.get(Region, region_id)
    if not region or region.tenant_id != user.tenant_id:
        raise HTTPException(404, "Region not found")
    await delete_region(db, region)
