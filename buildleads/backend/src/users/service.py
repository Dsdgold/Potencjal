import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.passwords import hash_password
from src.config import PLAN_LIMITS, PlanType, UserRole
from src.tenants.models import Tenant
from src.users.models import User


async def list_users(db: AsyncSession, tenant_id: uuid.UUID) -> list[User]:
    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id).order_by(User.created_at.desc())
    )
    return list(result.scalars().all())


async def create_user(
    db: AsyncSession,
    tenant: Tenant,
    *,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: str = "salesperson",
    region_id: uuid.UUID | None = None,
) -> User:
    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == email.lower()))
    if existing.scalar_one_or_none():
        raise ValueError("Email already registered")

    # Check user limit
    plan = PlanType(tenant.plan)
    limits = PLAN_LIMITS[plan]
    max_users = limits["max_users"]
    if max_users > 0:
        count = (await db.execute(
            select(func.count()).select_from(User).where(User.tenant_id == tenant.id)
        )).scalar() or 0
        if count >= max_users:
            raise ValueError(f"User limit reached ({max_users}). Upgrade your plan.")

    user = User(
        tenant_id=tenant.id,
        email=email.lower().strip(),
        password_hash=hash_password(password),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        role=role,
        region_id=region_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user: User, **kwargs) -> User:
    for key, val in kwargs.items():
        if val is not None:
            setattr(user, key, val)
    await db.commit()
    await db.refresh(user)
    return user


async def deactivate_user(db: AsyncSession, user: User) -> User:
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user
