import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.tenants.models import Tenant


async def get_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant | None:
    return await db.get(Tenant, tenant_id)


async def list_tenants(db: AsyncSession) -> list[Tenant]:
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    return list(result.scalars().all())


async def update_tenant(db: AsyncSession, tenant: Tenant, **kwargs) -> Tenant:
    for key, val in kwargs.items():
        if val is not None:
            setattr(tenant, key, val)
    await db.commit()
    await db.refresh(tenant)
    return tenant
