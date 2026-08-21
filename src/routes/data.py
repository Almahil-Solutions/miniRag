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

    # "wb" binary write with streaming size cap
    try:
        total_bytes = 0
        max_bytes = app_settings.FILE_MAX_SIZE * data_controller.size_scale
        async with aiofiles.open(file_path, "wb") as out_file:
            while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    await out_file.close()
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={
                            "result_signal": ResponceSignal.FILE_SIZE_EXCEEDED.value
                        }
                    )
                await out_file.write(chunk)
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "result_signal": ResponceSignal.FILE_UPLOADED_FAILED.value
            }
        )

    # Scan file for malware (P4.5)
    is_clean, scan_meta = data_controller.scan_file_for_malware(file_path=file_path)
    if not is_clean:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "result_signal": "file_malware_detected",
                "scan_details": scan_meta,
            }
        )

    # store asset information in the database
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    asset_resource = Asset(
        asset_project_id=project.project_id,
        asset_type=AssetTypeEnum.FILE.value,
        asset_name=file_name,
        asset_size=os.path.getsize(file_path),
        asset_config=scan_meta,
    )

    asset_record = await asset_model.create_asset(asset=asset_resource)
    return JSONResponse(
        content={
            "result_signal": ResponceSignal.FILE_UPLOADED_SUCCESSFULLY.value,
            "asset_name": file_name,
            "asset_id": str(asset_record.asset_id),
            "asset_uuid": str(asset_record.asset_uuid),
            "asset_version": asset_record.asset_version,
            "is_latest": asset_record.is_latest,
        }
    )


# ---------------------------------------------------------------------------
# GET /{project_uuid}/documents   (P4.3 — owner-scoped paginated listing)
# ---------------------------------------------------------------------------

@data_router.get("/{project_uuid}/documents")
async def list_project_documents(
    request: Request,
    project_uuid: UUID,
    page: int = 1,
    page_size: int = 10,
    asset_type: str = None,
    only_latest: bool = True,
    user=Depends(get_current_user),
    project=Depends(require_project_owner),
):
    """Retrieve a paginated list of documents (assets) for the project."""
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    assets, total_pages, total_records = await asset_model.get_project_assets_paginated(
        asset_project_id=project.project_id,
        page=page,
        page_size=page_size,
        asset_type=asset_type,
        only_latest=only_latest,
    )

    return JSONResponse(
        content={
            "documents": [
                {
                    "asset_id": a.asset_id,
                    "asset_uuid": str(a.asset_uuid),
                    "asset_name": a.asset_name,
                    "asset_type": a.asset_type,
                    "asset_size": a.asset_size,
                    "asset_version": a.asset_version,
                    "is_latest": a.is_latest,
                    "asset_config": a.asset_config,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in assets
            ],
            "total_documents": total_records,
            "total_pages": total_pages,
            "page": page,
        }
    )


# ---------------------------------------------------------------------------
# GET /{project_uuid}/documents/{asset_uuid}   (P4.3 — document metadata & stats)
# ---------------------------------------------------------------------------

@data_router.get("/{project_uuid}/documents/{asset_uuid}")
async def get_document_details(
    request: Request,
    project_uuid: UUID,
    asset_uuid: UUID,
    user=Depends(get_current_user),
    project=Depends(require_project_owner),
):
    """Retrieve metadata, version details, and chunk statistics for a document."""
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)

    asset = await asset_model.get_asset_by_uuid(
        asset_uuid=asset_uuid,
        asset_project_id=project.project_id,
    )
    if not asset:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": "document_not_found"}
        )

    chunk_count = await chunk_model.count_asset_chunks(asset_id=asset.asset_id)
    versions = await asset_model.get_asset_versions(
        asset_project_id=project.project_id,
        asset_name=asset.asset_name
    )

    return JSONResponse(
        content={
            "asset_id": asset.asset_id,
            "asset_uuid": str(asset.asset_uuid),
            "asset_name": asset.asset_name,
            "asset_type": asset.asset_type,
            "asset_size": asset.asset_size,
            "asset_version": asset.asset_version,
            "is_latest": asset.is_latest,
            "total_chunks": chunk_count,
            "asset_config": asset.asset_config,
            "created_at": asset.created_at.isoformat() if asset.created_at else None,
            "available_versions": [v.asset_version for v in versions],
        }
    )


# ---------------------------------------------------------------------------
# DELETE /{project_uuid}/documents/{asset_uuid}   (P4.1, P4.3 — soft delete + purge vectors)
# ---------------------------------------------------------------------------

@data_router.delete("/{project_uuid}/documents/{asset_uuid}")
async def delete_document(
    request: Request,
    project_uuid: UUID,
    asset_uuid: UUID,
    user=Depends(get_current_user),
    project=Depends(require_project_owner),
):
    """Soft delete a document and its chunks, and purge its vectors from VectorDB."""
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)

    asset = await asset_model.get_asset_by_uuid(
        asset_uuid=asset_uuid,
        asset_project_id=project.project_id,
    )
    if not asset:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": "document_not_found"}
        )

    # Soft delete chunks
    deleted_chunks_count = await chunk_model.soft_delete_chunks_by_asset_id(asset_id=asset.asset_id)

    # Purge vectors from VectorDB for this asset
    try:
        if hasattr(request.app, "vectordb_client") and request.app.vectordb_client is not None:
            collection_name = f"collection_{request.app.vectordb_client.default_vector_size}_{project.project_id}".strip()
            await request.app.vectordb_client.delete_by_asset_id(
                collection_name=collection_name,
                asset_id=asset.asset_id,
            )
    except Exception as exc:
        logger.warning(f"Failed to delete vectors for asset {asset.asset_id}: {exc}")

    # Soft delete asset record
    await asset_model.soft_delete_asset_by_uuid(
        asset_uuid=asset_uuid,
        asset_project_id=project.project_id,
    )

    return JSONResponse(
        content={
            "signal": "success",
            "message": "Document soft-deleted and vectors purged",
            "asset_uuid": str(asset_uuid),
            "chunks_purged": deleted_chunks_count,
        }
    )


# ---------------------------------------------------------------------------
# POST /{project_uuid}/documents/{asset_uuid}/reprocess   (P4.3 — document reprocess)
# ---------------------------------------------------------------------------

@data_router.post("/{project_uuid}/documents/{asset_uuid}/reprocess")
async def reprocess_document(
    request: Request,
    project_uuid: UUID,
    asset_uuid: UUID,
    process_request: ProcessRequest,
    user=Depends(get_current_user),
    project=Depends(require_project_owner),
    _rl=Depends(rate_limit_dependency),
):
    """Trigger reprocessing for a specific document asset."""
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)

    asset = await asset_model.get_asset_by_uuid(
        asset_uuid=asset_uuid,
        asset_project_id=project.project_id,
    )
    if not asset:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": "document_not_found"}
        )

    # Soft delete old chunks and purge old vectors for this asset
    await chunk_model.soft_delete_chunks_by_asset_id(asset_id=asset.asset_id)
    try:
        if hasattr(request.app, "vectordb_client") and request.app.vectordb_client is not None:
            collection_name = f"collection_{request.app.vectordb_client.default_vector_size}_{project.project_id}".strip()
            await request.app.vectordb_client.delete_by_asset_id(
                collection_name=collection_name,
                asset_id=asset.asset_id,
            )
    except Exception as exc:
        logger.warning(f"Reprocess vector purge warning: {exc}")

    # Dispatch workflow task for this specific file
    task = process_and_push_workflow.delay(
        project_id=project.project_id,
        file_name=asset.asset_name,
        chunk_size=process_request.chunk_size,
        chunk_overlap=process_request.chunk_overlap,
        do_reset=process_request.do_reset,
    )

    return JSONResponse(
        content={
            "result_signal": ResponceSignal.PROCEDD_AND_PUSH_WORKFLOW_READY.value,
            "task_id": task.id,
            "asset_uuid": str(asset_uuid),
            "asset_name": asset.asset_name,
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
