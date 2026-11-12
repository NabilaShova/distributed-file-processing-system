"""Dispatch pending tasks to registered workers and store one job result."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from sqlalchemy import select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from common.models import Job, JobResult, Task, TaskResult, Worker
from common.schemas import COMPLETED, FAILED, PENDING, RUNNING
from coordinator.aggregator import aggregate_task_metrics
from coordinator.database import job_detail

ONLINE = "ONLINE"


class JobNotFound(LookupError):
    """The requested job is not in the database."""


class NoWorkers(RuntimeError):
    """No online worker is registered."""


def execute_job(engine: Engine, chunks_dir: Path, job_id: str, timeout_seconds: int) -> dict:
    """Run every pending task for a job. Completed tasks are not sent again."""
    started = datetime.now(timezone.utc)
    db_lock = threading.Lock() if engine.dialect.name == "sqlite" else nullcontext()
    workers = _online_workers(engine, db_lock, job_id)
    assignments = _claim_tasks(engine, db_lock, job_id, workers, timeout_seconds)
    if assignments:
        with ThreadPoolExecutor(max_workers=len(workers)) as pool:
            list(
                pool.map(
                    lambda item: _dispatch(engine, db_lock, chunks_dir, item, timeout_seconds),
                    assignments,
                )
            )
    return _finish(engine, db_lock, job_id, started)


def register_worker(engine: Engine, worker_id: str, hostname: str, base_url: str) -> dict:
    now = _utcnow()
    with Session(engine) as session, session.begin():
        worker = session.get(Worker, worker_id)
        if worker is None:
            worker = Worker(
                worker_id=worker_id,
                hostname=hostname,
                base_url=base_url.rstrip("/"),
                status=ONLINE,
                last_heartbeat=now,
            )
            session.add(worker)
        else:
            worker.hostname = hostname
            worker.base_url = base_url.rstrip("/")
            worker.status = ONLINE
            worker.last_heartbeat = now
        session.flush()
        return {
            "worker_id": worker.worker_id,
            "hostname": worker.hostname,
            "base_url": worker.base_url,
            "status": worker.status,
        }


def _online_workers(engine: Engine, db_lock, job_id: str) -> list[dict]:
    with db_lock, Session(engine) as session:
        job = session.get(Job, job_id)
        if job is None:
            raise JobNotFound(job_id)
        query = select(Worker).where(Worker.status == ONLINE).order_by(Worker.worker_id)
        rows = session.scalars(query)
        workers = [{"worker_id": row.worker_id, "base_url": row.base_url} for row in rows]
        if not workers:
            raise NoWorkers(job_id)
        job.status = RUNNING
        if job.started_at is None:
            job.started_at = _utcnow()
        session.commit()
        return workers


def _claim_tasks(
    engine,
    db_lock,
    job_id: str,
    workers: list[dict],
    timeout_seconds: int,
) -> list[dict]:
    with db_lock, Session(engine) as session:
        pending = (
            select(Task)
            .where(Task.job_id == job_id, Task.status == PENDING)
            .order_by(Task.chunk_index)
        )
        tasks = list(session.scalars(pending))
        processing_config = session.get(Job, job_id).processing_config
        assignments = []
        now = _utcnow()
        for index, task in enumerate(tasks):
            worker = workers[index % len(workers)]
            claimed = session.execute(
                update(Task)
                .where(Task.task_id == task.task_id, Task.status == PENDING)
                .values(
                    status=RUNNING,
                    assigned_worker_id=worker["worker_id"],
                    attempt_count=Task.attempt_count + 1,
                    started_at=now,
                    lease_expires_at=now + timedelta(seconds=timeout_seconds),
                )
            )
            if claimed.rowcount != 1:
                continue
            assignments.append(
                {
                    "task_id": task.task_id,
                    "chunk_path": task.chunk_path,
                    "attempt_number": task.attempt_count + 1,
                    "worker_id": worker["worker_id"],
                    "base_url": worker["base_url"],
                    "processing_config": processing_config,
                }
            )
        session.commit()
        return assignments


def _dispatch(engine, db_lock, chunks_dir: Path, assignment: dict, timeout_seconds: int) -> None:
    path = chunks_dir / assignment["chunk_path"]
    try:
        response = requests.post(
            f"{assignment['base_url']}/process",
            json={
                "task_id": assignment["task_id"],
                "attempt_number": assignment["attempt_number"],
                "csv_text": path.read_text(encoding="utf-8"),
                "processing_config": assignment["processing_config"],
            },
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
    except (OSError, requests.RequestException, ValueError) as exc:
        _mark_failed(engine, db_lock, assignment, str(exc))
        return
    _mark_completed(engine, db_lock, assignment, body)


def _mark_completed(engine, db_lock, assignment: dict, body: dict) -> None:
    metrics = {
        "total_rows": body["total_rows"],
        "columns": body["columns"],
        "condition_count": body.get("condition_count"),
    }
    now = _utcnow()
    try:
        with db_lock, Session(engine) as session, session.begin():
            changed = session.execute(
                update(Task)
                .where(
                    Task.task_id == assignment["task_id"],
                    Task.status == RUNNING,
                    Task.assigned_worker_id == assignment["worker_id"],
                )
                .values(status=COMPLETED, finished_at=now, error_message=None)
            )
            if changed.rowcount != 1:
                return
            session.add(
                TaskResult(
                    result_id=f"{assignment['task_id']}-result",
                    task_id=assignment["task_id"],
                    worker_id=assignment["worker_id"],
                    attempt_number=assignment["attempt_number"],
                    metrics=metrics,
                    duration_ms=int(body.get("duration_ms") or 0),
                )
            )
    except IntegrityError:
        return


def _mark_failed(engine, db_lock, assignment: dict, message: str) -> None:
    with db_lock, Session(engine) as session, session.begin():
        session.execute(
            update(Task)
            .where(
                Task.task_id == assignment["task_id"],
                Task.status == RUNNING,
                Task.assigned_worker_id == assignment["worker_id"],
            )
            .values(status=FAILED, finished_at=_utcnow(), error_message=message[:2000])
        )


def _finish(engine, db_lock, job_id: str, started: datetime) -> dict:
    with db_lock, Session(engine) as session, session.begin():
        job = session.get(Job, job_id)
        task_query = select(Task).where(Task.job_id == job_id).order_by(Task.chunk_index)
        tasks = list(session.scalars(task_query))
        if any(task.status == FAILED for task in tasks):
            job.status = FAILED
            job.finished_at = _utcnow()
            job.error_message = "One or more tasks failed."
            return job_detail(job, tasks, session.get(JobResult, job_id))
        if tasks and all(task.status == COMPLETED for task in tasks):
            task_ids = [task.task_id for task in tasks]
            result_query = select(TaskResult).where(TaskResult.task_id.in_(task_ids))
            stored = list(session.scalars(result_query))
            metrics = aggregate_task_metrics([item.metrics for item in stored])
            elapsed = datetime.now(timezone.utc) - started
            result = session.get(JobResult, job_id)
            if result is None:
                duration_ms = int(elapsed.total_seconds() * 1000)
                result = JobResult(job_id=job_id, metrics=metrics, duration_ms=duration_ms)
                session.add(result)
            else:
                result.metrics = metrics
                result.duration_ms = int(elapsed.total_seconds() * 1000)
            job.status = COMPLETED
            job.finished_at = _utcnow()
            job.error_message = None
            session.flush()
            return job_detail(job, tasks, result)
        return job_detail(job, tasks, session.get(JobResult, job_id))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
