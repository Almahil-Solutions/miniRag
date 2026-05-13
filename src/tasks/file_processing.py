from celery_app import celery_app, get_setup_utils
from helpers.config import get_settings
import asyncio
import logging
from utils import IdempotencyManager


from controllers import ProcessController, NLPController
from models import ResponceSignal, ProjectModel, ChunkModel, DataChunk, AssetModel, AssetTypeEnum

logger = logging.getLogger("celery.task")


@celery_app.task(bind=True, name="tasks.file_processing.process_project_files", autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 60})
def process_project_files(self, project_id: int, file_name: str = None, chunk_size: int = 100,
         chunk_overlap: int = 20, do_reset: int = 0 ):
    try:
        return asyncio.run(_process_project_files(self, project_id, file_name, chunk_size, chunk_overlap, do_reset))
    except Exception as e:
        logger.error(f"Error processing project files: {e}")
        raise

async def _process_project_files(task_instance, project_id: int, file_name: str = None, chunk_size: int = 100,
         chunk_overlap: int = 20, do_reset: int = 0 ):
    db_engine, vectordb_client = None, None
    try:
        (db_engine, db_client,llm_provider_factory, vectordb_provider_factory, 
        generation_client, embedding_client, vectordb_client, template_parser) = await get_setup_utils()

        idempotency_manager = IdempotencyManager(db_client=db_client, db_engine=db_engine)

        task_args = {
            "project_id": project_id,
            "file_name": file_name,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "do_reset": do_reset
        }

        task_name = "tasks.file_processing.process_project_files"

        settings = get_settings()

        # Check if task should be executed
        should_execute, existing_task = await idempotency_manager.should_execute_task(
            task_name=task_name,
            task_args=task_args,
            celery_task_id=task_instance.request.id,
            task_time_limit=settings.CELERY_TASK_TIME_LIMIT
        )
        if not should_execute:
            logger.warning(f"Can not handle the task | status : {existing_task.status}")
            return existing_task.result

        task_record = None
        if existing_task:
            # update the existing task with new celery task id
            await idempotency_manager.update_task_status(
                execution_id=existing_task.execution_id,
                status="PENDING"
            )
            task_record = existing_task

        else:
            # create new task record
            task_record = await idempotency_manager.create_task_record(
                task_name=task_name,
                task_args=task_args,
                celery_task_id=task_instance.request.id
            )
        
        # update task status to STARTED
        await idempotency_manager.update_task_status(
            execution_id=task_record.execution_id,
            status="STARTED"
        )
            

        project_model = await ProjectModel.create_instance(db_client=db_client)
        project = await project_model.get_project_or_create_one(project_id=project_id)
        chunk_model = await ChunkModel.create_instance(db_client=db_client)
        asset_model = await AssetModel.create_instance(db_client=db_client)

        nlp_controller = NLPController(
            vectordb_client=vectordb_client,
            generation_client=generation_client,
            embedding_client=embedding_client,
            template_parser=template_parser,
        )


        project_file_ids = {}
        if file_name:
            asset_record = await asset_model.get_asset_record(
                asset_project_id=project.project_id, 
                asset_name=file_name
            )

            if asset_record is None:
                task_instance.update_state(
                    state='FAILURE',
                    meta={
                        "result_signal": ResponceSignal.FILE_ID_ERROR.value,
                    }
                )
                # update task status to FAILURE
                await idempotency_manager.update_task_status(
                    execution_id=task_record.execution_id,
                    status="FAILURE",
                    result={
                        "result_signal": ResponceSignal.FILE_ID_ERROR.value,
                    }
                )
                raise Exception(f"No asset for asset name {file_name} in project {project_id}")

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
            task_instance.update_state(
                state='FAILURE',
                meta={
                    "result_signal": ResponceSignal.FILE_NOT_FOUND.value,
                }
            )
            # update task status to FAILURE
            await idempotency_manager.update_task_status(
                execution_id=task_record.execution_id,
                status="FAILURE",
                result={
                    "result_signal": ResponceSignal.FILE_NOT_FOUND.value,
                }
            )
            raise Exception(f"No files found in project {project_id}")


        process_controller = ProcessController(project_id=project_id)
        num_records = 0
        num_files = 0

        if do_reset == 1:
            # Delete associated vectors collection
            collection_name = nlp_controller.create_collection_name(project_id=project.project_id)
            _= await vectordb_client.delete_collection(collection_name=collection_name)
            
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
                logger.error(f"No chunks generated for file {file_id} in project {project_id}")
                continue
            
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

        task_instance.update_state(
            state='SUCCESS',
            meta={
                "result_signal": ResponceSignal.FILE_PROCESSING_SUCCESSFULL.value,
                "inserted_chunks": num_records,
                "files_processed": num_files
            }
        )
        # update task status to SUCCESS
        await idempotency_manager.update_task_status(
            execution_id=task_record.execution_id,
            status="SUCCESS",
            result={
                "result_signal": ResponceSignal.FILE_PROCESSING_SUCCESSFULL.value,
                "inserted_chunks": num_records,
                "files_processed": num_files,
                "project_id": project_id,
                "do_reset": do_reset
            }
        )
        return {
            "result_signal": ResponceSignal.FILE_PROCESSING_SUCCESSFULL.value,
            "inserted_chunks": num_records,
            "files_processed": num_files,
            "project_id": project_id,
            "do_reset": do_reset
        }
    except Exception as e:
        logger.error(f"Error processing project files: {str(e)}")
        raise
    finally:
        try:
            if db_engine:
                await db_engine.dispose()
            if vectordb_client:
                await vectordb_client.disconnect()
        except Exception as e:
            logger.error(f"Error while cleaning up resources: {str(e)}")