import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
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


import json
from datetime import datetime, timezone

# ── Structured JSON Logging (P2.3) ───────────────────────────────────────────

class JSONLogFormatter(logging.Formatter):
    """Formats log records as structured JSON lines."""
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "user_id", "method", "path", "status_code", "latency_ms"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


# Configure root/uvicorn handler with JSON formatter
_log_handler = logging.StreamHandler()
_log_handler.setFormatter(JSONLogFormatter())
logging.basicConfig(level=logging.INFO, handlers=[_log_handler], force=True)
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
    # SQLAlchemy connection pooling (P2.5)
    app.db_engine = create_async_engine(
        postgres_conn,
        pool_size=settings.POSTGRES_POOL_SIZE,
        max_overflow=settings.POSTGRES_MAX_OVERFLOW,
        pool_timeout=settings.POSTGRES_POOL_TIMEOUT,
        pool_recycle=settings.POSTGRES_POOL_RECYCLE,
        pool_pre_ping=True,
        connect_args={"server_settings": {"statement_timeout": "30000"}},
    )
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
settings = get_settings()
_allow_all = "*" in settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    allow_credentials=not _allow_all,
)


# ── HTTP Exception Handler ─────────────────────────────────────────────────────
# Passes through Starlette/FastAPI HTTP exceptions (404, 405, 422, etc.) with
# their correct status codes.  Without this, the catch-all Exception handler
# below would intercept them and incorrectly return 500.

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# ── Validation Error Handler ───────────────────────────────────────────────────
# Returns 422 with field-level error details for request body / query param
# validation failures instead of leaking them via the generic 500 handler.

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


# ── Global Exception Handler (P0.6) ───────────────────────────────────────────
# Catches any remaining unhandled exception, logs it server-side with a full
# traceback, and returns a generic error response that does NOT leak
# implementation details or stack traces to the client.

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
