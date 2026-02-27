"""Simple credential encryption using Fernet symmetric encryption."""

from cryptography.fernet import Fernet
from app.config import get_settings
import json


def _get_fernet() -> Fernet:
    key = get_settings().CREDENTIALS_ENCRYPTION_KEY
    if not key:
        key = Fernet.generate_key().decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_credentials(data: dict) -> str:
    f = _get_fernet()
    return f.encrypt(json.dumps(data).encode()).decode()


def decrypt_credentials(encrypted: str) -> dict:
    f = _get_fernet()
    return json.loads(f.decrypt(encrypted.encode()).decode())
