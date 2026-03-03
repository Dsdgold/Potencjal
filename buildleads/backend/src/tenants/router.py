"""Tenant endpoints — mostly admin-only for platform management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.permissions import get_current_user, require_admin
from src.database import get_db
from src.tenants.schemas import TenantOut, TenantUpdate
from src.tenants.service import get_tenant, list_tenants, update_tenant
from src.users.models import User

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


@router.get("/me", response_model=TenantOut)
async def my_tenant(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's tenant."""
    tenant = await get_tenant(db, user.tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    return tenant
