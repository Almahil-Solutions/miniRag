import asyncio
import os
import sys
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.compiler import compiles

# Register SQLite compilation for PostgreSQL types
@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"

from models.db_schemes.minirag.schemes.minirag_base import SQLAlchemyBase
import models.db_schemes.minirag.schemes  # Ensure all schemes are registered
from models.db_schemes import User, UserRole, Project, Asset, DataChunk, QueryLog
from helpers.security import hash_password, create_access_token
from helpers.config import get_settings


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def db_engine():
    """Create in-memory SQLite async engine and initialize all tables."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLAlchemyBase.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(SQLAlchemyBase.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_client(db_engine):
    """Async sessionmaker factory for database operations."""
    return sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def mock_llm_client():
    """Mock LLM Generation & Embedding Client."""
    client = MagicMock()
    client.generate_text = MagicMock(return_value="This is a mock LLM generated answer.")
    client.generate_text_stream = MagicMock(return_value=["This ", "is ", "a ", "streamed ", "answer."])
    client.embed_text = MagicMock(return_value=[[0.1] * 1536])
    client.embedding_size = 1536
    client.preprocess_text = MagicMock(side_effect=lambda x: str(x))
    client.construct_prompt = MagicMock(side_effect=lambda prompt, role: {"role": role, "content": prompt})

    # Enums stub
    class Enums:
        class Role:
            SYSTEM = "system"
            USER = "user"
            ASSISTANT = "assistant"
        SYSTEM = MagicMock(value="system")
        USER = MagicMock(value="user")
        ASSISTANT = MagicMock(value="assistant")
    client.enums = Enums
    return client


@pytest.fixture
def mock_vectordb_client():
    """Mock Vector Database Client."""
    client = AsyncMock()
    client.default_vector_size = 1536
    client.create_collection = AsyncMock(return_value=True)
    client.delete_collection = AsyncMock(return_value=True)
    client.insert_many = AsyncMock(return_value=True)
    client.delete_by_asset_id = AsyncMock(return_value=True)

    class MockCollectionInfo:
        def __init__(self):
            self.vectors_count = 10
            self.status = "green"
            self.__dict__ = {"vectors_count": 10, "status": "green"}

    client.get_collection_info = AsyncMock(return_value=MockCollectionInfo())

    class MockSearchResult:
        def __init__(self, text: str = "Relevant context snippet from document.", score: float = 0.92):
            self.text = text
            self.score = score
        def dict(self):
            return {"text": self.text, "score": self.score}

    client.search_by_vector = AsyncMock(return_value=[MockSearchResult()])
    return client


@pytest.fixture
def mock_redis():
    """Mock Redis client for rate limiting."""
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.ttl = AsyncMock(return_value=60)
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    return redis


@pytest_asyncio.fixture
async def test_user(db_client) -> User:
    """Create and persist a standard member test user."""
    user = User(
        user_id=uuid.uuid4(),
        email="member@example.com",
        hashed_password=hash_password("Password123!"),
        full_name="Member Test User",
        role=UserRole.MEMBER,
        plan="free",
        monthly_llm_budget=100.0,
        is_active=True,
    )
    async with db_client() as session:
        async with session.begin():
            session.add(user)
        await session.commit()
    return user


@pytest_asyncio.fixture
async def test_admin(db_client) -> User:
    """Create and persist an admin test user."""
    admin = User(
        user_id=uuid.uuid4(),
        email="admin@example.com",
        hashed_password=hash_password("AdminPassword123!"),
        full_name="Admin Test User",
        role=UserRole.ADMIN,
        plan="enterprise",
        monthly_llm_budget=500.0,
        is_active=True,
    )
    async with db_client() as session:
        async with session.begin():
            session.add(admin)
        await session.commit()
    return admin


@pytest_asyncio.fixture
async def user_token(test_user) -> str:
    """Generate JWT bearer token for member test user."""
    return create_access_token(
        user_id=str(test_user.user_id),
        role=test_user.role.value if hasattr(test_user.role, "value") else str(test_user.role),
        expires_minutes=60,
    )


@pytest_asyncio.fixture
async def admin_token(test_admin) -> str:
    """Generate JWT bearer token for admin test user."""
    return create_access_token(
        user_id=str(test_admin.user_id),
        role=test_admin.role.value if hasattr(test_admin.role, "value") else str(test_admin.role),
        expires_minutes=60,
    )


@pytest_asyncio.fixture
async def auth_headers(user_token) -> dict:
    return {"Authorization": f"Bearer {user_token}"}


@pytest_asyncio.fixture
async def admin_auth_headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture
async def test_project(db_client, test_user) -> Project:
    """Create and persist a project owned by test_user."""
    project = Project(
        project_id=1,
        project_uuid=uuid.uuid4(),
        owner_user_id=test_user.user_id,
    )
    async with db_client() as session:
        async with session.begin():
            session.add(project)
        await session.commit()
    return project


@pytest_asyncio.fixture
async def app_client(
    db_client,
    mock_llm_client,
    mock_vectordb_client,
    mock_redis
) -> AsyncGenerator[AsyncClient, None]:
    """Test AsyncClient configured with mock backend dependencies."""
    from main import app
    from stores.llm.templates.template_parser import TemplateParser
    app.db_client = db_client
    app.generation_client = mock_llm_client
    app.embedding_client = mock_llm_client
    app.vectordb_client = mock_vectordb_client
    app.redis_client = mock_redis
    app.template_parser = TemplateParser(language="en", default_language="en")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client
