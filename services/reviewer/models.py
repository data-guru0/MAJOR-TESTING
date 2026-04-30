import uuid
from typing import Any
from sqlalchemy import BigInteger, Column, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP
from pydantic import BaseModel
from pydantic_settings import BaseSettings

Base = declarative_base()


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_full_name = Column(Text, nullable=False)
    pr_number = Column(Integer, nullable=False)
    head_sha = Column(Text, nullable=False)
    installation_id = Column(BigInteger, nullable=False)
    status = Column(Text, nullable=False, default="pending")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class ReviewRequest(BaseModel):
    pr_id: uuid.UUID
    repo_full_name: str
    pr_number: int
    installation_id: int
    findings: list[dict[str, Any]]


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:password@postgres:5432/codereviewer"
    github_app_id: str = ""
    github_app_private_key: str = ""

    class Config:
        env_file = ".env"
