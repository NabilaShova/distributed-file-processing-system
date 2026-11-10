"""Coordinator HTTP entry point.

Phase 2 exposes a health check. Upload, scheduling, and aggregation come later.
"""

from __future__ import annotations

from flask import Flask, jsonify

from common.logging_config import configure_logging
from coordinator.config import CoordinatorConfig


def create_app(config: CoordinatorConfig | None = None) -> Flask:
    settings = config or CoordinatorConfig.from_env()
    configure_logging(settings.log_level)
    app = Flask(__name__)
    app.config["COORDINATOR_CONFIG"] = settings

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "role": "coordinator"})

    return app


def main() -> None:
    settings = CoordinatorConfig.from_env()
    app = create_app(settings)
    app.run(host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
