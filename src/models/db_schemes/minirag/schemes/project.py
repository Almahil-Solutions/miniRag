from .minirag_base import SQLAlchemyBase
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid


class Project(SQLAlchemyBase):
    __tablename__ = "projects"
    project_id = Column(Integer, primary_key=True, autoincrement=True)
    project_uuid = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4, unique=True)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    owner = relationship("User", back_populates="projects")
    assets = relationship("Asset", back_populates="project", cascade="all, delete-orphan")
    chunks = relationship("DataChunk", back_populates="project", cascade="all, delete-orphan")