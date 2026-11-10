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


def test_worker_health_includes_worker_id() -> None:
    config = WorkerConfig(
        host="127.0.0.1",
        port=8001,
        worker_id="node01-worker",
        log_level="WARNING",
        database_url="mysql+pymysql://app_user:change-me@127.0.0.1:3306/distributed_processing",
    )
    client = create_worker(config).test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["worker_id"] == "node01-worker"


def test_chunk_size_rejects_text(monkeypatch) -> None:
    monkeypatch.setenv("CHUNK_SIZE", "large")
    try:
        CoordinatorConfig.from_env()
    except ValueError as exc:
        assert "CHUNK_SIZE" in str(exc)
    else:
        raise AssertionError("invalid CHUNK_SIZE was accepted")
