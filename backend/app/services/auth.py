import uuid
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def create_token(user_id: uuid.UUID, role: str, package: str, token_type: str = "access") -> str:
    now = datetime.now(timezone.utc)
    if token_type == "access":
        exp = now + timedelta(minutes=settings.jwt_access_minutes)
    else:
        exp = now + timedelta(days=settings.jwt_refresh_days)

    payload = {
        "sub": str(user_id),
        "role": role,
        "pkg": package,
        "type": token_type,
        "exp": exp,
        "iat": now,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
