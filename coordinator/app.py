"""Coordinator HTTP entry point."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, request
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from werkzeug.utils import secure_filename

from common.logging_config import configure_logging
from common.models import Job, JobResult, Task, Worker
from common.schemas import PENDING
from coordinator.config import CoordinatorConfig
from coordinator.database import create_db_engine, job_detail, worker_detail
from coordinator.partitioner import (
    DatasetError,
    parse_processing_config,
    partition_frame,
    read_dataset,
    validate_dataset,
    write_chunks,
)
from coordinator.scheduler import JobNotFound, NoWorkers, execute_job, register_worker

logger = logging.getLogger(__name__)
MAX_CSV_BYTES = 50 * 1024 * 1024


def create_app(config: CoordinatorConfig | None = None, engine: Engine | None = None) -> Flask:
    settings = config or CoordinatorConfig.from_env()
    configure_logging(settings.log_level)
    app = Flask(__name__)
    app.config["COORDINATOR_CONFIG"] = settings
    database_engine = engine or create_db_engine(settings.database_url)
    sessions = sessionmaker(bind=database_engine, expire_on_commit=False)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "role": "coordinator"})

    @app.post("/jobs")
    def create_job():
        try:
            filename, csv_text, processing_config, chunk_size = _read_upload(settings.chunk_size)
            frame = read_dataset(csv_text)
            validate_dataset(frame, processing_config)
            chunks = partition_frame(frame, chunk_size)
        except DatasetError as exc:
            return jsonify({"error": str(exc)}), 400

        job_id = str(uuid4())
        written: list[dict] = []
        try:
            written = write_chunks(Path(settings.chunks_dir), job_id, chunks)
            with Session(database_engine) as session:
                session.add(
                    Job(
                        job_id=job_id,
                        filename=filename,
                        status=PENDING,
                        total_rows=int(len(frame)),
                        chunk_size=chunk_size,
                        chunk_count=len(written),
                        processing_config=processing_config,
                    )
                )
                session.add_all(
                    Task(
                        task_id=item["task_id"],
                        job_id=job_id,
                        chunk_index=item["chunk_index"],
                        status=PENDING,
                        attempt_count=0,
                        max_attempts=3,
                        row_start=item["row_start"],
                        row_end=item["row_end"],
                        chunk_path=item["chunk_path"],
                    )
                    for item in written
                )
                session.commit()
                job = session.get(Job, job_id)
                tasks = list(
                    session.scalars(
                        select(Task).where(Task.job_id == job_id).order_by(Task.chunk_index)
                    )
                )
                body = job_detail(job, tasks, None)
        except SQLAlchemyError:
            _remove_chunks(Path(settings.chunks_dir), written)
            logger.exception("Could not store job %s", job_id)
            return jsonify({"error": "The job could not be stored."}), 500
        logger.info("Created job %s with %s tasks", job_id, len(written))
        return jsonify(body), 201

    @app.get("/jobs")
    def list_jobs():
        with sessions() as session:
            jobs = session.scalars(select(Job).order_by(Job.created_at.desc())).all()
            return jsonify(
                [
                    {
                        "job_id": job.job_id,
                        "filename": job.filename,
                        "status": job.status,
                        "total_rows": job.total_rows,
                        "chunk_count": job.chunk_count,
                    }
                    for job in jobs
                ]
            )

    @app.get("/jobs/<job_id>")
    def get_job(job_id: str):
        with sessions() as session:
            job = session.get(Job, job_id)
            if job is None:
                return jsonify({"error": "Job not found."}), 404
            task_query = select(Task).where(Task.job_id == job_id).order_by(Task.chunk_index)
            tasks = list(session.scalars(task_query))
            return jsonify(job_detail(job, tasks, session.get(JobResult, job_id)))

    @app.get("/jobs/<job_id>/results")
    def get_results(job_id: str):
        with sessions() as session:
            job = session.get(Job, job_id)
            if job is None:
                return jsonify({"error": "Job not found."}), 404
            result = session.get(JobResult, job_id)
            return jsonify(
                {
                    "job_id": job.job_id,
                    "status": job.status,
                    "results": None
                    if result is None
                    else {"metrics": result.metrics, "duration_ms": result.duration_ms},
                }
            )

    @app.get("/workers")
    def list_workers():
        with sessions() as session:
            workers = session.scalars(select(Worker).order_by(Worker.worker_id)).all()
            return jsonify([worker_detail(worker) for worker in workers])

    @app.get("/workers/<worker_id>")
    def get_worker(worker_id: str):
        with sessions() as session:
            worker = session.get(Worker, worker_id)
            if worker is None:
                return jsonify({"error": "Worker not found."}), 404
            return jsonify(worker_detail(worker))

    @app.post("/workers")
    def add_worker():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Request body must be JSON."}), 400
        worker_id = payload.get("worker_id")
        hostname = payload.get("hostname")
        base_url = payload.get("base_url")
        names = (worker_id, hostname, base_url)
        if not all(isinstance(value, str) and value.strip() for value in names):
            return jsonify({"error": "worker_id, hostname, and base_url are required."}), 400
        try:
            return jsonify(register_worker(database_engine, worker_id, hostname, base_url)), 201
        except SQLAlchemyError:
            logger.exception("Could not register worker")
            return jsonify({"error": "The worker could not be stored."}), 500

    @app.post("/jobs/<job_id>/run")
    def run_job(job_id: str):
        try:
            body = execute_job(
                database_engine,
                Path(settings.chunks_dir),
                job_id,
                settings.request_timeout,
            )
        except JobNotFound:
            return jsonify({"error": "Job not found."}), 404
        except NoWorkers:
            return jsonify({"error": "No online worker is registered."}), 409
        except SQLAlchemyError:
            logger.exception("Could not run job %s", job_id)
            return jsonify({"error": "The job could not be run."}), 500
        return jsonify(body)

    return app


def _read_upload(default_chunk_size: int) -> tuple[str, str, dict, int]:
    if request.is_json:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            raise DatasetError("Request body must be JSON.")
        filename = _csv_filename(str(payload.get("filename") or "upload.csv"))
        processing_config = parse_processing_config(payload.get("processing_config"))
        chunk_size = _chunk_size(payload.get("chunk_size"), default_chunk_size)
        csv_text = payload.get("csv_text")
        if not isinstance(csv_text, str):
            raise DatasetError("csv_text is required.")
        if len(csv_text.encode("utf-8")) > MAX_CSV_BYTES:
            raise DatasetError("The CSV exceeds the 50 MB upload limit.")
        return filename, csv_text, processing_config, chunk_size

    upload = request.files.get("file")
    if upload is None or not upload.filename:
        raise DatasetError("A CSV file upload is required.")
    filename = _csv_filename(upload.filename)
    raw_bytes = upload.read(MAX_CSV_BYTES + 1)
    if len(raw_bytes) > MAX_CSV_BYTES:
        raise DatasetError("The CSV exceeds the 50 MB upload limit.")
    processing_config = parse_processing_config(request.form.get("processing_config"))
    chunk_size = _chunk_size(request.form.get("chunk_size"), default_chunk_size)
    return filename, raw_bytes.decode("utf-8-sig"), processing_config, chunk_size


def _csv_filename(filename: str) -> str:
    cleaned = secure_filename(filename)
    if not cleaned.lower().endswith(".csv"):
        raise DatasetError("Upload must be a .csv file.")
    return cleaned


def _chunk_size(raw: object, default: int) -> int:
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise DatasetError("chunk_size must be an integer.") from exc
    if value < 1:
        raise DatasetError("chunk_size must be at least 1.")
    return value


def _remove_chunks(chunks_dir: Path, written: list[dict]) -> None:
    for item in written:
        (chunks_dir / item["chunk_path"]).unlink(missing_ok=True)


def main() -> None:
    settings = CoordinatorConfig.from_env()
    app = create_app(settings)
    app.run(host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
