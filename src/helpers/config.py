from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Optional, Literal


# Known placeholder secrets that must never reach production.
_PLACEHOLDER_SECRETS = {
    "minirag_redis",
    "minirag_rabbitmq",
    "your_api_key_here",
    "your_password",
    "postgres_password",
    "admin_password",
}


class Settings(BaseSettings):

    APP_ENV: str = "production"
    APP_NAME: str
    APP_VERSION: str

    FILE_ALLOWED_TYPES: List[str]
    FILE_MAX_SIZE: int
    FILE_DEFAULT_CHUNK_SIZE: int

    GENERATION_BACKEND_LITERAL: Optional[List[str]] = None
    GENERATION_BACKEND: Literal["OPENAI", "COHERE"]
    EMBEDDING_BACKEND: Literal["OPENAI", "COHERE"]

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_URL: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None

    GENERATION_MODEL_ID: Optional[str] = None
    EMBEDDING_MODEL_ID: Optional[str] = None
    EMBEDDING_MODEL_SIZE: Optional[int] = None
    INPUT_DAFAULT_MAX_CHARACTERS: Optional[int] = None
    GENERATION_DAFAULT_MAX_TOKENS: Optional[int] = None
    GENERATION_DAFAULT_TEMPERATURE: Optional[float] = None

    VECTOR_DB_BACKEND_LITERAL: Optional[List[str]] = None
    VECTOR_DB_BACKEND: Literal["PGVECTOR", "QDRANT"]
    VECTOR_DB_PATH: str
    VECTOR_DB_DISTANCE_METHOD: Optional[str] = None
    VECTOR_DB_PGVEC_INDEX_THRESHOLD: Optional[int] = None

    PRIMARY_LANG: str = "en"
    DEFAULT_LANG: str = "en"

    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_MAIN_DATABASE: str
    POSTGRES_POOL_SIZE: int = 10
    POSTGRES_MAX_OVERFLOW: int = 20
    POSTGRES_POOL_TIMEOUT: int = 30
    POSTGRES_POOL_RECYCLE: int = 1800

    # ── CORS Settings ─────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["*"]

    # ── JWT Auth ──────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "minirag-default-super-secret-jwt-key-for-dev-only-32bytes"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── Redis (used by rate limiter) ──────────────────────────────────────────
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None

    # ── Malware Scanning (ClamAV) ─────────────────────────────────────────────
    CLAMAV_HOST: str = "clamav"
    CLAMAV_PORT: int = 3310
    CLAMAV_ENABLED: bool = False

    # Celery Configuration - Essential settings Only
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_TASK_TIME_LIMIT: int = 600
    CELERY_TASK_ACKS_LATE: bool = True
    CELERY_WORKER_CONCURRENCY: int = 2
    CELERY_FLOWER_PASSWORD: Optional[str] = None
    CELERY_TASK_CLEANUP_RETENTION: int = 86400

    # ── Startup Secret Validators ──────────────────────────────────────────────
    # These validators run at application startup and hard-fail if any known
    # placeholder/default secret is detected.  Misconfiguration is surfaced
    # immediately at boot rather than silently accepted.

    @field_validator("CELERY_RESULT_BACKEND", mode="after")
    @classmethod
    def reject_placeholder_redis(cls, v: Optional[str]) -> Optional[str]:
        if v and any(p in v for p in ("minirag_redis",)):
            raise ValueError(
                "CELERY_RESULT_BACKEND contains a known placeholder password "
                "('minirag_redis'). Set a real REDIS_PASSWORD before starting."
            )
        return v

    @field_validator("CELERY_BROKER_URL", mode="after")
    @classmethod
    def reject_placeholder_rabbitmq(cls, v: Optional[str]) -> Optional[str]:
        if v and any(p in v for p in ("minirag_rabbitmq",)):
            raise ValueError(
                "CELERY_BROKER_URL contains a known placeholder password "
                "('minirag_rabbitmq'). Set a real RABBITMQ password before starting."
            )
        return v

    @field_validator("OPENAI_API_KEY", mode="after")
    @classmethod
    def reject_placeholder_openai_key(cls, v: Optional[str]) -> Optional[str]:
        if v and v.strip() in _PLACEHOLDER_SECRETS:
            raise ValueError(
                "OPENAI_API_KEY is set to a known placeholder value. "
                "Replace it with a real API key."
            )
        return v

    @field_validator("COHERE_API_KEY", mode="after")
    @classmethod
    def reject_placeholder_cohere_key(cls, v: Optional[str]) -> Optional[str]:
        if v and v.strip() in _PLACEHOLDER_SECRETS:
            raise ValueError(
                "COHERE_API_KEY is set to a known placeholder value. "
                "Replace it with a real API key."
            )
        return v

    @field_validator("POSTGRES_PASSWORD", mode="after")
    @classmethod
    def reject_placeholder_postgres_password(cls, v: str) -> str:
        if v and v.strip() in _PLACEHOLDER_SECRETS:
            raise ValueError(
                "POSTGRES_PASSWORD is set to a known placeholder value "
                "('postgres_password'). Set a real database password before starting."
            )
        return v

    @field_validator("JWT_SECRET_KEY", mode="after")
    @classmethod
    def reject_placeholder_jwt_secret(cls, v: str) -> str:
        if v and v.strip() in _PLACEHOLDER_SECRETS:
            raise ValueError(
                "JWT_SECRET_KEY is set to a known placeholder value. "
                "Generate a real secret (e.g. `openssl rand -hex 32`) before starting."
            )
        return v

    class Config:
        env_file = [".env", "src/.env"]
        extra = "ignore"


def get_settings():
    return Settings()