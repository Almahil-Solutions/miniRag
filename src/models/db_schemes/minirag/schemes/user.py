from .minirag_base import SQLAlchemyBase
from sqlalchemy import Column, String, Boolean, DateTime, Float, func, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class User(SQLAlchemyBase):
    __tablename__ = "users"
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.MEMBER)
    is_active = Column(Boolean, nullable=False, default=True)
    plan = Column(String, nullable=False, default="free")
    monthly_llm_budget = Column(Float, nullable=True, default=100.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    projects = relationship("Project", back_populates="owner")
    api_keys = relationship("ApiKey", back_populates="user")
    query_logs = relationship("QueryLog", back_populates="user")
