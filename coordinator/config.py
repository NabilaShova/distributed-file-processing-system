"""Runtime settings for the coordinator process."""

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
class CoordinatorConfig:
    host: str
    port: int
    log_level: str
    chunk_size: int
    database_url: str
    service_name: str = "coordinator"

    @classmethod
    def from_env(cls) -> CoordinatorConfig:
        return cls(
            host=os.environ.get("COORDINATOR_HOST", "0.0.0.0"),
            port=_int_env("COORDINATOR_PORT", 8000),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            chunk_size=_int_env("CHUNK_SIZE", 1000),
            database_url=os.environ.get(
                "DATABASE_URL",
                "mysql+pymysql://dfps_app:change-me@127.0.0.1:3306/distributed_processing",
            ),
        )
