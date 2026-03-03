"""Role-based permission system — 4 roles for BuildLeads.

Hierarchy (highest to lowest):
  platform_admin > manager > salesperson > viewer

Usage in routers:
  user = Depends(require_admin)
  user = Depends(require_manager)
  user = Depends(require_salesperson)
  user = Depends(require_any)
"""

import uuid

import jwt as pyjwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import UserRole
from src.database import get_db
from src.users.models import User
from src.auth.jwt import decode_token


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    token = auth[7:]
    try:
        payload = decode_token(token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(401, "Invalid token type")

    user = await db.get(User, uuid.UUID(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")
    return user


async def get_optional_user(request: Request, db: AsyncSession = Depends(get_db)) -> User | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None


def _require_roles(*allowed_roles: UserRole):
    async def dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in [r.value for r in allowed_roles]:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return dep


# Pre-built permission dependencies
require_admin = _require_roles(UserRole.PLATFORM_ADMIN)
require_manager = _require_roles(UserRole.PLATFORM_ADMIN, UserRole.MANAGER)
require_salesperson = _require_roles(UserRole.PLATFORM_ADMIN, UserRole.MANAGER, UserRole.SALESPERSON)
require_any = _require_roles(UserRole.PLATFORM_ADMIN, UserRole.MANAGER, UserRole.SALESPERSON, UserRole.VIEWER)
