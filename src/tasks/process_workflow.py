from celery import chain
from celery_app import celery_app, get_setup_utils
from helpers.config import get_settings
import asyncio
import logging
from tasks.file_processing import process_project_files
from tasks.data_indexing import _index_project_data


from controllers import ProcessController, NLPController
from models import ResponceSignal, ProjectModel, ChunkModel, DataChunk, AssetModel, AssetTypeEnum
from tqdm.auto import tqdm

logger = logging.getLogger("celery.task")

@celery_app.task(bind=True, name="tasks.process_workflow.push_after_process_task", autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 60})
def push_after_process_task(self, previous_task_result):

    project_id = previous_task_result.get("project_id")
    do_reset = previous_task_result.get("do_reset")

    task_result = asyncio.run(_index_project_data(self, project_id, do_reset))
    
    return {
        "project_id": project_id,
        "do_reset": do_reset,
        "task_result": task_result
    }
    


@celery_app.task(
                bind=True, 
                name="tasks.process_workflow.process_and_push_workflow", 
                autoretry_for=(Exception,), 
                retry_kwargs={"max_retries": 3, "countdown": 60}
)
def process_and_push_workflow(self, project_id: int, file_name: str = None, chunk_size: int = 100,chunk_overlap: int = 20, do_reset: int = 0 ):
    workflow_task = chain(

        process_project_files.s(project_id=project_id, file_name=file_name, chunk_size=chunk_size, chunk_overlap=chunk_overlap, do_reset=do_reset),
        push_after_process_task.s()
    )
    result = workflow_task.apply_async()
    return{
        "signal": "WORKFLOW_STARTED",
        "workflow_id": result.id,
        "tasks": ["tasks.file_processing.process_project_files", "tasks.data_indexing.index_project_data"]
    }