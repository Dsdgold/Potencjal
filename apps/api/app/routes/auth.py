"""Auth routes: register, login, refresh, me."""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.organization import Organization, Plan
from app.models.admin import AuditLog
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse,
    RefreshRequest, UserResponse, UserUpdate,
)
from app.services.auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.middleware.auth import get_current_user, CurrentUser

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email już zarejestrowany")

    # Get free plan
    plan_result = await db.execute(select(Plan).where(Plan.code == "free"))
    free_plan = plan_result.scalar_one_or_none()

    # Create organization
    org = Organization(name=req.org_name, plan_id=free_plan.id if free_plan else None)
    db.add(org)
    await db.flush()

    # Create user (admin of their org)
    user = User(
        org_id=org.id,
        email=req.email,
        password_hash=hash_password(req.password),
        full_name=req.full_name,
        role="admin",
    )
    db.add(user)
    await db.flush()

    # Audit
    db.add(AuditLog(
        org_id=org.id, actor_user_id=user.id,
        action="register", target_type="user", target_id=str(user.id),
    ))

    access = create_access_token(user.id, org.id, user.role)
    refresh = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=get_settings_val(),
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Nieprawidłowy email lub hasło")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Konto dezaktywowane")

    user.last_login = datetime.utcnow()

    access = create_access_token(user.id, user.org_id, user.role)
    refresh = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=get_settings_val(),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Nieprawidłowy refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Użytkownik nieaktywny")

    access = create_access_token(user.id, user.org_id, user.role)
    refresh_tok = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh_tok,
        expires_in=get_settings_val(),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_name = None
    if current_user.org_id:
        result = await db.execute(select(Organization).where(Organization.id == current_user.org_id))
        org = result.scalar_one_or_none()
        org_name = org.name if org else None

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        org_id=current_user.org_id,
        org_name=org_name,
        is_active=current_user.is_active,
        created_at=datetime.utcnow(),
    )


@router.patch("/me", response_model=UserResponse)
async def update_me(
    req: UserUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one()

    if req.full_name is not None:
        user.full_name = req.full_name
    if req.email is not None:
        user.email = req.email

    return UserResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        role=user.role, org_id=user.org_id, is_active=user.is_active,
        created_at=user.created_at,
    )


def get_settings_val():
    from app.config import get_settings
    return get_settings().ACCESS_TOKEN_EXPIRE_MINUTES * 60
