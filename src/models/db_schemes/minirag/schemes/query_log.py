from .minirag_base import SQLAlchemyBase
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid


class QueryLog(SQLAlchemyBase):
    __tablename__ = "query_logs"
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=True, index=True)
    endpoint = Column(String, nullable=False)
    query_text = Column(String, nullable=True)
    result_summary = Column(JSONB, nullable=True)
    status = Column(String, nullable=False)
    latency_ms = Column(Integer, nullable=True)
    ip_address = Column(String, nullable=True)
    request_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", back_populates="query_logs")
