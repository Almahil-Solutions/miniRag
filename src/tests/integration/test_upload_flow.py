import io
from unittest.mock import patch, MagicMock
import pytest
from models import ResponceSignal


class TestUploadFlowIntegration:
    @pytest.mark.asyncio
    async def test_upload_unauthenticated_rejected(self, app_client, test_project):
        pdf_content = b"%PDF-1.4\n%test content\n" + b"\x00" * 50
        response = await app_client.post(
            f"/api/v1/data/upload/{test_project.project_uuid}",
            files={"file": ("doc.pdf", io.BytesIO(pdf_content), "application/pdf")},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_authenticated_success(self, app_client, auth_headers, test_project):
        txt_content = b"This is valid knowledge base content about miniRAG architecture."
        response = await app_client.post(
            f"/api/v1/data/upload/{test_project.project_uuid}",
            files={"file": ("architecture.txt", io.BytesIO(txt_content), "text/plain")},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["result_signal"] == ResponceSignal.FILE_UPLOADED_SUCCESSFULLY.value
        assert "asset_uuid" in data
        assert "asset_id" in data
        assert data["asset_version"] == 1
        assert data["is_latest"] is True

    @pytest.mark.asyncio
    async def test_upload_spoofed_file_rejected(self, app_client, auth_headers, test_project):
        exe_content = b"MZ" + b"\x00" * 300  # Spoofed exe
        response = await app_client.post(
            f"/api/v1/data/upload/{test_project.project_uuid}",
            files={"file": ("trojan.pdf", io.BytesIO(exe_content), "application/pdf")},
            headers=auth_headers,
        )
        assert response.status_code == 400
        data = response.json()
        assert data["result_signal"] == ResponceSignal.FILE_TYPE_NOT_SUPPORTED.value

    @pytest.mark.asyncio
    async def test_process_file_endpoint_authenticated(self, app_client, auth_headers, test_project):
        with patch("routes.data.process_project_files.delay") as mock_delay:
            mock_delay.return_value = MagicMock(id="mock-celery-task-id-123")
            response = await app_client.post(
                f"/api/v1/data/process/{test_project.project_uuid}",
                json={
                    "file_name": "architecture.txt",
                    "chunk_size": 100,
                    "chunk_overlap": 20,
                    "do_reset": False,
                },
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["result_signal"] == ResponceSignal.FILE_PROCESSING_SUCCESSFULL.value
            assert data["task_id"] == "mock-celery-task-id-123"
            mock_delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_and_push_workflow_endpoint(self, app_client, auth_headers, test_project):
        with patch("routes.data.process_and_push_workflow.delay") as mock_delay:
            mock_delay.return_value = MagicMock(id="mock-workflow-task-id-456")
            response = await app_client.post(
                f"/api/v1/data/process-and-push/{test_project.project_uuid}",
                json={
                    "file_name": "architecture.txt",
                    "chunk_size": 100,
                    "chunk_overlap": 20,
                    "do_reset": False,
                },
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["result_signal"] == ResponceSignal.PROCEDD_AND_PUSH_WORKFLOW_READY.value
            assert data["workflow_id"] == "mock-workflow-task-id-456"
            mock_delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_vector_index_endpoint(self, app_client, auth_headers, test_project):
        with patch("routes.nlp.index_project_data.delay") as mock_delay:
            mock_delay.return_value = MagicMock(id="mock-indexing-task-id-789")
            response = await app_client.post(
                f"/api/v1/nlp/index/push/{test_project.project_uuid}",
                json={"do_reset": False},
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["signal"] == ResponceSignal.DATA_PUSH_TASK_READY.value
            assert data["task_id"] == "mock-indexing-task-id-789"
            mock_delay.assert_called_once()
