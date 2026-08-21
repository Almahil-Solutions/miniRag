"""Projects router — explicit CRUD for projects.

Replaces the old auto-create-on-touch behaviour that was embedded inside
``ProjectModel.get_project_or_create_one``.  Creating a project is now an
intentional, authenticated action rather than a side-effect of the first
upload or index call.
"""
from fastapi import APIRouter, Depends, status, Request
from fastapi.responses import JSONResponse
from helpers.security import get_current_user
from models import ProjectModel
from models.db_schemes import Project
import logging

log = logging.getLogger("uvicorn.error")

projects_router = APIRouter(
    prefix="/api/v1/projects",
    tags=["api_v1", "projects"],
)


@projects_router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(
    request: Request,
    user=Depends(get_current_user),
):
    """Create a new project owned by the authenticated user.

    Returns:
        201 Created with the new project's ``project_id`` and ``project_uuid``.
    """
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)

    new_project = Project(
        # owner_user_id will be populated once P1.2 (owner FK migration) is done.
        # For now we create without it so this route can be exercised immediately.
        # TODO P1.2: set owner_user_id=user.user_id here.
    )

    project = await project_model.create_project(project=new_project)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "project_id": project.project_id,
            "project_uuid": str(project.project_uuid),
        },
    )


@projects_router.get("", status_code=status.HTTP_200_OK)
async def list_projects(
    request: Request,
    page: int = 1,
    page_size: int = 10,
    user=Depends(get_current_user),
):
    """List all projects (paginated).

    Admin users see all projects; regular users will only see their own once
    the ``owner_user_id`` FK (P1.2) is in place.
    """
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    projects, total_pages = await project_model.get_all_projects(page=page, page_size=page_size)

    return JSONResponse(
        content={
            "projects": [
                {
                    "project_id": p.project_id,
                    "project_uuid": str(p.project_uuid),
                }
                for p in projects
            ],
            "total_pages": total_pages,
            "page": page,
        }
    )
