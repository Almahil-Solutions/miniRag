from .minirag_base import SQLAlchemyBase
from sqlalchemy import Column, String, Integer, DateTime, Boolean, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy import Index
import uuid


class Asset(SQLAlchemyBase):
    __tablename__ = "assets"
    asset_id = Column(Integer, primary_key=True, autoincrement=True)
    asset_uuid = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4, unique=True)

    asset_type = Column(String, nullable=False)
    asset_name = Column(String, nullable=False)
    asset_size = Column(Integer, nullable=True)
    asset_config = Column(JSONB, nullable=True)

    # Document versioning
    asset_version = Column(Integer, nullable=False, default=1)
    is_latest = Column(Boolean, nullable=False, default=True)

    asset_project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False)

    project = relationship("Project", back_populates="assets")
    chunks = relationship("DataChunk", back_populates="asset")

    __table_args__ = (
        Index('ix_asset_project_id', asset_project_id),
        Index('ix_asset_type', asset_type),
        Index('ix_asset_is_latest', is_latest),
        Index('ix_asset_project_name_version', asset_project_id, asset_name, asset_version),
    )

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())