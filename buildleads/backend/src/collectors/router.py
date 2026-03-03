"""Collector endpoints — trigger collection runs, view status."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.permissions import require_admin
from src.database import get_db
from src.users.models import User

router = APIRouter(prefix="/api/v1/collectors", tags=["collectors"])


@router.post("/bzp/run")
async def run_bzp_collector(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a BZP collection run for the admin's tenant."""
    from src.collectors.bzp import BZPCollector
    from src.regions.models import Region
    from sqlalchemy import select

    region = (await db.execute(
        select(Region).where(Region.tenant_id == user.tenant_id).limit(1)
    )).scalar_one_or_none()

    collector = BZPCollector(
        db=db,
        tenant_id=user.tenant_id,
        region_id=region.id if region else None,
    )
    job = await collector.run()
    return {
        "job_id": str(job.id),
        "status": job.status,
        "items_found": job.items_found,
        "items_qualified": job.items_qualified,
        "error": job.error_log,
    }


@router.post("/gunb/run")
async def run_gunb_collector(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a GUNB collection run for the admin's tenant."""
    from src.collectors.gunb import GUNBCollector
    from src.regions.models import Region
    from sqlalchemy import select

    region = (await db.execute(
        select(Region).where(Region.tenant_id == user.tenant_id).limit(1)
    )).scalar_one_or_none()

    voivodeships = None
    if region and region.voivodeships:
        voivodeships = region.voivodeships

    collector = GUNBCollector(
        db=db,
        tenant_id=user.tenant_id,
        region_id=region.id if region else None,
        voivodeships=voivodeships,
    )
    job = await collector.run()
    return {
        "job_id": str(job.id),
        "status": job.status,
        "items_found": job.items_found,
        "items_qualified": job.items_qualified,
        "error": job.error_log,
    }
