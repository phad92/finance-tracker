from datetime import timedelta
from typing import Optional
import uuid
import jwt
from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user, get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    is_jti_revoked,
    revoke_jti,
    verify_password,
)
from app.models.identity import User
from app.schemas.auth import RefreshTokenRequest, Token, UserRegister, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

REFRESH_COOKIE_NAME = "refresh_token"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    is_prod = settings.ENVIRONMENT.lower() == "production"
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=f"{settings.API_V1_STR}/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=f"{settings.API_V1_STR}/auth",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Register a new user account (honors ALLOW_PUBLIC_REGISTRATION after first owner setup)."""
    count_stmt = select(User).limit(1)
    existing_users = await db.execute(count_stmt)
    is_first_user = existing_users.first() is None

    if not is_first_user and not settings.ALLOW_PUBLIC_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration is disabled for this private deployment.",
        )

    stmt = select(User).where(User.email == user_in.email.lower().strip())
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    new_user = User(
        email=user_in.email.lower().strip(),
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        default_currency=user_in.default_currency.upper().strip(),
        is_active=True,
        is_superuser=is_first_user,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """OAuth2 password login; issues short-lived access token and HttpOnly refresh cookie."""
    email = form_data.username.lower().strip()
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(subject=user.id, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(subject=user.id)

    _set_refresh_cookie(response, refresh_token)

    return Token(
        access_token=access_token,
        refresh_token=None,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    request: Request,
    response: Response,
    body: Optional[RefreshTokenRequest] = Body(default=None),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Rotate refresh token (cookie or body) and issue a new access token + HttpOnly refresh cookie."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME) or (body.refresh_token if body else None)
    if not raw_refresh:
        raise credentials_exception

    try:
        payload = jwt.decode(raw_refresh, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str = payload.get("sub")
        token_type = payload.get("type")
        jti = payload.get("jti")
        if not user_id_str or token_type != "refresh" or is_jti_revoked(jti):
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user or not user.is_active:
        raise credentials_exception

    # Rotate: revoke used refresh token JTI and issue a fresh pair
    revoke_jti(jti)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access = create_access_token(subject=user.id, expires_delta=access_token_expires)
    new_refresh = create_refresh_token(subject=user.id)
    _set_refresh_cookie(response, new_refresh)

    return Token(
        access_token=new_access,
        refresh_token=None,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response) -> None:
    """Revoke the active refresh token cookie and clear the session cookie."""
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_refresh:
        try:
            payload = jwt.decode(raw_refresh, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            revoke_jti(payload.get("jti"))
        except jwt.PyJWTError:
            pass
    _clear_refresh_cookie(response)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> User:
    """Retrieve the currently authenticated user's profile."""
    return current_user
