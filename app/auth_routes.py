import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, SignupRequest, TokenResponse, UserOut
from app.security import create_access_token, hash_password, verify_password

logger = logging.getLogger("notrieai")
router = APIRouter()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)):
    email = _normalize_email(payload.email)

    # Whoever signs up with this email becomes admin automatically.
    # Comparison is case-insensitive since emails are normalized above.
    admin_email = os.getenv("ADMIN_EMAIL")
    is_admin = bool(admin_email) and email == admin_email.strip().lower()

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        is_admin=is_admin,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        )
    await db.refresh(user)

    token = create_access_token(user_id=user.id, email=user.email, is_admin=user.is_admin)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    email = _normalize_email(payload.email)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Same error for "no such user" and "wrong password" so we don't leak
    # which emails are registered.
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password.",
    )
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise invalid_credentials

    token = create_access_token(user_id=user.id, email=user.email, is_admin=user.is_admin)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))
