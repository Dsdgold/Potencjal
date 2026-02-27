"""Background lookup tasks."""

import asyncio
from app.celery_app import app
import structlog

logger = structlog.get_logger()


@app.task(name="app.tasks.lookup.async_lookup_company", bind=True, max_retries=3)
def async_lookup_company(self, nip: str, org_id: str = None, user_id: str = None, force: bool = False):
    """Run company lookup as background task."""
    try:
        from app.database import async_session
        from app.services.lookup import lookup_company
        import uuid

        async def _run():
            async with async_session() as db:
                result = await lookup_company(
                    nip=nip,
                    db=db,
                    org_id=uuid.UUID(org_id) if org_id else None,
                    user_id=uuid.UUID(user_id) if user_id else None,
                    force_refresh=force,
                    use_mock=True,
                )
                await db.commit()
                return result

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(_run())
            return {"status": "ok", "nip": nip, "score": result.get("score", {}).get("score_0_100")}
        finally:
            loop.close()

    except Exception as exc:
        logger.error("async_lookup_failed", nip=nip, error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@app.task(name="app.tasks.lookup.refresh_watchlist")
def refresh_watchlist():
    """Refresh all watchlisted companies."""
    try:
        from sqlalchemy import select
        from app.database import async_session
        from app.models.crm import Watchlist
        from app.models.company import Company
        import asyncio

        async def _run():
            async with async_session() as db:
                result = await db.execute(
                    select(Company.nip)
                    .join(Watchlist, Watchlist.company_id == Company.id)
                    .distinct()
                )
                nips = [r[0] for r in result.all()]
                return nips

        loop = asyncio.new_event_loop()
        try:
            nips = loop.run_until_complete(_run())
        finally:
            loop.close()

        for nip in nips:
            async_lookup_company.delay(nip, force=True)

        logger.info("watchlist_refresh_queued", count=len(nips))
        return {"refreshed": len(nips)}

    except Exception as e:
        logger.error("watchlist_refresh_failed", error=str(e))
        return {"error": str(e)}
