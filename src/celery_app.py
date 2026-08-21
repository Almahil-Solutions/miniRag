from celery import Celery
from helpers.config import get_settings

from stores.llm import LLMProviderFactory, TemplateParser
from stores.vectordb import VectorDBProviderFactory, VectorDBEnums
from tasks.shared_engine import get_shared_engine, get_shared_sessionmaker

settings = get_settings()


async def get_setup_utils():
    settings = get_settings()
    db_engine = get_shared_engine()
    db_client = get_shared_sessionmaker()

    llm_provider_factory = LLMProviderFactory(settings)
    vectordb_provider_factory = VectorDBProviderFactory(config=settings, db_client=db_client)
    
    # Generation Client Providers
    generation_client = llm_provider_factory.create(provider=settings.GENERATION_BACKEND)
    generation_client.set_generation_model(model_id=settings.GENERATION_MODEL_ID)

    # Embedding Client Providers
    embedding_client = llm_provider_factory.create(provider=settings.EMBEDDING_BACKEND)
    embedding_client.set_embedding_model(model_id=settings.EMBEDDING_MODEL_ID, embedding_size=settings.EMBEDDING_MODEL_SIZE)

    # Vector DB Client Providers
    vectordb_client = vectordb_provider_factory.create(provider=settings.VECTOR_DB_BACKEND)
    await vectordb_client.connect()

    # Template Parser
    template_parser = TemplateParser(
        language=settings.PRIMARY_LANG,
        default_language=settings.DEFAULT_LANG
    )

    return (db_engine, db_client,llm_provider_factory, vectordb_provider_factory,
            generation_client, embedding_client, vectordb_client, template_parser)




# Create Celery app instance
celery_app = Celery(
    "miniRag",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,

    include=[
        "tasks.file_processing",
        "tasks.data_indexing",
        "tasks.process_workflow",
        "tasks.maintenance",


    ]
)


celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_TASK_SERIALIZER,
    accept_content=[settings.CELERY_TASK_SERIALIZER],

    # Task safety - Late acknowledgement prevents task loss if worker crashes
    task_acks_late=settings.CELERY_TASK_ACKS_LATE,

    # Time limits - Prevent long-running (hanging) tasks from blocking workers
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,

    # Result backend - store results for status tracking, and delete after 1 hour (3600s)
    task_ignore_result=False,
    result_expires=3600,

    # Worker configuration
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,

    # Connection settings for better reliability
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    worker_cancel_long_running_tasks_on_connection_loss=True,

    task_routes={
        "tasks.file_processing.process_project_files": {"queue": "file_processing_queue"},
        "tasks.data_indexing.index_project_data": {"queue": "data_indexing_queue"},
        "tasks.process_workflow.process_and_push_workflow": {"queue": "file_processing_queue"},
        "tasks.maintenance.clean_celery_execution_table": {"queue": "default"},

    },

    # Beat schedule - Periodic tasks
    beat_schedule={
        "clean-up-old-task-records": {
            "task": "tasks.maintenance.clean_celery_execution_table",
            "schedule": 86400,
            "args": ()
        }
    },

    timezone='UTC',
    

)


# Register tasks
celery_app.conf.task_default_queue = "default"
