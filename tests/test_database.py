"""Schema and connection tests that do not use the live Galera cluster."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from common.db import check_connection
from common.models import Base, Job, JobResult, Task, TaskResult, Worker


def _sqlite_session() -> Session:
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return Session(engine)


def test_check_connection_accepts_sqlite() -> None:
    assert check_connection("sqlite://") is True


def test_tables_store_metadata_without_a_second_task_result() -> None:
    session = _sqlite_session()
    worker = Worker(
        worker_id="node01-worker",
        hostname="node01",
        base_url="http://10.10.10.10:8001",
        status="ONLINE",
    )
    job = Job(
        job_id=str(uuid4()),
        filename="flights.csv",
        status="PENDING",
        total_rows=2,
        chunk_size=1000,
        chunk_count=1,
        processing_config={"numeric_columns": ["departure_delay"]},
    )
    task = Task(
        task_id=str(uuid4()),
        job_id=job.job_id,
        chunk_index=0,
        status="COMPLETED",
        assigned_worker_id=worker.worker_id,
        attempt_count=1,
        max_attempts=3,
        row_start=0,
        row_end=2,
        chunk_path="data/chunks/job/task.csv",
    )
    session.add_all([worker, job])
    session.commit()
    session.add(task)
    session.commit()

    session.add(
        TaskResult(
            result_id=str(uuid4()),
            task_id=task.task_id,
            worker_id=worker.worker_id,
            attempt_number=1,
            metrics={"sum": 15, "valid_count": 2},
            duration_ms=20,
        )
    )
    session.add(
        JobResult(
            job_id=job.job_id,
            metrics={"sum": 15, "valid_count": 2, "average": 7.5},
            duration_ms=20,
        )
    )
    session.commit()

    duplicate = TaskResult(
        result_id=str(uuid4()),
        task_id=task.task_id,
        worker_id=worker.worker_id,
        attempt_number=2,
        metrics={"sum": 15, "valid_count": 2},
        duration_ms=25,
    )
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        session.commit()
