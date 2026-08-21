"""JWT auth helpers and FastAPI dependency functions.

Functions:
    hash_password       — bcrypt-hash a plaintext password.
    verify_password     — compare a plaintext password against its hash.
    create_access_token — issue a signed JWT with sub + role claims.
    get_current_user    — FastAPI dependency: validates Bearer JWT and returns User.
    require_role        — dependency factory that gates on one or more UserRole values.
    require_project_owner — dependency that returns the Project after verifying caller
                            ownership; returns 404 (not 403) to avoid leaking project
                            existence to unauthorised callers.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request

from helpers.config import get_settings

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the *hashed* password."""
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------

def create_access_token(
    user_id: str,
    role: str,
    expires_minutes: Optional[int] = None,
) -> str:
    """Sign and return a JWT containing *user_id* (sub) and *role*.

    Args:
        user_id:         UUID string of the authenticated user.
        role:            String role value (e.g. "admin", "member").
        expires_minutes: Override the default expiry from settings.

    Returns:
        A signed JWT string.
    """
    settings = get_settings()
    expiry = expires_minutes if expires_minutes is not None else settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expiry),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

async def get_current_user(request: Request):
    """FastAPI dependency: validates a Bearer JWT and returns the User ORM object.

    Raises:
        HTTPException(401) — missing token, invalid token, or inactive/deleted user.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_header.split(" ", 1)[1]

    try:
        payload = jwt.decode(
            token,
            get_settings().JWT_SECRET_KEY,
            algorithms=["HS256"],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from models import UserModel  # deferred to avoid circular imports
    user_model = await UserModel.create_instance(db_client=request.app.db_client)
    user = await user_model.get_by_id(payload["sub"])

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Attach to request state so middleware (e.g. audit logger) can read it.
    request.state.user = user
    return user


def require_role(*allowed_roles: str):
    """FastAPI dependency factory: verifies the current user has one of *allowed_roles*.

    Usage::

        @router.get("/admin")
        async def admin_only(user=Depends(require_role("admin"))):
            ...

    Raises:
        HTTPException(403) — user's role is not in *allowed_roles*.
    """
    async def checker(user=Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user
    return checker


async def require_project_owner(
    project_id: int,
    request: Request,
    user=Depends(get_current_user),
):
    """FastAPI dependency: verify the authenticated caller owns *project_id* (or is admin).

    **Security note:** returns HTTP 404 (not 403) to avoid leaking whether the
    project exists to callers who do not own it.

    Args:
        project_id: Integer primary key from the URL path parameter.
        request:    Starlette Request (injected automatically by FastAPI).
        user:       Authenticated User ORM object (from ``get_current_user``).

    Returns:
        The ``Project`` ORM object if the caller is authorised.

    Raises:
        HTTPException(401) — unauthenticated (propagated from get_current_user).
        HTTPException(404) — project not found or caller is not the owner.
    """
    from models import ProjectModel  # deferred to avoid circular imports
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_by_id(project_id)

    if not project or (
        project.owner_user_id != user.user_id and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project
