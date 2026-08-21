from fastapi import APIRouter, Depends, status, Request
from fastapi.responses import JSONResponse
from helpers import get_settings, Settings
from helpers.security import get_current_user, require_project_owner
from .schemes.nlp import PushRequest, SearchRequest
from models import ResponceSignal, ProjectModel, ChunkModel, DataChunk
from controllers import NLPController
import logging
import os
from tasks.data_indexing import index_project_data

log = logging.getLogger("uvicorn.error")


nlp_router = APIRouter(
    prefix="/api/v1/nlp",
    tags=["api_v1", "nlp"]
)


@nlp_router.post("/index/push/{project_id}")
async def index_project(
    request: Request,
    project_id: int,
    push_request: PushRequest,
    user=Depends(get_current_user),
    project=Depends(require_project_owner),
):
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
async def get_project_index_info(
    request: Request,
    project_id: int,
    user=Depends(get_current_user),
    project=Depends(require_project_owner),
):
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
async def search_index(
    request: Request,
    project_id: int,
    search_request: SearchRequest,
    user=Depends(get_current_user),
    project=Depends(require_project_owner),
):
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser
    )

    results = await nlp_controller.search_vector_db_collection(
        project=project, text=search_request.text, limit=search_request.limit
    )

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
async def answer_rag(
    request: Request,
    project_id: int,
    search_request: SearchRequest,
    user=Depends(get_current_user),
    project=Depends(require_project_owner),
):
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

    # Build the base response — never expose prompt internals in production.
    response_body: dict = {
        "signal": ResponceSignal.RAG_ANSWER_SUCCESS.value,
        "answer": answer,
    }

    # Gate debug fields behind APP_ENV=development to prevent prompt leakage
    # in production (see PROJECT_SNAPSHOT issue #15).
    if os.getenv("APP_ENV", "production") == "development":
        response_body["full_prompt"] = full_prompt
        response_body["chat_history"] = [
            msg if isinstance(msg, dict) else vars(msg)
            for msg in (chat_history or [])
        ]

    return JSONResponse(content=response_body)