"""JWT token creation and verification — adapted from Potencjal."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt

from src.config import settings


def create_token(
    user_id: uuid.UUID,
    role: str,
    tenant_id: uuid.UUID,
    token_type: str = "access",
) -> str:
    now = datetime.now(timezone.utc)
    if token_type == "access":
        exp = now + timedelta(minutes=settings.jwt_access_minutes)
    else:
        exp = now + timedelta(days=settings.jwt_refresh_days)

    payload = {
        "sub": str(user_id),
        "role": role,
        "tid": str(tenant_id),
        "type": token_type,
        "exp": exp,
        "iat": now,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
