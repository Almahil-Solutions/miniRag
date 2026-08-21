"""User self-service routes and API-key management.

Endpoints
---------
GET    /api/v1/users/me                   — view own profile
PATCH  /api/v1/users/me                   — update own profile
POST   /api/v1/users/me/api-keys          — generate a new API key
DELETE /api/v1/users/me/api-keys/{key_id} — revoke an API key
"""

import logging
import secrets
import hashlib
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from helpers.security import get_current_user
from models import UserModel, ApiKeyModel
from models.db_schemes import ApiKey

log = logging.getLogger("uvicorn.error")

users_router = APIRouter(
    prefix="/api/v1/users",
    tags=["api_v1", "users"],
)


# ---------------------------------------------------------------------------
# Request schemas (local — simple enough not to warrant a separate file)
# ---------------------------------------------------------------------------

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = Field(None, max_length=200)


class CreateApiKeyRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="Human-readable label")


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------

@users_router.get("/me", status_code=status.HTTP_200_OK)
async def get_my_profile(
    user=Depends(get_current_user),
):
    """Return the authenticated user's public profile."""
    return JSONResponse(
        content={
            "user_id": str(user.user_id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "plan": user.plan,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
    )


# ---------------------------------------------------------------------------
# PATCH /me
# ---------------------------------------------------------------------------

@users_router.patch("/me", status_code=status.HTTP_200_OK)
async def update_my_profile(
    request: Request,
    body: UpdateProfileRequest,
    user=Depends(get_current_user),
):
    """Update the authenticated user's mutable profile fields.

    Only ``full_name`` is user-editable at this tier.  Role and plan changes
    are admin-only (see ``admin.py``).
    """
    if body.full_name is not None:
        user.full_name = body.full_name

    user_model = await UserModel.create_instance(db_client=request.app.db_client)
    updated = await user_model.update_user(user)

    return JSONResponse(
        content={
            "user_id": str(updated.user_id),
            "email": updated.email,
            "full_name": updated.full_name,
        }
    )


# ---------------------------------------------------------------------------
# POST /me/api-keys
# ---------------------------------------------------------------------------

@users_router.post("/me/api-keys", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: Request,
    body: CreateApiKeyRequest,
    user=Depends(get_current_user),
):
    """Generate a new API key for the authenticated user.

    The raw key is returned **once** — it is hashed (SHA-256) before storage
    and cannot be recovered later.  The caller must copy it immediately.
    """
    raw_key = secrets.token_hex(32)  # 256 bits of entropy
    hashed = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key_model = await ApiKeyModel.create_instance(db_client=request.app.db_client)
    new_key = ApiKey(
        user_id=user.user_id,
        hashed_key=hashed,
        name=body.name,
    )
    record = await api_key_model.create_key(new_key)

    log.info("API key created: key_id=%s user_id=%s name=%s", record.key_id, user.user_id, body.name)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "key_id": str(record.key_id),
            "name": record.name,
            # Raw key is returned ONCE — store it safely.
            "api_key": raw_key,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        },
    )


# ---------------------------------------------------------------------------
# DELETE /me/api-keys/{key_id}
# ---------------------------------------------------------------------------

@users_router.delete(
    "/me/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_api_key(
    request: Request,
    key_id: UUID,
    user=Depends(get_current_user),
):
    """Revoke (soft-delete) one of the authenticated user's API keys.

    Uses the user_id + key_id pair in the WHERE clause so a user can never
    revoke another user's key even if they know the UUID.
    """
    api_key_model = await ApiKeyModel.create_instance(db_client=request.app.db_client)
    await api_key_model.revoke_key(key_id=str(key_id), user_id=str(user.user_id))

    log.info("API key revoked: key_id=%s user_id=%s", key_id, user.user_id)
