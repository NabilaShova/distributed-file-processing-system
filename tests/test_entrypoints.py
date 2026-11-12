"""Tests for the Phase 2 HTTP entry points."""

from coordinator.app import create_app as create_coordinator
from coordinator.config import CoordinatorConfig
from worker.app import create_app as create_worker
from worker.config import WorkerConfig


def test_coordinator_health() -> None:
    config = CoordinatorConfig(
        host="127.0.0.1",
        port=8000,
        log_level="WARNING",
        chunk_size=1000,
        database_url="mysql+pymysql://app_user:change-me@127.0.0.1:3306/distributed_processing",
    )
    client = create_coordinator(config).test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "role": "coordinator"}


def _worker_client():
    config = WorkerConfig(
        host="127.0.0.1",
        port=8001,
        worker_id="node01-worker",
        log_level="WARNING",
        database_url="mysql+pymysql://dfps_app:change-me@127.0.0.1:3306/distributed_processing",
    )
    return create_worker(config, connection_check=lambda _url: True).test_client()


def test_worker_health_includes_worker_id() -> None:
    response = _worker_client().get("/health")
    assert response.status_code == 200
    assert response.get_json()["worker_id"] == "node01-worker"


def test_worker_status_reports_availability() -> None:
    response = _worker_client().get("/status")
    assert response.status_code == 200
    body = response.get_json()
    assert body["availability"] == "AVAILABLE"
    assert body["database_reachable"] is True


def test_worker_process_returns_chunk_metrics() -> None:
    response = _worker_client().post(
        "/process",
        json={
            "task_id": "task-1",
            "attempt_number": 1,
            "csv_text": "delay\n10\n20\n",
            "processing_config": {"numeric_columns": ["delay"]},
        },
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["worker_id"] == "node01-worker"
    assert body["task_id"] == "task-1"
    assert body["columns"]["delay"]["sum"] == 30.0


def test_worker_process_rejects_invalid_csv() -> None:
    response = _worker_client().post("/process", json={"csv_text": ""})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_chunk_size_rejects_text(monkeypatch) -> None:
    monkeypatch.setenv("CHUNK_SIZE", "large")
    try:
        CoordinatorConfig.from_env()
    except ValueError as exc:
        assert "CHUNK_SIZE" in str(exc)
    else:
        raise AssertionError("invalid CHUNK_SIZE was accepted")
