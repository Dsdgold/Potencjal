"""Maintenance tasks: cleanup, GDPR retention."""

from app.celery_app import app
import structlog

logger = structlog.get_logger()


@app.task(name="app.tasks.maintenance.cleanup_expired_snapshots")
def cleanup_expired_snapshots():
    """Remove snapshots past their TTL (GDPR data minimization)."""
    import asyncio
    from datetime import datetime
    from sqlalchemy import delete
    from app.database import async_session
    from app.models.company import CompanySnapshot

    async def _run():
        async with async_session() as db:
            result = await db.execute(
                delete(CompanySnapshot).where(
                    CompanySnapshot.ttl_expires_at < datetime.utcnow()
                )
            )
            await db.commit()
            return result.rowcount

    loop = asyncio.new_event_loop()
    try:
        count = loop.run_until_complete(_run())
        logger.info("cleanup_snapshots", deleted=count)
        return {"deleted": count}
    finally:
        loop.close()
