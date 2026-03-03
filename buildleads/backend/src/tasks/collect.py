"""Collection tasks — BZP and GUNB data fetching via Celery."""

from __future__ import annotations

import asyncio
import logging

from src.tasks.celery_app import app
from src.tasks._async_helpers import run_async

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def collect_bzp(self):
    """Fetch construction tenders from BZP for all active tenants."""
    return run_async(_collect_bzp_async())


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def collect_gunb(self):
    """Fetch building permits from GUNB for all active tenants."""
    return run_async(_collect_gunb_async())


async def _collect_bzp_async():
    from sqlalchemy import select
    from src.database import async_session
    from src.tenants.models import Tenant
    from src.regions.models import Region
    from src.collectors.bzp import BZPCollector

    results = []
    async with async_session() as db:
        tenants = (await db.execute(
            select(Tenant).where(Tenant.is_active == True)  # noqa: E712
        )).scalars().all()

        for tenant in tenants:
            # Get first region as default
            region = (await db.execute(
                select(Region).where(Region.tenant_id == tenant.id).limit(1)
            )).scalar_one_or_none()

            collector = BZPCollector(
                db=db,
                tenant_id=tenant.id,
                region_id=region.id if region else None,
            )
            job = await collector.run()
            results.append({
                "tenant": tenant.name,
                "status": job.status,
                "found": job.items_found,
                "qualified": job.items_qualified,
            })
            logger.info(
                "BZP collect for %s: %s found, %s new leads",
                tenant.name, job.items_found, job.items_qualified,
            )

    return results


async def _collect_gunb_async():
    from sqlalchemy import select
    from src.database import async_session
    from src.tenants.models import Tenant
    from src.regions.models import Region
    from src.collectors.gunb import GUNBCollector

    results = []
    async with async_session() as db:
        tenants = (await db.execute(
            select(Tenant).where(Tenant.is_active == True)  # noqa: E712
        )).scalars().all()

        for tenant in tenants:
            # Get first region + its voivodeships for filtering
            region = (await db.execute(
                select(Region).where(Region.tenant_id == tenant.id).limit(1)
            )).scalar_one_or_none()

            voivodeships = None
            if region and region.voivodeships:
                voivodeships = region.voivodeships

            collector = GUNBCollector(
                db=db,
                tenant_id=tenant.id,
                region_id=region.id if region else None,
                voivodeships=voivodeships,
            )
            job = await collector.run()
            results.append({
                "tenant": tenant.name,
                "status": job.status,
                "found": job.items_found,
                "qualified": job.items_qualified,
            })
            logger.info(
                "GUNB collect for %s: %s found, %s new leads",
                tenant.name, job.items_found, job.items_qualified,
            )

    return results
