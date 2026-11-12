"""Dispatch tests with one, two, and three local workers."""

import threading

import pytest
import requests
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from werkzeug.serving import make_server

from common.models import Base, Task
from common.schemas import TASK_STATUSES
from coordinator.app import create_app
from coordinator.config import CoordinatorConfig
from worker.app import create_app as create_worker_app
from worker.config import WorkerConfig

CSV = "delay\n10\n0\n30\n"


class _WorkerServer:
    def __init__(self, worker_id: str) -> None:
        config = WorkerConfig(
            host="127.0.0.1",
            port=0,
            worker_id=worker_id,
            log_level="ERROR",
            database_url="sqlite://",
        )
        app = create_worker_app(config, connection_check=lambda _url: True)
        self.server = make_server("127.0.0.1", 0, app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def stop(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=5)


def _engine():
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
    return engine


def _coordinator(tmp_path, engine):
    config = CoordinatorConfig(
        host="127.0.0.1",
        port=8000,
        log_level="ERROR",
        chunk_size=2,
        database_url="sqlite://",
        chunks_dir=str(tmp_path),
        request_timeout=10,
    )
    return create_app(config, engine=engine).test_client()


def _wait_until_ready(url: str) -> None:
    last_error = None
    for _ in range(50):
        try:
            if requests.get(f"{url}/health", timeout=1).status_code == 200:
                return
        except requests.RequestException as exc:
            last_error = exc
    raise AssertionError(f"Worker did not start: {last_error}")


def _run_with_workers(tmp_path, worker_count: int):
    engine = _engine()
    client = _coordinator(tmp_path, engine)
    servers = [_WorkerServer(f"worker-{index}") for index in range(worker_count)]
    try:
        for index, server in enumerate(servers):
            _wait_until_ready(server.url)
            registered = client.post(
                "/workers",
                json={
                    "worker_id": f"worker-{index}",
                    "hostname": f"host-{index}",
                    "base_url": server.url,
                },
            )
            assert registered.status_code == 201
        created = client.post(
            "/jobs",
            json={
                "filename": "delays.csv",
                "csv_text": CSV,
                "chunk_size": 2,
                "processing_config": {"numeric_columns": ["delay"]},
            },
        )
        assert created.status_code == 201
        job_id = created.get_json()["job_id"]
        ran = client.post(f"/jobs/{job_id}/run")
        assert ran.status_code == 200
        body = ran.get_json()
        assert body["status"] == "COMPLETED"
        delay = body["results"]["metrics"]["columns"]["delay"]
        assert delay["sum"] == 40.0
        assert delay["valid_count"] == 3
        assert delay["average"] == 40.0 / 3.0
        with Session(engine) as session:
            tasks = list(session.scalars(select(Task).where(Task.job_id == job_id)))
        used = {task.assigned_worker_id for task in tasks}
        assert len(used) == min(worker_count, 2)
        assert len(tasks) == 2
    finally:
        for server in servers:
            server.stop()


def test_task_states_match_the_design() -> None:
    assert TASK_STATUSES == ("PENDING", "RUNNING", "COMPLETED", "FAILED")


@pytest.mark.parametrize("worker_count", [1, 2, 3])
def test_job_runs_on_one_two_and_three_workers(tmp_path, worker_count: int) -> None:
    _run_with_workers(tmp_path, worker_count)


def test_run_without_workers_leaves_the_job_pending(tmp_path) -> None:
    client = _coordinator(tmp_path, _engine())
    created = client.post(
        "/jobs",
        json={
            "filename": "delays.csv",
            "csv_text": CSV,
            "processing_config": {"numeric_columns": ["delay"]},
        },
    )
    job_id = created.get_json()["job_id"]
    response = client.post(f"/jobs/{job_id}/run")
    assert response.status_code == 409
    assert client.get(f"/jobs/{job_id}").get_json()["status"] == "PENDING"
