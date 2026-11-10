"""Runtime settings for one worker process."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


@dataclass(frozen=True)
class WorkerConfig:
    host: str
    port: int
    worker_id: str
    log_level: str
    database_url: str
    service_name: str = "worker"

    @classmethod
    def from_env(cls) -> WorkerConfig:
        return cls(
            host=os.environ.get("WORKER_HOST", "0.0.0.0"),
            port=_int_env("WORKER_PORT", 8001),
            worker_id=os.environ.get("WORKER_ID", "worker-local"),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            database_url=os.environ.get(
                "DATABASE_URL",
                "mysql+pymysql://dfps_app:change-me@127.0.0.1:3306/distributed_processing",
            ),
        )
