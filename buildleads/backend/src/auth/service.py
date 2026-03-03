"""Auth business logic — register (creates tenant + user), login, token refresh."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt import create_token
from src.auth.passwords import hash_password, verify_password
from src.config import PLAN_LIMITS, PlanType, UserRole
from src.regions.models import Region
from src.tenants.models import Tenant
from src.users.models import User


async def register_tenant(
    db: AsyncSession,
    *,
    company_name: str,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
) -> tuple[Tenant, User]:
    """Create a new tenant + the first user (manager role)."""
    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == email.lower()))
    if existing.scalar_one_or_none():
        raise ValueError("Email already registered")

    # Create tenant
    slug = company_name.lower().replace(" ", "-").replace(".", "")[:80]
    # Ensure slug uniqueness
    slug_check = await db.execute(select(Tenant).where(Tenant.slug == slug))
    if slug_check.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    limits = PLAN_LIMITS[PlanType.TRIAL]
    tenant = Tenant(
        name=company_name,
        slug=slug,
        plan=PlanType.TRIAL.value,
        max_users=limits["max_users"],
        max_regions=limits["max_regions"],
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=14),
    )
    db.add(tenant)
    await db.flush()

    # Create default region
    region = Region(
        tenant_id=tenant.id,
        name="Domyślny",
        voivodeships=[],
    )
    db.add(region)
    await db.flush()

    # Create first user as manager
    user = User(
        tenant_id=tenant.id,
        email=email.lower().strip(),
        password_hash=hash_password(password),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        role=UserRole.MANAGER.value,
        region_id=region.id,
        email_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(tenant)
    await db.refresh(user)
    return tenant, user


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    """Verify credentials and return the user."""
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise ValueError("Invalid email or password")
    if not user.is_active:
        raise ValueError("Account deactivated")
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    return user


def issue_tokens(user: User) -> dict:
    """Create access + refresh token pair."""
    return {
        "access_token": create_token(user.id, user.role, user.tenant_id, "access"),
        "refresh_token": create_token(user.id, user.role, user.tenant_id, "refresh"),
        "token_type": "bearer",
    }
