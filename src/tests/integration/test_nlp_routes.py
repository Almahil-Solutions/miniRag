import pytest
from models.db_schemes import QueryLog


class TestNLPRoutesIntegration:
    @pytest.mark.asyncio
    async def test_search_index_authenticated(self, app_client, auth_headers, test_project):
        response = await app_client.post(
            f"/api/v1/nlp/index/search/{test_project.project_uuid}",
            json={"text": "How does vector search work in miniRAG?", "limit": 5},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["signal"] == "vector_db_search_success"
        assert len(data["results"]) >= 1

    @pytest.mark.asyncio
    async def test_search_index_unauthenticated(self, app_client, test_project):
        response = await app_client.post(
            f"/api/v1/nlp/index/search/{test_project.project_uuid}",
            json={"text": "Unauthenticated query", "limit": 5},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_search_index_validation_bounds(self, app_client, auth_headers, test_project):
        # limit > 50 should be rejected by Pydantic validation (P3.5)
        response = await app_client.post(
            f"/api/v1/nlp/index/search/{test_project.project_uuid}",
            json={"text": "Valid text query", "limit": 100},
            headers=auth_headers,
        )
        assert response.status_code == 422

        # text > 2000 chars should be rejected (P3.5)
        response_oversized = await app_client.post(
            f"/api/v1/nlp/index/search/{test_project.project_uuid}",
            json={"text": "a" * 2005, "limit": 10},
            headers=auth_headers,
        )
        assert response_oversized.status_code == 422

    @pytest.mark.asyncio
    async def test_answer_rag_success_and_audit_logging(self, app_client, auth_headers, test_project):
        response = await app_client.post(
            f"/api/v1/nlp/index/answer/{test_project.project_uuid}",
            json={"text": "Explain RAG architecture in miniRAG.", "limit": 5, "language": "en"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["signal"] == "rag_answer_success"
        assert "answer" in data
        assert len(data["answer"]) > 0

    @pytest.mark.asyncio
    async def test_answer_rag_stream(self, app_client, auth_headers, test_project):
        response = await app_client.post(
            f"/api/v1/nlp/index/answer/{test_project.project_uuid}",
            json={"text": "Stream answer test", "limit": 5, "stream": True},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_answer_rag_budget_exceeded(self, app_client, auth_headers, test_project, db_client, test_user):
        """A5: When monthly LLM spend meets or exceeds user's monthly_llm_budget, return 429."""
        # Insert a high-cost query log to exhaust budget
        qlog = QueryLog(
            user_id=test_user.user_id,
            project_id=test_project.project_id,
            endpoint="/api/v1/nlp/index/answer",
            query_text="Budget exhausting query",
            result_summary={"llm_cost": 150.0},  # Exceeds default budget of 100.0
            status="success",
        )
        async with db_client() as session:
            async with session.begin():
                session.add(qlog)
            await session.commit()

        response = await app_client.post(
            f"/api/v1/nlp/index/answer/{test_project.project_uuid}",
            json={"text": "Another query after budget exhausted", "limit": 5},
            headers=auth_headers,
        )
        assert response.status_code == 429
        assert "Monthly LLM budget exceeded" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_nlp_history(self, app_client, auth_headers, test_project, db_client, test_user):
        qlog = QueryLog(
            user_id=test_user.user_id,
            project_id=test_project.project_id,
            endpoint="/api/v1/nlp/index/search",
            query_text="Sample history query",
            result_summary={"result_count": 3},
            status="success",
            latency_ms=45,
        )
        async with db_client() as session:
            async with session.begin():
                session.add(qlog)
            await session.commit()

        response = await app_client.get("/api/v1/nlp/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert len(data["logs"]) >= 1
        assert any(entry["query_text"] == "Sample history query" for entry in data["logs"])
