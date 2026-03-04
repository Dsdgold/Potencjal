"""BuildLeads API — FastAPI entry point.

Evolved from Potencjal MVP into a multi-tenant SaaS platform.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from src.config import UserRole, settings
from src.database import async_session, engine, Base

# Import all models for table creation
from src.tenants.models import Tenant  # noqa: F401
from src.users.models import User  # noqa: F401
from src.regions.models import Region  # noqa: F401
from src.leads.models import Lead, LeadAction, ScoringHistory  # noqa: F401
from src.notifications.models import Notification, EmailLog, ScrapeJob, StripeEvent  # noqa: F401

# Import routers
from src.auth.router import router as auth_router
from src.tenants.router import router as tenants_router
from src.users.router import router as users_router
from src.regions.router import router as regions_router
from src.leads.router import router as leads_router
from src.qualifier.router import router as scoring_router
from src.dashboard.router import router as dashboard_router
from src.notifications.router import router as notifications_router
from src.admin.router import router as admin_router
from src.billing.router import router as billing_router
from src.collectors.router import router as collectors_router
from src.qualifier.osint_router import router as osint_router
from src.qualifier.ai_router import router as ai_router

from src.auth.passwords import hash_password


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (use Alembic for production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed platform admin if no users exist
    async with async_session() as db:
        result = await db.execute(select(User).limit(1))
        if not result.scalar_one_or_none():
            # Create platform admin tenant
            import uuid
            from datetime import datetime, timezone

            tenant = Tenant(
                name="BuildLeads Platform",
                slug="buildleads-platform",
                plan="enterprise",
                plan_status="active",
                max_users=-1,
                max_regions=-1,
            )
            db.add(tenant)
            await db.flush()

            region = Region(
                tenant_id=tenant.id,
                name="Cała Polska",
                voivodeships=[],
            )
            db.add(region)
            await db.flush()

            admin = User(
                tenant_id=tenant.id,
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                first_name="Platform",
                last_name="Admin",
                role=UserRole.PLATFORM_ADMIN.value,
                region_id=region.id,
                is_active=True,
                email_verified=True,
            )
            db.add(admin)
            await db.commit()
    yield


app = FastAPI(
    title="BuildLeads API",
    description="B2B lead qualification platform for Polish construction materials sector",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(auth_router)
app.include_router(tenants_router)
app.include_router(users_router)
app.include_router(regions_router)
app.include_router(leads_router)
app.include_router(scoring_router)
app.include_router(dashboard_router)
app.include_router(notifications_router)
app.include_router(admin_router)
app.include_router(billing_router)
app.include_router(collectors_router)
app.include_router(osint_router)
app.include_router(ai_router)


@app.get("/health")
async def health():
    return {"status": "ok", "app": "buildleads"}
