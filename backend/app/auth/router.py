# app/auth/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import security
from app.auth.deps import get_current_user
from app.auth.schemas import LoginRequest, SignupRequest, TokenResponse, UserOut
from app.db import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    email = req.email.lower()
    if db.query(User).filter(User.email == email).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=email, password_hash=security.hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=security.create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    email = req.email.lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None or not security.verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return TokenResponse(access_token=security.create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut(id=current_user.id, email=current_user.email)
