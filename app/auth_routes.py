import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.email_client import EmailNotConfigured, send_password_reset_email
from app.models import PasswordResetToken, User
from app.rate_limit import limiter
from app.schemas import (
    ForgotPasswordRequest,
    GoogleAuthRequest,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    UserOut,
)
from app.security import create_access_token, hash_password, verify_password
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

RESET_TOKEN_TTL_MINUTES = 30
# Generic response for forgot-password, always returned regardless of
# whether the email exists - so this endpoint can't be used to check
# which emails have an account.
_FORGOT_PASSWORD_GENERIC_MESSAGE = (
    "If an account exists for that email, we've sent a password reset link."
)

logger = logging.getLogger("notrieai")
router = APIRouter()

# A single reusable Request object for Google's token-verification calls,
# so the underlying HTTP client (and Google's cached signing certs) is
# reused across requests instead of being rebuilt every time.
_google_request = google_requests.Request()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def signup(request: Request, payload: SignupRequest, db: AsyncSession = Depends(get_db)):
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
@limiter.limit("8/minute;20/hour")
async def login(request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)):
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


@router.post("/google", response_model=TokenResponse)
@limiter.limit("10/minute;30/hour")
async def google_auth(
    request: Request, payload: GoogleAuthRequest, db: AsyncSession = Depends(get_db)
):
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured.",
        )

    # verify_oauth2_token checks the signature against Google's public
    # keys, the audience (must match our client_id), issuer, and
    # expiry - this is what actually proves the token is real and
    # belongs to this app, not just decoding it.
    try:
        claims = google_id_token.verify_oauth2_token(payload.id_token, _google_request, client_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google sign-in. Please try again.",
        )

    if not claims.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your Google account's email isn't verified.",
        )

    google_sub = claims["sub"]
    email = _normalize_email(claims["email"])

    result = await db.execute(select(User).where(User.google_id == google_sub))
    user = result.scalar_one_or_none()

    if user is None:
        # Not linked to Google yet - if an account with this email
        # already exists (e.g. they originally signed up with a
        # password), link Google to it instead of creating a duplicate.
        # This is safe because Google has already verified they own
        # this email address.
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            admin_email = os.getenv("ADMIN_EMAIL")
            is_admin = bool(admin_email) and email == admin_email.strip().lower()
            user = User(email=email, hashed_password=None, google_id=google_sub, is_admin=is_admin)
            db.add(user)
        else:
            user.google_id = google_sub
        await db.commit()
        await db.refresh(user)

    token = create_access_token(user_id=user.id, email=user.email, is_admin=user.is_admin)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))
@limiter.limit("3/hour")
async def forgot_password(
    request: Request, payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
):
    email = _normalize_email(payload.email)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Always return the same generic message whether or not the account
    # exists, and only do the real work when it does - this endpoint must
    # not reveal which emails are registered.
    if user is not None:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )
        await db.commit()

        frontend_url = os.getenv("FRONTEND_URL", "https://rotryai.vercel.app").rstrip("/")
        reset_link = f"{frontend_url}/reset-password?token={raw_token}"
        try:
            await send_password_reset_email(user.email, reset_link)
        except EmailNotConfigured:
            logger.error("Password reset requested but SMTP is not configured.")
        except RuntimeError:
            logger.error("Password reset email failed to send for %s", user.email)

    return MessageResponse(message=_FORGOT_PASSWORD_GENERIC_MESSAGE)


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("5/hour")
async def reset_password(
    request: Request, payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
):
    token_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    reset_token = result.scalar_one_or_none()

    invalid_link = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="This reset link is invalid or has expired. Please request a new one.",
    )
    now = datetime.now(timezone.utc)
    if (
        reset_token is None
        or reset_token.used_at is not None
        or reset_token.expires_at < now
    ):
        raise invalid_link

    result = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise invalid_link

    user.hashed_password = hash_password(payload.new_password)
    reset_token.used_at = now
    await db.commit()

    return MessageResponse(message="Your password has been reset. You can now log in.")
