"""SQLAlchemy models for distributed_processing.

database/schema.sql is the definition applied to MariaDB. These models match
that definition so tests can create the same tables on SQLite.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class Worker(Base):
    __tablename__ = "workers"

    worker_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    hostname: Mapped[str] = mapped_column(String(255))
    base_url: Mapped[str] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="OFFLINE")
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now()
    )


class Job(Base):
    __tablename__ = "jobs"

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    total_rows: Mapped[int] = mapped_column(default=0)
    chunk_size: Mapped[int]
    chunk_count: Mapped[int] = mapped_column(default=0)
    processing_config: Mapped[dict] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (UniqueConstraint("job_id", "chunk_index", name="uq_tasks_job_chunk"),)

    task_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.job_id"))
    chunk_index: Mapped[int]
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    assigned_worker_id: Mapped[str | None] = mapped_column(ForeignKey("workers.worker_id"))
    attempt_count: Mapped[int] = mapped_column(default=0)
    max_attempts: Mapped[int] = mapped_column(default=3)
    row_start: Mapped[int]
    row_end: Mapped[int]
    chunk_path: Mapped[str] = mapped_column(String(512))
    error_message: Mapped[str | None] = mapped_column(String(2000))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now()
    )


class TaskResult(Base):
    __tablename__ = "task_results"

    result_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), unique=True)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.worker_id"))
    attempt_number: Mapped[int]
    metrics: Mapped[dict] = mapped_column(JSON)
    duration_ms: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )


class JobResult(Base):
    __tablename__ = "job_results"

    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.job_id"), primary_key=True)
    metrics: Mapped[dict] = mapped_column(JSON)
    duration_ms: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )
