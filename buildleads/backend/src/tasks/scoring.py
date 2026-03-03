"""Scoring tasks — batch score unscored leads."""

from __future__ import annotations

import logging

from src.tasks.celery_app import app
from src.tasks._async_helpers import run_async

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=2, default_retry_delay=30)
def score_unscored_leads(self):
    """Score all leads that have no score yet."""
    return run_async(_score_unscored_async())


async def _score_unscored_async():
    from sqlalchemy import select
    from src.database import async_session
    from src.leads.models import Lead
    from src.qualifier.service import score_lead

    scored = 0
    async with async_session() as db:
        result = await db.execute(
            select(Lead)
            .where(Lead.score.is_(None))
            .order_by(Lead.created_at.desc())
            .limit(500)
        )
        leads = result.scalars().all()

        for lead in leads:
            try:
                await score_lead(db, lead)
                scored += 1
            except Exception as exc:
                logger.warning("Failed to score lead %s: %s", lead.id, exc)

    logger.info("Scored %d/%d unscored leads", scored, len(leads))
    return {"total": len(leads), "scored": scored}
