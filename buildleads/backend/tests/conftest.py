"""Shared test fixtures — in-memory SQLite async engine + test client."""

import asyncio
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import Base, get_db
from src.auth.passwords import hash_password
from src.auth.jwt import create_token
from src.config import UserRole

# ── Engine ────────────────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


# ── Seed data ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def seed_tenant(db):
    """Create a test tenant."""
    from src.tenants.models import Tenant
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Company",
        slug="test-company",
        plan="growth",
        plan_status="active",
        max_users=10,
        max_regions=3,
    )
    db.add(tenant)
    await db.flush()
    return tenant


@pytest_asyncio.fixture
async def seed_region(db, seed_tenant):
    """Create a test region."""
    from src.regions.models import Region
    region = Region(
        id=uuid.uuid4(),
        tenant_id=seed_tenant.id,
        name="Mazowieckie",
        voivodeships=["mazowieckie"],
    )
    db.add(region)
    await db.flush()
    return region


@pytest_asyncio.fixture
async def seed_admin(db, seed_tenant, seed_region):
    """Create a platform_admin user."""
    from src.users.models import User
    user = User(
        id=uuid.uuid4(),
        tenant_id=seed_tenant.id,
        email="admin@test.pl",
        password_hash=hash_password("admin123"),
        first_name="Admin",
        last_name="Testowy",
        role=UserRole.PLATFORM_ADMIN.value,
        region_id=seed_region.id,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def seed_manager(db, seed_tenant, seed_region):
    """Create a manager user."""
    from src.users.models import User
    user = User(
        id=uuid.uuid4(),
        tenant_id=seed_tenant.id,
        email="manager@test.pl",
        password_hash=hash_password("test123"),
        first_name="Manager",
        last_name="Testowy",
        role=UserRole.MANAGER.value,
        region_id=seed_region.id,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def seed_salesperson(db, seed_tenant, seed_region):
    """Create a salesperson user."""
    from src.users.models import User
    user = User(
        id=uuid.uuid4(),
        tenant_id=seed_tenant.id,
        email="sales@test.pl",
        password_hash=hash_password("test123"),
        first_name="Sales",
        last_name="Testowy",
        role=UserRole.SALESPERSON.value,
        region_id=seed_region.id,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def seed_viewer(db, seed_tenant, seed_region):
    """Create a viewer user."""
    from src.users.models import User
    user = User(
        id=uuid.uuid4(),
        tenant_id=seed_tenant.id,
        email="viewer@test.pl",
        password_hash=hash_password("test123"),
        first_name="Viewer",
        last_name="Testowy",
        role=UserRole.VIEWER.value,
        region_id=seed_region.id,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def seed_lead(db, seed_tenant, seed_region):
    """Create a test lead."""
    from src.leads.models import Lead
    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=seed_tenant.id,
        region_id=seed_region.id,
        source="manual",
        name="Firma Budowlana Testowa Sp. z o.o.",
        nip="1234567890",
        city="Warszawa",
        voivodeship="mazowieckie",
        employees=50,
        revenue_pln=5_000_000,
        revenue_band="small",
        pkd="41.20",
        years_active=8.0,
        vat_status="Czynny VAT",
        basket_pln=3000,
        status="new",
    )
    db.add(lead)
    await db.flush()
    return lead


# ── Token helpers ─────────────────────────────────────────────────────

def make_token(user) -> str:
    return create_token(user.id, user.role, user.tenant_id, "access")


def auth_headers(user) -> dict:
    return {"Authorization": f"Bearer {make_token(user)}"}


# ── App client ────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(engine):
    """AsyncClient that talks to the FastAPI app with test DB."""
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    from src.main import app
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
