"""NLP routes — vector index management, semantic search, and RAG answering.

Path parameters use ``project_uuid`` (UUID) instead of the internal integer
``project_id`` so that sequential IDs are never exposed in public URLs (P1.7).
The ``require_project_owner`` dependency resolves the UUID to the full Project
ORM object, which is then passed to the controller.

Rate limiting is applied to the ``search`` and ``answer`` endpoints via the
``rate_limit_dependency`` (P2.1).  Detailed query-level audit logs are written
inside those handlers (P2.2).
"""

from uuid import UUID
import logging
import os
import time

from fastapi import APIRouter, Depends, Query, status, Request
from fastapi.responses import JSONResponse, StreamingResponse

from helpers import get_settings, Settings
from helpers.security import get_current_user, require_project_owner
from utils.rate_limiter import rate_limit_dependency
from .schemes.nlp import PushRequest, SearchRequest
from models import ResponceSignal, ProjectModel, ChunkModel, DataChunk, QueryLogModel
from controllers import NLPController
from tasks.data_indexing import index_project_data

log = logging.getLogger("uvicorn.error")


nlp_router = APIRouter(
    prefix="/api/v1/nlp",
    tags=["api_v1", "nlp"]
)


# ---------------------------------------------------------------------------
# POST /index/push/{project_uuid}
# ---------------------------------------------------------------------------

@nlp_router.post("/index/push/{project_uuid}")
async def index_project(
    request: Request,
    project_uuid: UUID,
    push_request: PushRequest,
    user=Depends(get_current_user),
    project=Depends(require_project_owner),
):
    """Trigger a Celery task to (re)index all project chunks into the vector DB."""
    task = index_project_data.delay(
        project_id=project.project_id,
        do_reset=push_request.do_reset
    )
    return JSONResponse(
        content={
            "signal": ResponceSignal.DATA_PUSH_TASK_READY.value,
            "task_id": task.id
        }
    )


# ---------------------------------------------------------------------------
# GET /index/info/{project_uuid}
# ---------------------------------------------------------------------------

@nlp_router.get("/index/info/{project_uuid}")
async def get_project_index_info(
    request: Request,
    project_uuid: UUID,
    user=Depends(get_current_user),
    project=Depends(require_project_owner),
):
    """Return vector DB collection metadata for the given project."""
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser
    )

    collection_info = await nlp_controller.get_vector_db_collection_info(project_id=project.project_id)

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


# ---------------------------------------------------------------------------
# POST /index/search/{project_uuid}   (rate-limited, audit-logged)
# ---------------------------------------------------------------------------

@nlp_router.post("/index/search/{project_uuid}")
async def search_index(
    request: Request,
    project_uuid: UUID,
    search_request: SearchRequest,
    user=Depends(get_current_user),
    project=Depends(require_project_owner),
    _rl=Depends(rate_limit_dependency),
):
    """Semantic search against the project's vector index.

    Rate limited (plan-aware) and audit-logged with query_text and a summary
    of the result count.
    """
    start_ts = time.perf_counter()
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser
    )

    results = await nlp_controller.search_vector_db_collection(
        project=project, text=search_request.text, limit=search_request.limit
    )

    latency_ms = int((time.perf_counter() - start_ts) * 1_000)

    # ── Detailed audit log (P2.2) ─────────────────────────────────────────
    try:
        log_model = await QueryLogModel.create_instance(db_client=request.app.db_client)
        await log_model.create_log(
            user_id=str(user.user_id),
            project_id=project.project_id,
            endpoint=request.url.path,
            query_text=search_request.text,
            result_summary={
                "result_count": len(results) if results else 0,
                "limit": search_request.limit,
            },
            status="success" if results else "no_results",
            latency_ms=latency_ms,
            ip_address=getattr(request.client, "host", None),
            request_id=getattr(request.state, "request_id", None),
        )
    except Exception as exc:
        log.warning("search_index: failed to write detailed audit log: %s", exc)

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


# ---------------------------------------------------------------------------
# POST /index/answer/{project_uuid}   (rate-limited, audit-logged)
# ---------------------------------------------------------------------------

@nlp_router.post("/index/answer/{project_uuid}")
async def answer_rag(
    request: Request,
    project_uuid: UUID,
    search_request: SearchRequest,
    user=Depends(get_current_user),
    project=Depends(require_project_owner),
    _rl=Depends(rate_limit_dependency),
):
    """RAG answer generation: semantic search + LLM summarisation.

    Rate limited (plan-aware), LLM budget-checked (A5), and audit-logged
    with query_text, answer length, and call cost in result_summary.
    """
    # ── Monthly LLM Budget Check (A5) ────────────────────────────────────
    user_budget = getattr(user, "monthly_llm_budget", None)
    if user_budget is not None and user_budget > 0:
        try:
            log_model = await QueryLogModel.create_instance(db_client=request.app.db_client)
            current_spend = await log_model.get_monthly_spend(str(user.user_id))
            if current_spend >= user_budget:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Monthly LLM budget exceeded. Please upgrade your plan or contact support.",
                        "current_spend": current_spend,
                        "monthly_budget": user_budget,
                    }
                )
        except Exception as exc:
            log.warning("answer_rag: failed to check monthly LLM budget: %s", exc)

    start_ts = time.perf_counter()
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser
    )

    if search_request.stream:
        return StreamingResponse(
            nlp_controller.answer_rag_question_stream(
                project=project,
                query=search_request.text,
                limit=search_request.limit,
                language=search_request.language,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    answer, full_prompt, chat_history = await nlp_controller.answer_rag_question(
        project=project,
        query=search_request.text,
        limit=search_request.limit,
        language=search_request.language
    )

    latency_ms = int((time.perf_counter() - start_ts) * 1_000)

    # ── Detailed audit log & Cost Tracking (P2.2, A5) ──────────────────────
    try:
        # Approximate cost calculation based on standard model token pricing
        estimated_cost = round(0.0015 + (len(answer) / 1000) * 0.002, 6) if answer else 0.0
        log_model = await QueryLogModel.create_instance(db_client=request.app.db_client)
        await log_model.create_log(
            user_id=str(user.user_id),
            project_id=project.project_id,
            endpoint=request.url.path,
            query_text=search_request.text,
            result_summary={
                "answer_length": len(answer) if answer else 0,
                "limit": search_request.limit,
                "language": search_request.language,
                "llm_cost": estimated_cost,
            },
            status="success" if answer else "error",
            latency_ms=latency_ms,
            ip_address=getattr(request.client, "host", None),
            request_id=getattr(request.state, "request_id", None),
        )
    except Exception as exc:
        log.warning("answer_rag: failed to write detailed audit log: %s", exc)

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


# ---------------------------------------------------------------------------
# GET /history   (P2.2 — user query log)
# ---------------------------------------------------------------------------

@nlp_router.get("/history")
async def get_nlp_history(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
):
    """Return the authenticated user's NLP query history (newest-first).

    This endpoint lets users audit their own search and answer activity.
    Admin users can view all logs via GET /api/v1/admin/query-logs.
    """
    log_model = await QueryLogModel.create_instance(db_client=request.app.db_client)
    logs, total_pages = await log_model.get_logs_for_user(
        user_id=str(user.user_id),
        page=page,
        page_size=page_size,
    )

    return JSONResponse(
        content={
            "logs": [
                {
                    "log_id": str(entry.log_id),
                    "project_id": entry.project_id,
                    "endpoint": entry.endpoint,
                    "query_text": entry.query_text,
                    "result_summary": entry.result_summary,
                    "status": entry.status,
                    "latency_ms": entry.latency_ms,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None,
                }
                for entry in logs
            ],
            "page": page,
            "total_pages": total_pages,
        }
    )