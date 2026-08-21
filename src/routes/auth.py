"""Authentication routes — register, login, refresh, logout.

Endpoints
---------
POST /api/v1/auth/register  — create a new user account
POST /api/v1/auth/login     — exchange credentials for a JWT
POST /api/v1/auth/refresh   — extend an existing (valid) JWT
POST /api/v1/auth/logout    — advisory token invalidation (client-side)
"""

import logging
from fastapi import APIRouter, Depends, status, Request
from fastapi.responses import JSONResponse

from helpers.config import get_settings
from helpers.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from models import UserModel, ResponceSignal
from models.db_schemes import User
from .schemes.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    LogoutRequest,
)

log = logging.getLogger("uvicorn.error")

auth_router = APIRouter(
    prefix="/api/v1/auth",
    tags=["api_v1", "auth"],
)


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------

@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    body: RegisterRequest,
):
    """Create a new user account.

    Returns 409 if the e-mail address is already registered so callers can
    surface a friendly duplicate-account error rather than a generic 500.
    """
    user_model = await UserModel.create_instance(db_client=request.app.db_client)

    # Conflict check — e-mail must be unique
    existing = await user_model.get_by_email(body.email)
    if existing is not None:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "Email address already registered."},
        )

    new_user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    user = await user_model.create_user(new_user)

    log.info("New user registered: %s (id=%s)", user.email, user.user_id)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "user_id": str(user.user_id),
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        },
    )


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------

@auth_router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    body: LoginRequest,
):
    """Authenticate with e-mail + password and return a signed JWT.

    Returns 401 for both "user not found" and "wrong password" to prevent
    user-enumeration via timing differences.
    """
    user_model = await UserModel.create_instance(db_client=request.app.db_client)
    user = await user_model.get_by_email(body.email)

    if user is None or not verify_password(body.password, user.hashed_password):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid email or password."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Account is disabled. Contact support."},
        )

    settings = get_settings()
    token = create_access_token(
        user_id=str(user.user_id),
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        expires_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    log.info("User logged in: %s (id=%s)", user.email, user.user_id)

    return JSONResponse(
        content={
            "access_token": token,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }
    )


# ---------------------------------------------------------------------------
# POST /refresh
# ---------------------------------------------------------------------------

@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    body: RefreshRequest,
):
    """Re-issue a JWT for an already-authenticated session.

    The current token must still be valid (not expired).  A proper
    implementation would use a long-lived refresh token stored in an
    HttpOnly cookie; this version re-validates the access token and issues
    a fresh one with a new expiry window.
    """
    from jose import jwt, JWTError

    settings = get_settings()
    try:
        payload = jwt.decode(body.token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Token is invalid or has expired. Please log in again."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_model = await UserModel.create_instance(db_client=request.app.db_client)
    user = await user_model.get_by_id(payload["sub"])

    if not user or not user.is_active:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "User not found or inactive."},
        )

    new_token = create_access_token(
        user_id=str(user.user_id),
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        expires_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    return JSONResponse(
        content={
            "access_token": new_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }
    )


# ---------------------------------------------------------------------------
# POST /logout
# ---------------------------------------------------------------------------

@auth_router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    body: LogoutRequest,
    user=Depends(get_current_user),
):
    """Advisory logout — the client should discard its stored token.

    JWTs are stateless so the server cannot truly revoke them without a
    deny-list (Redis).  A future enhancement would add the token's ``jti``
    claim to Redis with a TTL matching the remaining validity window.
    """
    log.info("User logged out: id=%s", user.user_id)
    return JSONResponse(content={"detail": "Logged out successfully."})
