"""Admin-only routes — user management and query-log inspection.

All endpoints in this router require the ``admin`` role.  A non-admin user
receives HTTP 403 from the ``require_role("admin")`` dependency before the
handler body is executed.

Endpoints
---------
GET   /api/v1/admin/users              — paginated list of all users
PATCH /api/v1/admin/users/{user_id}    — update role / plan / active status
GET   /api/v1/admin/query-logs         — paginated list of all query logs
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from helpers.security import require_role
from models import UserModel, QueryLogModel

log = logging.getLogger("uvicorn.error")

admin_router = APIRouter(
    prefix="/api/v1/admin",
    tags=["api_v1", "admin"],
    # Every route in this router requires the "admin" role.
    dependencies=[Depends(require_role("admin"))],
)


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class AdminUpdateUserRequest(BaseModel):
    """Fields an admin is allowed to modify on a user account."""
    role: Optional[str] = None       # e.g. "admin", "member", "viewer"
    plan: Optional[str] = None       # e.g. "free", "pro", "enterprise"
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# GET /users
# ---------------------------------------------------------------------------

@admin_router.get("/users", status_code=status.HTTP_200_OK)
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Return a paginated list of all registered users.

    Accessible to admin accounts only.
    """
    user_model = await UserModel.create_instance(db_client=request.app.db_client)
    users, total_pages = await user_model.get_all_users(page=page, page_size=page_size)

    return JSONResponse(
        content={
            "users": [
                {
                    "user_id": str(u.user_id),
                    "email": u.email,
                    "full_name": u.full_name,
                    "role": u.role.value if hasattr(u.role, "value") else str(u.role),
                    "plan": u.plan,
                    "is_active": u.is_active,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                }
                for u in users
            ],
            "page": page,
            "total_pages": total_pages,
        }
    )


# ---------------------------------------------------------------------------
# PATCH /users/{user_id}
# ---------------------------------------------------------------------------

@admin_router.patch("/users/{user_id}", status_code=status.HTTP_200_OK)
async def admin_update_user(
    request: Request,
    user_id: UUID,
    body: AdminUpdateUserRequest,
):
    """Modify a user's role, plan, or active status.

    Returns 404 if the user does not exist.
    """
    user_model = await UserModel.create_instance(db_client=request.app.db_client)
    user = await user_model.get_by_id(str(user_id))

    if user is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "User not found."},
        )

    if body.role is not None:
        # Validate against the UserRole enum at the ORM level — the DB will
        # reject invalid values, but validate here for a cleaner error message.
        from models.db_schemes.minirag.schemes.user import UserRole
        try:
            user.role = UserRole(body.role)
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": f"Invalid role '{body.role}'. Valid values: {[r.value for r in UserRole]}"},
            )

    if body.plan is not None:
        user.plan = body.plan

    if body.is_active is not None:
        user.is_active = body.is_active

    updated = await user_model.update_user(user)
    log.info(
        "Admin updated user: user_id=%s role=%s plan=%s is_active=%s",
        user_id, body.role, body.plan, body.is_active,
    )

    return JSONResponse(
        content={
            "user_id": str(updated.user_id),
            "email": updated.email,
            "role": updated.role.value if hasattr(updated.role, "value") else str(updated.role),
            "plan": updated.plan,
            "is_active": updated.is_active,
        }
    )


# ---------------------------------------------------------------------------
# GET /query-logs
# ---------------------------------------------------------------------------

@admin_router.get("/query-logs", status_code=status.HTTP_200_OK)
async def list_query_logs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Return a paginated list of all query-log entries (admin view).

    Includes all users' activity, newest-first.
    """
    log_model = await QueryLogModel.create_instance(db_client=request.app.db_client)
    logs, total_pages = await log_model.get_all_logs(page=page, page_size=page_size)

    return JSONResponse(
        content={
            "logs": [
                {
                    "log_id": str(entry.log_id),
                    "user_id": str(entry.user_id),
                    "project_id": entry.project_id,
                    "endpoint": entry.endpoint,
                    "query_text": entry.query_text,
                    "result_summary": entry.result_summary,
                    "status": entry.status,
                    "latency_ms": entry.latency_ms,
                    "ip_address": entry.ip_address,
                    "request_id": entry.request_id,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None,
                }
                for entry in logs
            ],
            "page": page,
            "total_pages": total_pages,
        }
    )
