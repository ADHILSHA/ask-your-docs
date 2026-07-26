# app/auth/deps.py
"""Auth dependency: resolve the Bearer token to the current user."""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.db import get_db
from app.models.user import User

# auto_error=False so a missing header yields our own 401 (not the default 403).
_bearer = HTTPBearer(auto_error=False)

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _UNAUTHENTICATED
    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise _UNAUTHENTICATED

    user_id = payload.get("sub")
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise _UNAUTHENTICATED
    return user
