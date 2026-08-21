import pytest
import uuid
from datetime import datetime, timezone, timedelta
from utils.idempotency_manager import IdempotencyManager


class TestIdempotencyManagerUnit:
    @pytest.fixture
    def manager(self, db_client, db_engine):
        return IdempotencyManager(db_client=db_client, db_engine=db_engine)

    def test_create_args_hash_deterministic(self, manager):
        """SHA-256 args hash is identical regardless of dict key order."""
        args_1 = {"chunk_size": 100, "do_reset": False, "file_name": "data.txt"}
        args_2 = {"file_name": "data.txt", "do_reset": False, "chunk_size": 100}

        hash_1 = manager.create_args_hash("task_name", args_1)
        hash_2 = manager.create_args_hash("task_name", args_2)

        assert hash_1 == hash_2
        assert len(hash_1) == 64  # SHA-256 hex string

    @pytest.mark.asyncio
    async def test_create_and_get_task_record(self, manager):
        task_id = uuid.uuid4()
        task_args = {"project_id": 10, "file": "doc.pdf"}

        rec = await manager.create_task_record("index_data", task_args, celery_task_id=task_id)
        assert rec.execution_id is not None
        assert rec.status == "PENDING"
        assert rec.task_name == "index_data"

        fetched = await manager.get_existing_task("index_data", task_args, celery_task_id=task_id)
        assert fetched is not None
        assert fetched.execution_id == rec.execution_id

    @pytest.mark.asyncio
    async def test_should_execute_new_task(self, manager):
        """Non-existent task should always execute."""
        task_id = uuid.uuid4()
        should_run, existing = await manager.should_execute_task(
            "unknown_task", {"a": 1}, celery_task_id=task_id
        )
        assert should_run is True
        assert existing is None

    @pytest.mark.asyncio
    async def test_should_not_execute_completed_task(self, manager):
        """Completed (SUCCESS) task should not be re-executed."""
        task_id = uuid.uuid4()
        task_args = {"target": "indexing"}

        rec = await manager.create_task_record("success_task", task_args, celery_task_id=task_id)
        await manager.update_task_status(rec.execution_id, "SUCCESS", result={"vectors": 50})

        should_run, existing = await manager.should_execute_task(
            "success_task", task_args, celery_task_id=task_id
        )
        assert should_run is False
        assert existing.status == "SUCCESS"

    @pytest.mark.asyncio
    async def test_should_not_execute_active_task_within_time_limit(self, manager):
        """Running task within time limit should not be re-executed."""
        task_id = uuid.uuid4()
        task_args = {"target": "active_run"}

        rec = await manager.create_task_record("running_task", task_args, celery_task_id=task_id)
        # Update started_at to now
        async with manager.db_client() as session:
            async with session.begin():
                merged = await session.get(type(rec), rec.execution_id)
                merged.started_at = datetime.now(timezone.utc)
            await session.commit()

        should_run, existing = await manager.should_execute_task(
            "running_task", task_args, celery_task_id=task_id, task_time_limit=600
        )
        assert should_run is False

    @pytest.mark.asyncio
    async def test_allows_reexecution_for_stuck_task(self, manager):
        """Stuck task running longer than time limit + 20s should allow re-execution."""
        task_id = uuid.uuid4()
        task_args = {"target": "stuck_run"}

        rec = await manager.create_task_record("stuck_task", task_args, celery_task_id=task_id)
        # Update started_at to 2 hours ago
        stuck_time = datetime.now(timezone.utc) - timedelta(hours=2)
        async with manager.db_client() as session:
            async with session.begin():
                merged = await session.get(type(rec), rec.execution_id)
                merged.started_at = stuck_time
            await session.commit()

        should_run, existing = await manager.should_execute_task(
            "stuck_task", task_args, celery_task_id=task_id, task_time_limit=600
        )
        assert should_run is True

    @pytest.mark.asyncio
    async def test_allows_reexecution_for_failed_task(self, manager):
        """Failed task should allow re-execution."""
        task_id = uuid.uuid4()
        task_args = {"target": "failed_run"}

        rec = await manager.create_task_record("failed_task", task_args, celery_task_id=task_id)
        await manager.update_task_status(rec.execution_id, "FAILURE", result={"error": "OOM"})

        should_run, existing = await manager.should_execute_task(
            "failed_task", task_args, celery_task_id=task_id
        )
        assert should_run is True

    @pytest.mark.asyncio
    async def test_clean_old_tasks(self, manager):
        """clean_old_tasks deletes expired records beyond time_retention."""
        task_id = uuid.uuid4()
        rec = await manager.create_task_record("old_task", {"p": 1}, celery_task_id=task_id)

        # Set created_at to 3 days ago
        old_time = datetime.now(timezone.utc) - timedelta(days=3)
        async with manager.db_client() as session:
            async with session.begin():
                merged = await session.get(type(rec), rec.execution_id)
                merged.created_at = old_time
            await session.commit()

        deleted_count = await manager.clean_old_tasks(time_retention=86400)
        assert deleted_count >= 1
