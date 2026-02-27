"""Admin panel routes."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role, CurrentUser
from app.models.organization import Organization, Plan, UsageEvent
from app.models.user import User
from app.models.admin import AuditLog, AdminOverride
from app.models.company import Company
from app.schemas.admin import (
    OrgResponse, OrgUpdate, UserAdminResponse, UserAdminUpdate,
    OverrideCreate, OverrideResponse, AuditLogResponse,
    PlanResponse, SystemHealthResponse,
)

router = APIRouter()


# ── Organizations ──────────────────────────────────

@router.get("/orgs", response_model=list[OrgResponse])
async def list_orgs(
    admin: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    skip: int = 0, limit: int = 50,
):
    result = await db.execute(
        select(Organization).offset(skip).limit(limit).order_by(Organization.created_at.desc())
    )
    orgs = result.scalars().all()
    items = []
    for org in orgs:
        plan_name = None
        if org.plan_id:
            pr = await db.execute(select(Plan.name).where(Plan.id == org.plan_id))
            plan_name = pr.scalar_one_or_none()
        items.append(OrgResponse(
            id=org.id, name=org.name, plan_id=org.plan_id, plan_name=plan_name,
            status=org.status, created_at=org.created_at,
        ))
    return items


@router.patch("/orgs/{org_id}", response_model=OrgResponse)
async def update_org(
    org_id: UUID, req: OrgUpdate,
    admin: CurrentUser = Depends(require_role("superadmin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organizacja nie znaleziona")

    if req.name is not None:
        org.name = req.name
    if req.plan_id is not None:
        org.plan_id = req.plan_id
    if req.status is not None:
        org.status = req.status

    db.add(AuditLog(
        org_id=org.id, actor_user_id=admin.id,
        action="update_org", target_type="organization", target_id=str(org.id),
        diff_json=req.model_dump(exclude_none=True),
    ))

    return OrgResponse(
        id=org.id, name=org.name, plan_id=org.plan_id,
        status=org.status, created_at=org.created_at,
    )


# ── Users ──────────────────────────────────────────

@router.get("/users", response_model=list[UserAdminResponse])
async def list_users(
    admin: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    skip: int = 0, limit: int = 50,
):
    query = select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    if admin.role != "superadmin":
        query = query.where(User.org_id == admin.org_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.patch("/users/{user_id}", response_model=UserAdminResponse)
async def update_user(
    user_id: UUID, req: UserAdminUpdate,
    admin: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")

    if admin.role != "superadmin" and user.org_id != admin.org_id:
        raise HTTPException(status_code=403, detail="Brak dostępu")

    if req.role is not None:
        user.role = req.role
    if req.is_active is not None:
        user.is_active = req.is_active

    db.add(AuditLog(
        org_id=admin.org_id, actor_user_id=admin.id,
        action="update_user", target_type="user", target_id=str(user.id),
        diff_json=req.model_dump(exclude_none=True),
    ))

    return user


# ── Plans ──────────────────────────────────────────

@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(
    admin: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Plan).order_by(Plan.price_monthly))
    return result.scalars().all()


# ── Overrides ──────────────────────────────────────

@router.post("/companies/{nip}/overrides", response_model=OverrideResponse, status_code=201)
async def create_override(
    nip: str, req: OverrideCreate,
    admin: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    from app.utils.nip import clean_nip
    result = await db.execute(select(Company).where(Company.nip == clean_nip(nip)))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Firma nie znaleziona")

    override = AdminOverride(
        org_id=admin.org_id,
        company_id=company.id,
        field_path=req.field_path,
        value_json=req.value_json,
        reason=req.reason,
        created_by=admin.id,
    )
    db.add(override)
    db.add(AuditLog(
        org_id=admin.org_id, actor_user_id=admin.id,
        action="create_override", target_type="company", target_id=str(company.id),
        diff_json={"field": req.field_path, "value": req.value_json, "reason": req.reason},
    ))
    await db.flush()
    return override


# ── Audit Logs ─────────────────────────────────────

@router.get("/audit", response_model=list[AuditLogResponse])
async def list_audit_logs(
    admin: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    skip: int = 0, limit: int = 100,
):
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    if admin.role != "superadmin":
        query = query.where(AuditLog.org_id == admin.org_id)
    result = await db.execute(query)
    return result.scalars().all()


# ── System Health ──────────────────────────────────

@router.get("/system/health", response_model=SystemHealthResponse)
async def system_health(
    admin: CurrentUser = Depends(require_role("superadmin")),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timedelta
    import redis as redis_lib
    from app.config import get_settings

    settings = get_settings()

    # DB check
    try:
        await db.execute(select(func.count()).select_from(Organization))
        db_status = "ok"
    except Exception:
        db_status = "error"

    # Redis check
    try:
        r = redis_lib.from_url(settings.REDIS_URL)
        r.ping()
        redis_status = "ok"
        queue_depth = r.llen("celery") or 0
    except Exception:
        redis_status = "error"
        queue_depth = -1

    # Qdrant check
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.QDRANT_URL}/healthz")
            qdrant_status = "ok" if resp.status_code == 200 else "error"
    except Exception:
        qdrant_status = "error"

    # Stats
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    lookups_result = await db.execute(
        select(func.count()).select_from(UsageEvent)
        .where(UsageEvent.event_type == "company_lookup")
        .where(UsageEvent.created_at >= today)
    )
    lookups_today = lookups_result.scalar() or 0

    orgs_result = await db.execute(
        select(func.count()).select_from(Organization)
        .where(Organization.status == "active")
    )
    active_orgs = orgs_result.scalar() or 0

    return SystemHealthResponse(
        db_status=db_status,
        redis_status=redis_status,
        qdrant_status=qdrant_status,
        queue_depth=queue_depth,
        provider_errors_24h=0,
        active_orgs=active_orgs,
        lookups_today=lookups_today,
    )
