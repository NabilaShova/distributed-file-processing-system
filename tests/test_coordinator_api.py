"""Coordinator API tests using SQLite, not the live Galera cluster."""

import json
from io import BytesIO

from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

from common.models import Base
from coordinator.app import create_app
from coordinator.config import CoordinatorConfig


def _client(tmp_path):
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
    config = CoordinatorConfig(
        host="127.0.0.1",
        port=8000,
        log_level="WARNING",
        chunk_size=1000,
        database_url="sqlite://",
        chunks_dir=str(tmp_path),
    )
    return create_app(config, engine=engine).test_client()


def test_upload_creates_job_and_chunk_files(tmp_path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/jobs",
        data={
            "file": (BytesIO(b"delay\n1\n2\n3\n"), "flights.csv"),
            "processing_config": json.dumps({"numeric_columns": ["delay"]}),
            "chunk_size": "2",
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["total_rows"] == 3
    assert body["chunk_count"] == 2
    assert body["tasks"][0]["status"] == "PENDING"
    assert body["tasks"][0]["row_start"] == 0
    assert body["tasks"][1]["row_end"] == 3
    assert (tmp_path / body["tasks"][0]["chunk_path"]).is_file()

    listed = client.get("/jobs")
    assert listed.status_code == 200
    assert listed.get_json()[0]["job_id"] == body["job_id"]

    results = client.get(f"/jobs/{body['job_id']}/results")
    assert results.status_code == 200
    assert results.get_json()["results"] is None


def test_upload_rejects_a_missing_column(tmp_path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/jobs",
        json={
            "filename": "flights.csv",
            "csv_text": "delay\n1\n",
            "processing_config": {"numeric_columns": ["arrival_delay"]},
        },
    )
    assert response.status_code == 400
    assert client.get("/jobs").get_json() == []


def test_missing_job_and_worker_return_not_found(tmp_path) -> None:
    client = _client(tmp_path)
    assert client.get("/jobs/missing").status_code == 404
    assert client.get("/workers").get_json() == []
    assert client.get("/workers/node01-worker").status_code == 404
