import uuid
from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP
from pydantic import BaseModel
from pydantic_settings import BaseSettings

Base = declarative_base()


class Finding(Base):
    __tablename__ = "findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pr_id = Column(UUID(as_uuid=True), ForeignKey("pull_requests.id"), nullable=True)
    file = Column(Text, nullable=True)
    line = Column(Integer, nullable=True)
    severity = Column(Text, nullable=True)
    message = Column(Text, nullable=True)
    agent = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class Pattern(Base):
    __tablename__ = "patterns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_full_name = Column(Text, nullable=False)
    pattern_text = Column(Text, nullable=False)
    frequency = Column(Integer, default=1)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class LearnRequest(BaseModel):
    repo_full_name: str
    pr_id: uuid.UUID


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:password@postgres:5432/codereviewer"
    redis_url: str = "redis://redis:6379/0"

    class Config:
        env_file = ".env"
