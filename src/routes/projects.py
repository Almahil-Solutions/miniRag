from uuid import UUID
from fastapi import APIRouter, Depends, status, Request
from fastapi.responses import JSONResponse
from helpers.security import get_current_user, require_project_owner
from models import ProjectModel, AssetModel, ChunkModel
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
        owner_user_id=user.user_id,
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
    """List projects (paginated).

    Admin users see all projects; regular users only see their own.
    """
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    owner_filter = None if getattr(user, "role", None) == "admin" else user.user_id
    projects, total_pages = await project_model.get_all_projects(
        page=page,
        page_size=page_size,
        owner_user_id=owner_filter
    )

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


@projects_router.delete("/{project_uuid}", status_code=status.HTTP_200_OK)
async def delete_project(
    request: Request,
    project_uuid: UUID,
    user=Depends(get_current_user),
    project=Depends(require_project_owner),
):
    """Soft-delete a project, its assets and data chunks, and purge its vector collection."""
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)

    # Soft delete chunks & assets
    await chunk_model.soft_delete_chunks_by_project_id(project.project_id)
    assets = await asset_model.get_all_project_assets(project.project_id, only_latest=False)
    for asset in assets:
        await asset_model.soft_delete_asset_by_uuid(asset.asset_uuid, project.project_id)

    # Soft delete project record
    deleted = await project_model.soft_delete_project_by_uuid(project_uuid)
    if not deleted:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": "project_not_found"}
        )

    # Purge VectorDB collection for this project
    try:
        if hasattr(request.app, "vectordb_client") and request.app.vectordb_client is not None:
            collection_name = f"collection_{request.app.vectordb_client.default_vector_size}_{project.project_id}".strip()
            await request.app.vectordb_client.delete_collection(collection_name=collection_name)
    except Exception as exc:
        log.warning("delete_project: error deleting vector collection: %s", exc)

    return JSONResponse(
        content={
            "signal": "success",
            "message": "Project soft-deleted successfully",
            "project_uuid": str(project_uuid),
        }
    )
