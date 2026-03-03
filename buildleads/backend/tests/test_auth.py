"""Tests for authentication — passwords, JWT, registration flow."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from src.auth.passwords import hash_password, verify_password
from src.auth.jwt import create_token, decode_token


class TestPasswords:
    def test_hash_and_verify(self):
        plain = "securePassword123"
        hashed = hash_password(plain)
        assert hashed != plain
        assert verify_password(plain, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)

    def test_different_hashes(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        # bcrypt produces different salts each time
        assert h1 != h2


class TestJWT:
    def test_create_and_decode_access(self):
        uid = uuid.uuid4()
        tid = uuid.uuid4()
        token = create_token(uid, "manager", tid, "access")
        payload = decode_token(token)
        assert payload["sub"] == str(uid)
        assert payload["role"] == "manager"
        assert payload["tid"] == str(tid)
        assert payload["type"] == "access"

    def test_create_and_decode_refresh(self):
        uid = uuid.uuid4()
        tid = uuid.uuid4()
        token = create_token(uid, "salesperson", tid, "refresh")
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_expired_token_raises(self):
        import jwt as pyjwt
        from src.config import settings

        payload = {
            "sub": str(uuid.uuid4()),
            "role": "manager",
            "tid": str(uuid.uuid4()),
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        token = pyjwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_token(token)


class TestPermissions:
    def test_role_hierarchy(self):
        """Verify the role hierarchy constants exist."""
        from src.auth.permissions import require_admin, require_manager, require_salesperson, require_any
        # These are FastAPI dependency callables
        assert callable(require_admin)
        assert callable(require_manager)
        assert callable(require_salesperson)
        assert callable(require_any)
