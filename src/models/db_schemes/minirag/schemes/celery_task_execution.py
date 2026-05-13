from .minirag_base import SQLAlchemyBase
from sqlalchemy import Column, String, Integer, DateTime, func, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid


class CeleryTaskExecution(SQLAlchemyBase):
    __tablename__ = "celery_task_execution"

    execution_id = Column(Integer, primary_key=True, autoincrement=True)

    task_name = Column(String(255), nullable=False)
    task_arg_hash = Column(String(64), nullable=False) # SHA-256 hash of the task arguments
    celery_task_id = Column(UUID(as_uuid=True), nullable=True)

    status = Column(String(50), nullable=False, default="PENDING")

    task_args = Column(JSONB, nullable=True)
    result = Column(JSONB, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_task_name_args_hash_celery_task_id", task_name, task_arg_hash, celery_task_id, unique=True),
        Index("idx_celery_task_execution_status", status),
        Index("idx_celery_task_execution_created_at", created_at),
        Index("idx_celery_task_id", celery_task_id),
    )

    

