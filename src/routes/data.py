"""Data routes — file upload, processing, and combined workflow.

Path parameters use ``project_uuid`` (UUID) instead of the internal integer
``project_id`` so that sequential IDs are never exposed in public URLs (P1.7).
The ``require_project_owner`` dependency resolves the UUID to the full Project
ORM object before the handler body runs.

Rate limiting is applied to upload and process endpoints via
``rate_limit_dependency`` (P2.1).
"""

from uuid import UUID
import os
import aiofiles
import logging

from fastapi import APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse

from helpers import get_settings, Settings
from helpers.security import get_current_user, require_project_owner
from utils.rate_limiter import rate_limit_dependency
from controllers import DataController, ProjectController, ProcessController, NLPController
from models import ResponceSignal, ProjectModel, ChunkModel, DataChunk, AssetModel, Asset, AssetTypeEnum
from .schemes.data import ProcessRequest
from tasks.file_processing import process_project_files
from tasks.process_workflow import process_and_push_workflow


logger = logging.getLogger("uvicorn.error")


data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"]
)


# ---------------------------------------------------------------------------
# POST /upload/{project_uuid}   (rate-limited)
# ---------------------------------------------------------------------------

@data_router.post("/upload/{project_uuid}")
async def upload_data(
    request: Request,
    project_uuid: UUID,
    file: UploadFile,
    app_settings: Settings = Depends(get_settings),
    user=Depends(get_current_user),
    project=Depends(require_project_owner),
    _rl=Depends(rate_limit_dependency),
):
    """Upload a file into the project's storage area.

    Validates the file extension, streams it to disk, and persists an Asset
    record.  Rate-limited per plan (P2.1).
    """
    data_controller = DataController()
    # validate file extension
    is_valid, result_signal = data_controller.validate_upload_file(file=file)
    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "result_signal": result_signal
            }
        )
    project_dir_path = ProjectController().get_project_path(project_id=project.project_id)
    file_path, file_name = data_controller.generate_unique_file_name(
        original_file_name=file.filename,
        project_id=project.project_id,
    )

    # "wb" binary write
    try:
        async with aiofiles.open(file_path, "wb") as out_file:
            while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
                await out_file.write(chunk)
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "result_signal": ResponceSignal.FILE_UPLOADED_FAILED.value
            }
        )

    # store asset information in the database
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    asset_resource = Asset(
        asset_project_id=project.project_id,
        asset_type=AssetTypeEnum.FILE.value,
        asset_name=file_name,
        asset_size=os.path.getsize(file_path),
    )

    asset_record = await asset_model.create_asset(asset=asset_resource)
    return JSONResponse(
        content={
            "result_signal": ResponceSignal.FILE_UPLOADED_SUCCESSFULLY.value,
            "asset_name": file_name,
            "asset_id": str(asset_record.asset_id),
            "asset_uuid": str(asset_record.asset_uuid),
        }
    )


# ---------------------------------------------------------------------------
# POST /process/{project_uuid}   (rate-limited)
# ---------------------------------------------------------------------------

@data_router.post("/process/{project_uuid}")
async def process_endpoint(
    request: Request,
    project_uuid: UUID,
    process_request: ProcessRequest,
    user=Depends(get_current_user),
    project=Depends(require_project_owner),
    _rl=Depends(rate_limit_dependency),
):
    """Trigger a Celery task to chunk and process an uploaded file."""
    do_reset = process_request.do_reset
    chunk_size = process_request.chunk_size
    chunk_overlap = process_request.chunk_overlap

    task = process_project_files.delay(
        project_id=project.project_id,
        file_name=process_request.file_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        do_reset=do_reset
    )
    return JSONResponse(
        content={
            "result_signal": ResponceSignal.FILE_PROCESSING_SUCCESSFULL.value,
            "task_id": task.id
        }
    )


# ---------------------------------------------------------------------------
# POST /process-and-push/{project_uuid}   (rate-limited)
# ---------------------------------------------------------------------------

@data_router.post("/process-and-push/{project_uuid}")
async def process_and_push_endpoint(
    request: Request,
    project_uuid: UUID,
    process_request: ProcessRequest,
    user=Depends(get_current_user),
    project=Depends(require_project_owner),
    _rl=Depends(rate_limit_dependency),
):
    """Trigger the combined process → index Celery workflow."""
    do_reset = process_request.do_reset
    chunk_size = process_request.chunk_size
    chunk_overlap = process_request.chunk_overlap

    workflow_task = process_and_push_workflow.delay(
        project_id=project.project_id,
        file_name=process_request.file_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        do_reset=do_reset
    )
    return JSONResponse(
        content={
            "result_signal": ResponceSignal.PROCEDD_AND_PUSH_WORKFLOW_READY.value,
            "workflow_id": workflow_task.id
        }
    )
