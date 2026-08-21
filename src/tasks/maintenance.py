from celery_app import celery_app, get_setup_utils
from helpers.config import get_settings
import asyncio
from utils import IdempotencyManager
import logging

logger = logging.getLogger("celery.task")

@celery_app.task(name="tasks.maintenance.clean_celery_execution_table", autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 60})
def clean_celery_execution_table():
    try:
        return asyncio.run(_clean_celery_execution_table())
    except Exception as e:
        logger.error(f"Error cleaning up old tasks: {e}")
        raise

async def _clean_celery_execution_table():
    db_engine, vectordb_client = None, None
    try:
        (db_engine, db_client,llm_provider_factory, vectordb_provider_factory, 
        generation_client, embedding_client, vectordb_client, template_parser) = await get_setup_utils()

        idempotency_manager = IdempotencyManager(db_client=db_client, db_engine=db_engine)

        settings = get_settings()

        # Clean up old tasks
        deleted_records = await idempotency_manager.clean_old_tasks(time_retention=settings.CELERY_TASK_CLEANUP_RETENTION)

        return {
            "status": "SUCCESS",
            "deleted_records": deleted_records
        }
    except Exception as e:
        logger.error(f"Error cleaning up old tasks: {str(e)}")
        raise
    finally:
        try:
            if vectordb_client:
                await vectordb_client.disconnect()
        except Exception as e:
            logger.error(f"Error while cleaning up resources: {str(e)}")