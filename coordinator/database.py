"""Coordinator database access.

The coordinator is the component that writes job, task, and result rows.
"""

from __future__ import annotations

from common.db import check_connection, create_db_engine, create_session_factory
from common.models import Job, JobResult, Task, Worker

__all__ = ["check_connection", "create_db_engine", "create_session_factory", "job_detail"]


def job_detail(job: Job, tasks: list[Task], result: JobResult | None) -> dict:
    return {
        "job_id": job.job_id,
        "filename": job.filename,
        "status": job.status,
        "total_rows": job.total_rows,
        "chunk_size": job.chunk_size,
        "chunk_count": job.chunk_count,
        "processing_config": job.processing_config,
        "error_message": job.error_message,
        "tasks": [
            {
                "task_id": task.task_id,
                "chunk_index": task.chunk_index,
                "status": task.status,
                "row_start": task.row_start,
                "row_end": task.row_end,
                "chunk_path": task.chunk_path,
                "attempt_count": task.attempt_count,
                "max_attempts": task.max_attempts,
                "assigned_worker_id": task.assigned_worker_id,
            }
            for task in tasks
        ],
        "results": None
        if result is None
        else {
            "metrics": result.metrics,
            "duration_ms": result.duration_ms,
        },
    }


def worker_detail(worker: Worker) -> dict:
    return {
        "worker_id": worker.worker_id,
        "hostname": worker.hostname,
        "base_url": worker.base_url,
        "status": worker.status,
    }
