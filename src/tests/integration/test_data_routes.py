import uuid
from unittest.mock import patch, MagicMock
import pytest
from models.db_schemes import User, UserRole, Project, Asset
from models.enums.AssetTypeEnum import AssetTypeEnum
from helpers.security import hash_password, create_access_token


class TestDataRoutesIntegration:
    @pytest.mark.asyncio
    async def test_create_project_and_listing(self, app_client, auth_headers):
        response = await app_client.post("/api/v1/projects", headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert "project_id" in data
        assert "project_uuid" in data

        list_resp = await app_client.get("/api/v1/projects", headers=auth_headers)
        assert list_resp.status_code == 200
        projects = list_resp.json()["projects"]
        assert any(p["project_uuid"] == data["project_uuid"] for p in projects)

    @pytest.mark.asyncio
    async def test_idor_protection_foreign_project_access_denied(self, app_client, db_client, test_project):
        """User B cannot access or inspect User A's project documents (returns 404)."""
        # Create second user
        other_user = User(
            user_id=uuid.uuid4(),
            email="attacker@example.com",
            hashed_password=hash_password("AttackerPass123!"),
            full_name="Attacker",
            role=UserRole.MEMBER,
            plan="free",
        )
        async with db_client() as session:
            async with session.begin():
                session.add(other_user)
            await session.commit()

        other_token = create_access_token(
            user_id=str(other_user.user_id),
            role="member",
            expires_minutes=30
        )
        other_headers = {"Authorization": f"Bearer {other_token}"}

        # Attempt to access test_project owned by test_user
        response = await app_client.get(
            f"/api/v1/data/{test_project.project_uuid}/documents",
            headers=other_headers
        )
        assert response.status_code == 404
        assert "Project not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_and_get_document_details(self, app_client, auth_headers, test_project, db_client):
        # Create an asset in the DB for test_project
        asset = Asset(
            asset_uuid=uuid.uuid4(),
            asset_project_id=test_project.project_id,
            asset_type=AssetTypeEnum.FILE.value,
            asset_name="handbook.pdf",
            asset_size=1024,
            asset_version=1,
            is_latest=True,
        )
        async with db_client() as session:
            async with session.begin():
                session.add(asset)
            await session.commit()

        # List documents
        list_resp = await app_client.get(
            f"/api/v1/data/{test_project.project_uuid}/documents",
            headers=auth_headers
        )
        assert list_resp.status_code == 200
        docs = list_resp.json()["documents"]
        assert len(docs) >= 1
        assert any(d["asset_name"] == "handbook.pdf" for d in docs)

        # Get document details
        detail_resp = await app_client.get(
            f"/api/v1/data/{test_project.project_uuid}/documents/{asset.asset_uuid}",
            headers=auth_headers
        )
        assert detail_resp.status_code == 200
        details = detail_resp.json()
        assert details["asset_name"] == "handbook.pdf"
        assert details["asset_version"] == 1
        assert details["is_latest"] is True

    @pytest.mark.asyncio
    async def test_soft_delete_document(self, app_client, auth_headers, test_project, db_client):
        asset = Asset(
            asset_uuid=uuid.uuid4(),
            asset_project_id=test_project.project_id,
            asset_type=AssetTypeEnum.FILE.value,
            asset_name="to_delete.txt",
            asset_size=512,
            asset_version=1,
            is_latest=True,
        )
        async with db_client() as session:
            async with session.begin():
                session.add(asset)
            await session.commit()

        del_resp = await app_client.delete(
            f"/api/v1/data/{test_project.project_uuid}/documents/{asset.asset_uuid}",
            headers=auth_headers
        )
        assert del_resp.status_code == 200
        assert del_resp.json()["signal"] == "success"

        # Subsequent fetch returns 404
        get_resp = await app_client.get(
            f"/api/v1/data/{test_project.project_uuid}/documents/{asset.asset_uuid}",
            headers=auth_headers
        )
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_reprocess_document(self, app_client, auth_headers, test_project, db_client):
        asset = Asset(
            asset_uuid=uuid.uuid4(),
            asset_project_id=test_project.project_id,
            asset_type=AssetTypeEnum.FILE.value,
            asset_name="reprocess_target.txt",
            asset_size=2048,
            asset_version=1,
            is_latest=True,
        )
        async with db_client() as session:
            async with session.begin():
                session.add(asset)
            await session.commit()

        with patch("routes.data.process_and_push_workflow.delay") as mock_delay:
            mock_delay.return_value = MagicMock(id="reprocess-task-777")
            resp = await app_client.post(
                f"/api/v1/data/{test_project.project_uuid}/documents/{asset.asset_uuid}/reprocess",
                json={"file_name": "reprocess_target.txt", "chunk_size": 100, "chunk_overlap": 20},
                headers=auth_headers,
            )
            assert resp.status_code == 200
            assert resp.json()["task_id"] == "reprocess-task-777"
