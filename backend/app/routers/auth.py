import secrets
import uuid
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import PACKAGE_LIMITS, settings
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import User
from app.schemas import (
    AdminUserUpdate,
    LoginRequest,
    PackageInfo,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
    UserUpdate,
)
from app.services.auth import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.services.email import send_activation_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Email already registered")

    activation_token = secrets.token_urlsafe(48)

    user = User(
        email=body.email.lower().strip(),
        password_hash=hash_password(body.password),
        full_name=body.full_name.strip(),
        package=body.package,
        is_email_verified=False,
        activation_token=activation_token,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Send activation email (non-blocking – if SMTP fails, user can still resend)
    send_activation_email(user.email, user.full_name, activation_token)

    return user


@router.get("/activate/{token}")
async def activate_account(token: str, db: AsyncSession = Depends(get_db)):
    """Activate user account via email link."""
    result = await db.execute(select(User).where(User.activation_token == token))
    user = result.scalar_one_or_none()

    if not user:
        return HTMLResponse(_activation_page("Nieprawidlowy link aktywacyjny.", False), status_code=400)

    if user.is_email_verified:
        return HTMLResponse(_activation_page("Konto juz jest aktywne. Mozesz sie zalogowac.", True))

    user.is_email_verified = True
    user.activation_token = None
    await db.commit()

    return HTMLResponse(_activation_page("Konto zostalo aktywowane! Mozesz sie teraz zalogowac.", True))


@router.post("/resend-activation")
async def resend_activation(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Resend activation email. Requires email + password to prevent abuse."""
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")

    if user.is_email_verified:
        return {"message": "Konto juz jest aktywne."}

    # Generate new token
    token = secrets.token_urlsafe(48)
    user.activation_token = token
    await db.commit()

    sent = send_activation_email(user.email, user.full_name, token)
    if sent:
        return {"message": "Email aktywacyjny wyslany ponownie."}
    else:
        return {"message": "SMTP nie skonfigurowany. Skontaktuj sie z administratorem.", "activation_token": token}


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(403, "Account deactivated")
    if not user.is_email_verified:
        raise HTTPException(403, "EMAIL_NOT_VERIFIED")

    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    return TokenResponse(
        access_token=create_token(user.id, user.role, user.package, "access"),
        refresh_token=create_token(user.id, user.role, user.package, "refresh"),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(401, "Not a refresh token")

    user = await db.get(User, uuid.UUID(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")

    return TokenResponse(
        access_token=create_token(user.id, user.role, user.package, "access"),
        refresh_token=create_token(user.id, user.role, user.package, "refresh"),
    )


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserOut)
async def update_me(
    body: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.full_name is not None:
        user.full_name = body.full_name.strip()
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/packages", response_model=list[PackageInfo])
async def list_packages():
    return [
        PackageInfo(key=k, **{kk: vv for kk, vv in v.items()})
        for k, v in PACKAGE_LIMITS.items()
    ]


# ── Admin endpoints ───────────────────────────────────────────────────

@router.get("/admin/users", response_model=list[UserOut])
async def admin_list_users(
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())


@router.put("/admin/users/{user_id}", response_model=UserOut)
async def admin_update_user(
    user_id: uuid.UUID,
    body: AdminUserUpdate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if body.role is not None:
        user.role = body.role
    if body.package is not None:
        user.package = body.package
    if body.is_active is not None:
        user.is_active = body.is_active
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/admin/users/{user_id}", status_code=204)
async def admin_delete_user(
    user_id: uuid.UUID,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    if user_id == admin.id:
        raise HTTPException(400, "Cannot delete yourself")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    await db.delete(user)
    await db.commit()


def _activation_page(message: str, success: bool) -> str:
    color = "#145efc" if success else "#ef4444"
    icon = "&#10003;" if success else "&#10007;"
    return f"""\
<!DOCTYPE html>
<html lang="pl">
<head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Potencjal – Aktywacja konta</title>
<style>
  body{{margin:0;padding:0;background:#0a1628;font-family:system-ui,sans-serif;color:#e5e7eb;
        display:flex;align-items:center;justify-content:center;min-height:100vh}}
  .box{{background:#152238;border:1px solid #1e3354;border-radius:14px;padding:40px;
        max-width:440px;width:90%;text-align:center}}
  .icon{{font-size:48px;color:{color};margin-bottom:16px}}
  h1{{font-size:20px;font-weight:800;margin:0 0 12px}}
  p{{color:#bfbab5;font-size:14px;line-height:1.6;margin:0 0 24px}}
  a{{display:inline-block;background:linear-gradient(180deg,#145efc,#0d4fd4);color:#fff;
     font-size:14px;font-weight:700;padding:10px 28px;border-radius:10px;text-decoration:none}}
</style></head>
<body><div class="box">
  <div class="icon">{icon}</div>
  <h1>{"Aktywacja udana!" if success else "Blad aktywacji"}</h1>
  <p>{message}</p>
  <a href="/">Przejdz do platformy</a>
</div></body></html>"""
