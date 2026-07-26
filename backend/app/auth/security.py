# app/auth/security.py
"""Password hashing (bcrypt) and JWT issue/verify.

Kept tiny and dependency-light. Secrets come from config; nothing here reaches
the client.
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import get_settings

_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(subject: str) -> str:
    """Issue a JWT whose `sub` is the user id."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode/verify a JWT. Raises jwt.PyJWTError on invalid/expired tokens."""
    return jwt.decode(token, get_settings().jwt_secret, algorithms=[_ALGORITHM])
