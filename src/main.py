import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from helpers.config import get_settings
from stores.llm import LLMProviderFactory, TemplateParser
from stores.vectordb import VectorDBProviderFactory, VectorDBEnums
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import metrics setup
from utils import setup_metrics, PrometheusMiddleware
from utils.audit_logger import AuditLoggingMiddleware

# Route routers
from routes import base, data, nlp
from routes.projects import projects_router
from routes.auth import auth_router
from routes.users import users_router
from routes.admin import admin_router


logger = logging.getLogger("uvicorn.error")


# ── Lifespan (replaces deprecated on_event) ───────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic using the modern lifespan context manager.

    Replaces the deprecated ``app.on_event("startup")`` / ``on_event("shutdown")``
    pattern (PROJECT_SNAPSHOT issue #4).
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    settings = get_settings()

    postgres_conn = (
        f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"
    )
    app.db_engine = create_async_engine(postgres_conn)
    app.db_client = sessionmaker(
        app.db_engine, class_=AsyncSession, expire_on_commit=False
    )

    # ── Redis async client (required by rate limiter) ─────────────────────
    try:
        from redis.asyncio import Redis
        redis_host = getattr(settings, "REDIS_HOST", "redis")
        redis_port = getattr(settings, "REDIS_PORT", 6379)
        redis_password = getattr(settings, "REDIS_PASSWORD", None)
        app.redis_client = Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            decode_responses=True,
        )
        # Ping to confirm connectivity at startup (non-fatal)
        await app.redis_client.ping()
        logger.info("Redis client connected: %s:%s", redis_host, redis_port)
    except Exception as exc:
        logger.warning("Redis unavailable at startup — rate limiting disabled: %s", exc)
        app.redis_client = None

    # ── LLM providers ─────────────────────────────────────────────────────
    llm_provider_factory = LLMProviderFactory(settings)
    vectordb_provider_factory = VectorDBProviderFactory(
        config=settings, db_client=app.db_client
    )

    app.generation_client = llm_provider_factory.create(provider=settings.GENERATION_BACKEND)
    app.generation_client.set_generation_model(model_id=settings.GENERATION_MODEL_ID)

    app.embedding_client = llm_provider_factory.create(provider=settings.EMBEDDING_BACKEND)
    app.embedding_client.set_embedding_model(
        model_id=settings.EMBEDDING_MODEL_ID,
        embedding_size=settings.EMBEDDING_MODEL_SIZE,
    )

    app.vectordb_client = vectordb_provider_factory.create(provider=settings.VECTOR_DB_BACKEND)
    await app.vectordb_client.connect()

    app.template_parser = TemplateParser(
        language=settings.PRIMARY_LANG,
        default_language=settings.DEFAULT_LANG,
    )

    yield  # ── Application runs ─────────────────────────────────────────────

    # ── Shutdown ──────────────────────────────────────────────────────────────
    await app.db_engine.dispose()
    await app.vectordb_client.disconnect()

    if app.redis_client is not None:
        await app.redis_client.aclose()


# ── Application factory ────────────────────────────────────────────────────────
# Conditionally disable OpenAPI documentation and schema in production (P0.5)
_app_env = os.getenv("APP_ENV", "production").strip().lower()
_is_dev = _app_env in ("development", "dev", "local")

app = FastAPI(
    title="miniRAG",
    docs_url="/docs" if _is_dev else None,
    redoc_url="/redoc" if _is_dev else None,
    openapi_url="/openapi.json" if _is_dev else None,
    lifespan=lifespan,
)

# Prometheus metrics (must be added before other middleware)
setup_metrics(app)

# ── Audit logging middleware ───────────────────────────────────────────────────
app.add_middleware(AuditLoggingMiddleware)

# ── CORS middleware ────────────────────────────────────────────────────────────
# TODO: Narrow ``allow_origins`` to your real frontend domain(s) in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Replace with explicit origins in prod
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    allow_credentials=False,      # Must be False when allow_origins=["*"]
)


# ── Global Exception Handler (P0.6) ───────────────────────────────────────────
# Catches any unhandled exception, logs it server-side with a full traceback,
# and returns a generic error response that does NOT leak implementation details
# or stack traces to the client.

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"signal": "INTERNAL_SERVER_ERROR"},
    )


# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(base.base_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)
app.include_router(projects_router)
