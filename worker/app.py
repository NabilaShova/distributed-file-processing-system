"""Worker HTTP entry point.

Phase 2 exposes a health check. Chunk processing is implemented in Phase 4.
"""

from __future__ import annotations

from flask import Flask, jsonify

from common.logging_config import configure_logging
from worker.config import WorkerConfig


def create_app(config: WorkerConfig | None = None) -> Flask:
    settings = config or WorkerConfig.from_env()
    configure_logging(settings.log_level)
    app = Flask(__name__)
    app.config["WORKER_CONFIG"] = settings

    @app.get("/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "role": "worker",
                "worker_id": settings.worker_id,
            }
        )

    return app


def main() -> None:
    settings = WorkerConfig.from_env()
    app = create_app(settings)
    app.run(host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
