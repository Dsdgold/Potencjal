"""Platform admin endpoints — tenant management, scrape jobs, system health."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.permissions import require_admin
from src.config import PLAN_LIMITS, PlanType
from src.database import get_db
from src.leads.models import Lead
from src.notifications.models import ScrapeJob
from src.tenants.models import Tenant
from src.tenants.schemas import TenantOut, TenantUpdate
from src.users.models import User

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/tenants", response_model=list[TenantOut])
async def list_tenants(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    return list(result.scalars().all())


@router.patch("/tenants/{tenant_id}", response_model=TenantOut)
async def edit_tenant(
    tenant_id: uuid.UUID,
    body: TenantUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    for key, val in body.model_dump(exclude_unset=True).items():
        if val is not None:
            setattr(tenant, key, val)
    # If plan changed, update limits
    if body.plan:
        plan = PlanType(body.plan)
        limits = PLAN_LIMITS[plan]
        tenant.max_users = limits["max_users"]
        tenant.max_regions = limits["max_regions"]
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.get("/tenants/{tenant_id}/usage")
async def tenant_usage(
    tenant_id: uuid.UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user_count = (await db.execute(
        select(func.count()).select_from(User).where(User.tenant_id == tenant_id)
    )).scalar() or 0
    lead_count = (await db.execute(
        select(func.count()).select_from(Lead).where(Lead.tenant_id == tenant_id)
    )).scalar() or 0
    return {"users": user_count, "leads": lead_count}


@router.get("/scrape-jobs")
async def list_scrape_jobs(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScrapeJob).order_by(ScrapeJob.created_at.desc()).limit(50)
    )
    jobs = result.scalars().all()
    return [
        {
            "id": str(j.id),
            "source": j.source,
            "status": j.status,
            "items_found": j.items_found,
            "items_qualified": j.items_qualified,
            "error_log": j.error_log,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "finished_at": j.finished_at.isoformat() if j.finished_at else None,
        }
        for j in jobs
    ]


@router.get("/system/health")
async def system_health(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    services = {"db": "ok"}

    # Check Redis
    try:
        import redis as redis_lib
        from src.config import settings as _settings
        r = redis_lib.from_url(_settings.redis_url, socket_timeout=2)
        r.ping()
        services["redis"] = "ok"
    except Exception:
        services["redis"] = "unavailable"

    # Check Ollama
    try:
        from src.qualifier.ollama_client import is_available
        services["ollama"] = "ok" if await is_available() else "unavailable"
    except Exception:
        services["ollama"] = "unavailable"

    overall = "ok" if services["db"] == "ok" and services["redis"] == "ok" else "degraded"
    return {"status": overall, "services": services}
