"""User management endpoints — list, create, update users within a tenant."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.permissions import get_current_user, require_manager
from src.config import UserRole
from src.database import get_db
from src.tenants.models import Tenant
from src.users.models import User
from src.users.schemas import UserCreate, UserOut, UserUpdate
from src.users.service import create_user, deactivate_user, list_users, update_user

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def get_users(
    user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    return await list_users(db, user.tenant_id)


@router.post("", response_model=UserOut, status_code=201)
async def add_user(
    body: UserCreate,
    user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, user.tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    # Manager can only create salesperson/viewer, not other managers
    if user.role == UserRole.MANAGER.value and body.role == "manager":
        raise HTTPException(403, "Managers cannot create other managers")

    try:
        return await create_user(
            db, tenant,
            email=body.email,
            password=body.password,
            first_name=body.first_name,
            last_name=body.last_name,
            role=body.role,
            region_id=body.region_id,
        )
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(User, user_id)
    if not target or target.tenant_id != user.tenant_id:
        raise HTTPException(404, "User not found")
    return target


@router.patch("/{user_id}", response_model=UserOut)
async def edit_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(User, user_id)
    if not target or target.tenant_id != user.tenant_id:
        raise HTTPException(404, "User not found")
    # Only manager+ can edit others; anyone can edit self
    if target.id != user.id and user.role not in (UserRole.PLATFORM_ADMIN.value, UserRole.MANAGER.value):
        raise HTTPException(403, "Cannot edit other users")
    return await update_user(db, target, **body.model_dump(exclude_unset=True))


@router.delete("/{user_id}", status_code=204)
async def remove_user(
    user_id: uuid.UUID,
    user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(User, user_id)
    if not target or target.tenant_id != user.tenant_id:
        raise HTTPException(404, "User not found")
    if target.id == user.id:
        raise HTTPException(400, "Cannot deactivate yourself")
    await deactivate_user(db, target)


@router.patch("/{user_id}/role")
async def change_role(
    user_id: uuid.UUID,
    role: str,
    user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    if role not in [r.value for r in UserRole if r != UserRole.PLATFORM_ADMIN]:
        raise HTTPException(400, f"Invalid role: {role}")
    target = await db.get(User, user_id)
    if not target or target.tenant_id != user.tenant_id:
        raise HTTPException(404, "User not found")
    # Manager cannot promote to manager
    if user.role == UserRole.MANAGER.value and role == UserRole.MANAGER.value:
        raise HTTPException(403, "Managers cannot promote to manager")
    target.role = role
    await db.commit()
    return {"status": "ok", "role": role}


@router.patch("/{user_id}/region")
async def assign_region(
    user_id: uuid.UUID,
    region_id: uuid.UUID,
    user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(User, user_id)
    if not target or target.tenant_id != user.tenant_id:
        raise HTTPException(404, "User not found")
    target.region_id = region_id
    await db.commit()
    return {"status": "ok", "region_id": str(region_id)}
