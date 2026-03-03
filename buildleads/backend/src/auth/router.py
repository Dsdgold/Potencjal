"""Auth endpoints — register, login, refresh, me."""

import uuid

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt import decode_token
from src.auth.passwords import hash_password
from src.auth.permissions import get_current_user
from src.auth.service import authenticate, issue_tokens, register_tenant
from src.database import get_db
from src.users.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ── Schemas ──────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    company_name: str = Field(..., max_length=300)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    first_name: str = Field(..., max_length=150)
    last_name: str = Field(..., max_length=150)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserMeResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: str
    region_id: uuid.UUID | None
    is_active: bool
    email_verified: bool
    last_login: str | None
    created_at: str

    model_config = {"from_attributes": True}


class UpdateMeRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    password: str | None = Field(None, min_length=6, max_length=128)


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        tenant, user = await register_tenant(
            db,
            company_name=body.company_name,
            email=body.email,
            password=body.password,
            first_name=body.first_name,
            last_name=body.last_name,
        )
    except ValueError as e:
        raise HTTPException(409, str(e))
    return issue_tokens(user)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await authenticate(db, body.email, body.password)
    except ValueError as e:
        raise HTTPException(401, str(e))
    return issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(401, "Refresh token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(401, "Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(401, "Not a refresh token")

    user = await db.get(User, uuid.UUID(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")
    return issue_tokens(user)


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "tenant_id": str(user.tenant_id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "region_id": str(user.region_id) if user.region_id else None,
        "is_active": user.is_active,
        "email_verified": user.email_verified,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.put("/me")
async def update_me(
    body: UpdateMeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.first_name is not None:
        user.first_name = body.first_name.strip()
    if body.last_name is not None:
        user.last_name = body.last_name.strip()
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    await db.commit()
    await db.refresh(user)
    return {"status": "ok"}
