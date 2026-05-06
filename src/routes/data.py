from fastapi import APIRouter, FastAPI, Depends, UploadFile, File, status, Request
from fastapi.responses import JSONResponse
from helpers import get_settings, Settings
from controllers import DataController, ProjectController, ProcessController, NLPController
from models import ResponceSignal, ProjectModel, ChunkModel, DataChunk, AssetModel, Asset, AssetTypeEnum
import os
import aiofiles
import logging
from .schemes.data import ProcessRequest



logger = logging.getLogger("uvicorn.error")


data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"]
)


@data_router.post("/upload/{project_id}")
async def upload_data(request: Request, project_id: int, file: UploadFile,
                        app_settings: Settings = Depends(get_settings)):

    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    
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
    project_dir_path = ProjectController().get_project_path(project_id=project_id)
    file_path, file_id = data_controller.generate_unique_file_name(original_file_name=file.filename, project_id=project_id)

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
        asset_name=file_id,
        asset_size=os.path.getsize(file_path),
    )

    asset_record = await asset_model.create_asset(asset=asset_resource)
    return JSONResponse(
        content={
            "result_signal": ResponceSignal.FILE_UPLOADED_SUCCESSFULLY.value,
            "file_id": file_id,
            "asset_id": str(asset_record.asset_id)
        }
    )

@data_router.post("/process/{project_id}")
async def process_endpoint(request: Request, project_id: int, process_request: ProcessRequest):

    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    chunk_size=process_request.chunk_size
    chunk_overlap=process_request.chunk_overlap

    project_file_ids = {}
    if process_request.file_id:
        asset_record = await asset_model.get_asset_record(
            asset_project_id=project.project_id, 
            asset_name=process_request.file_id
        )

        if asset_record is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "result_signal": ResponceSignal.FILE_ID_ERROR.value
                }
            )
        
        project_file_ids = {
            asset_record.asset_id: asset_record.asset_name
        }

    else:
        # get all file ids from the project
        
        project_assets = await asset_model.get_all_project_assets(
            asset_project_id=project.project_id,
            asset_type=AssetTypeEnum.FILE.value
        )
        project_file_ids = {
            asset.asset_id : asset.asset_name 
            for asset in project_assets
        }

    if len(project_file_ids) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "result_signal": ResponceSignal.FILE_NOT_FOUND.value
            }
        )
    

    process_controller = ProcessController(project_id=project_id)
    num_records = 0
    num_files = 0

    if process_request.do_reset == 1:
        # Delete associated vectors collection
        collection_name = nlp_controller.create_collection_name(project_id=project.project_id)
        _= await request.app.vectordb_client.delete_collection(collection_name=collection_name)
        
        # Delete associated chunks
        _= await chunk_model.delete_chunks_by_project_id(project_id=project.project_id)

    for asset_id, file_id in project_file_ids.items():
        file_content = process_controller.get_file_content(file_id=file_id)

        if file_content is None:
            logger.error(f"Error while processing file {file_id} from project {project_id}")
            continue 

        file_chunks = process_controller.process_file_content(
            file_content=file_content, 
            file_id=file_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        if file_chunks is None or len(file_chunks) == 0:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "result_signal": ResponceSignal.FILE_PROCESSING_FAILED.value
                }
            )
        
        file_chunks_record = [
            DataChunk(
                chunk_text=chunk.page_content,
                chunk_metadata=chunk.metadata,
                chunk_order=i+1,
                chunk_project_id=project.project_id,
                chunk_asset_id=asset_id,
            ) 
            for i, chunk in enumerate(file_chunks)
        ]


        num_records += await chunk_model.insert_many_chunks(chunks=file_chunks_record)
        num_files += 1

    return JSONResponse(
        content={
            "result_signal": ResponceSignal.FILE_PROCESSING_SUCCESSFULL.value,
            "inserted_chunks": num_records,
            "files_processed": num_files
        }
    )
    