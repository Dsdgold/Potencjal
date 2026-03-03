"""Maintenance tasks — trial expiry, cleanup."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.tasks.celery_app import app
from src.tasks._async_helpers import run_async

logger = logging.getLogger(__name__)


@app.task
def check_trial_expiry():
    """Deactivate tenants whose trial has expired."""
    return run_async(_check_trial_expiry_async())


async def _check_trial_expiry_async():
    from sqlalchemy import select
    from src.database import async_session
    from src.tenants.models import Tenant

    deactivated = 0
    now = datetime.now(timezone.utc)

    async with async_session() as db:
        result = await db.execute(
            select(Tenant).where(
                Tenant.plan == "trial",
                Tenant.is_active == True,  # noqa: E712
                Tenant.trial_ends_at.isnot(None),
                Tenant.trial_ends_at < now,
            )
        )
        expired = result.scalars().all()

        for tenant in expired:
            tenant.is_active = False
            tenant.plan_status = "expired"
            deactivated += 1
            logger.info("Trial expired for tenant: %s (%s)", tenant.name, tenant.id)

        await db.commit()

    logger.info("Trial expiry check: %d tenants deactivated", deactivated)
    return {"deactivated": deactivated}
