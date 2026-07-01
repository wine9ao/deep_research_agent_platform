"""SQLAlchemy ORM models for the Research Platform."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class ResearchTask(Base):
    """Stores research task metadata and results."""

    __tablename__ = "research_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=generate_uuid)
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    research_type: Mapped[str] = mapped_column(String(32), default="综合研究")
    status: Mapped[str] = mapped_column(String(32), default="created")  # created/running/completed/error
    current_step: Mapped[str] = mapped_column(String(64), default="init")
    iteration_count: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100

    # Results
    draft_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_scores: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    chart_specs: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    sources: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    execution_logs: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    use_mock: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    def __repr__(self) -> str:
        return f"<ResearchTask(task_id={self.task_id}, status={self.status})>"


class KnowledgeDocument(Base):
    """Stores uploaded knowledge base documents."""

    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), default="txt")  # txt, md, pdf, csv
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    doc_size: Mapped[int] = mapped_column(Integer, default=0)  # bytes
    chunk_count: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    def __repr__(self) -> str:
        return f"<KnowledgeDocument(title={self.title}, type={self.file_type})>"


class UserMemory(Base):
    """Stores user preferences and historical research context."""

    __tablename__ = "user_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    memory_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(64), default="default")
    memory_type: Mapped[str] = mapped_column(String(32), default="preference")  # preference/history/feedback
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    def __repr__(self) -> str:
        return f"<UserMemory(key={self.key}, type={self.memory_type})>"
