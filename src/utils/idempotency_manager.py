from re import I
from alembic.util import status
import hashlib
import json
from sqlalchemy import select, delete, func
from datetime import datetime, timezone, timedelta

from models import CeleryTaskExecution



class IdempotencyManager:
    def __init__(self, db_client, db_engine):
        self.db_client = db_client
        self.db_engine = db_engine

    def create_args_hash(self, task_name: str, task_args: dict):

        combined_data ={
            **task_args,
            'task_name': task_name
        }

        json_string = json.dumps(combined_data, sort_keys=True, default=str)

        return hashlib.sha256(json_string.encode()).hexdigest()



    async def create_task_record(self, task_name: str, task_args: dict, celery_task_id: str = None) -> CeleryTaskExecution:

        """Create new task execution record."""
        args_hash = self.create_args_hash(task_name, task_args)

        task_record = CeleryTaskExecution(
        task_name=task_name,
        task_arg_hash=args_hash,
        task_args=task_args,
        celery_task_id=celery_task_id,
        status='PENDING',
        started_at=func.now()
        )

        async with self.db_client() as session:
            async with session.begin():
                session.add(task_record)
            await session.commit()
            await session.refresh(task_record)
        return task_record



    async def update_task_status(self, execution_id: int, status: str, result: dict = None):
        """Update task status and result. """
        async with self.db_client() as session:
            async with session.begin():
                task_record = await session.get(CeleryTaskExecution, execution_id)
                if task_record:
                    task_record.status = status
                    if result:
                        task_record.result = result
                    if status in ['SUCCESS', 'FAILURE' ]:
                        task_record.completed_at = func.now()
                await session.commit()




    async def get_existing_task(self, task_name: str, task_args: dict, celery_task_id: str) -> CeleryTaskExecution:
        """Check if task with same name and args already exists. """
        args_hash = self.create_args_hash(task_name, task_args)

        async with self.db_client() as session:
            query = select(CeleryTaskExecution).where(
                CeleryTaskExecution.task_name == task_name,
                CeleryTaskExecution.task_arg_hash == args_hash,
                CeleryTaskExecution.celery_task_id == celery_task_id
            )

            result = await session.execute(query)
            return result.scalar_one_or_none()



    async def should_execute_task(self, task_name: str, task_args: dict, celery_task_id: str, task_time_limit: int = 300) -> tuple[bool, CeleryTaskExecution]:
        """Check if task should be executed or return existing result.
        Args:
            task_time_limit: Time limit in seconds after which a stuck task can be re-executed
        Returns (should_execute, existing_task_or_none)
        """

        existing_task = await self.get_existing_task(task_name, task_args, celery_task_id)

        if not existing_task:
            return True, None

        # Don't execute if task is already completed successfully
        if existing_task.status == 'SUCCESS':
            return False, existing_task

        # Check if task is stuck (running longer than time limit + 20 seconds)
        if existing_task.status in ['PENDING', 'STARTED', 'RETRY']:
            if existing_task.started_at:
                time_elapsed = (func.now() - existing_task.started_at).total_seconds()
                time_gap = 20 # 20 seconds grace period
                if time_elapsed > (task_time_limit + time_gap):
                    return True, existing_task # Task is stuck, allow re-execution
            return False, existing_task # Task is still running within time limit

        # Re-execute if previous task failed
        return True, existing_task


    async def clean_old_tasks(self, time_retention: int = 86400):
        """
        Delete old task records older than time_retention seconds.
        Args:
            time_retention: Time retention in seconds (default: 86400 => 1 day)
        Returns:
            Number of deleted records
        """

        cutoff_date = func.now() - timedelta(seconds=time_retention)

        async with self.db_client() as session:
            async with session.begin():
                statement = delete(CeleryTaskExecution).where(
                    CeleryTaskExecution.created_at < cutoff_date
                )
                result = await session.execute(statement)
                await session.commit()
        return result.rowcount