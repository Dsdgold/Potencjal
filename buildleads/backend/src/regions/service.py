import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.regions.models import Region


async def list_regions(db: AsyncSession, tenant_id: uuid.UUID) -> list[Region]:
    result = await db.execute(
        select(Region).where(Region.tenant_id == tenant_id).order_by(Region.created_at)
    )
    return list(result.scalars().all())


async def create_region(db: AsyncSession, tenant_id: uuid.UUID, name: str, voivodeships: list[str]) -> Region:
    region = Region(tenant_id=tenant_id, name=name, voivodeships=voivodeships)
    db.add(region)
    await db.commit()
    await db.refresh(region)
    return region


async def update_region(db: AsyncSession, region: Region, **kwargs) -> Region:
    for key, val in kwargs.items():
        if val is not None:
            setattr(region, key, val)
    await db.commit()
    await db.refresh(region)
    return region


async def delete_region(db: AsyncSession, region: Region) -> None:
    await db.delete(region)
    await db.commit()
