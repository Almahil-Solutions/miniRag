from fastapi import APIRouter, FastAPI, status, Request
from fastapi.responses import JSONResponse
from helpers import get_settings, Settings
from .schemes.nlp import PushRequest, SearchRequest
from models import ResponceSignal, ProjectModel, ChunkModel, DataChunk
from controllers import NLPController
import logging
from tasks.data_indexing import index_project_data

log = logging.getLogger("uvicorn.error")


nlp_router = APIRouter(
    prefix="/api/v1/nlp",
    tags=["api_v1", "nlp"]
)


@nlp_router.post("/index/push/{project_id}")
async def index_project(request: Request, project_id: int, push_request: PushRequest ):
    task = index_project_data.delay(
        project_id=project_id,
        do_reset=push_request.do_reset
    )
    return JSONResponse(
        content={
            "signal": ResponceSignal.DATA_PUSH_TASK_READY.value,
            "task_id": task.id
        }
    )


@nlp_router.get("/index/info/{project_id}")
async def get_project_index_info(request: Request, project_id: int):

    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )

    project = await project_model.get_project_or_create_one(project_id=project_id)

        
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser
    )

    collection_info = await nlp_controller.get_vector_db_collection_info(project_id=project_id)

    if not collection_info:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponceSignal.VECTORDB_COLLECTION_NOT_RETRIEVED.value
            }
        )
    return JSONResponse(
        content={
            "signal": ResponceSignal.VECTORDB_COLLECTION_RETRIEVED.value,
            "collection_info": collection_info
        }
    )

    


@nlp_router.post("/index/search/{project_id}")
async def search_index(request: Request, project_id: int, search_request: SearchRequest ):

    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)

    project = await project_model.get_project_or_create_one(project_id=project_id)

        
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser

    )

    results = await nlp_controller.search_vector_db_collection(project=project, text=search_request.text, limit=search_request.limit)

    if not results:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponceSignal.VECTORDB_SEARCH_ERROR.value
            }
        )
    return JSONResponse(
        content={
            "signal": ResponceSignal.VECTORDB_SEARCH_SUCCESS.value,
            "results": [result.dict() for result in results]
        }
    )


@nlp_router.post("/index/answer/{project_id}")
async def answer_rag(request: Request, project_id: int, search_request: SearchRequest ):

    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)

    project = await project_model.get_project_or_create_one(project_id=project_id)


    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser
    )

    answer, full_prompt, chat_history = await nlp_controller.answer_rag_question(
        project=project,
        query=search_request.text,
        limit=search_request.limit,
        language=search_request.language
    )

    if not answer:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponceSignal.RAG_ANSWER_ERROR.value
            }
        )
    return JSONResponse(
        content={
            "signal": ResponceSignal.RAG_ANSWER_SUCCESS.value,
            "answer": answer,
            "full_prompt": full_prompt,
            "chat_history": chat_history
        }
    )