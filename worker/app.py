"""Worker HTTP entry point."""

from __future__ import annotations

import logging
import threading

from flask import Flask, jsonify, request

from common.db import check_connection
from common.logging_config import configure_logging
from worker.config import WorkerConfig
from worker.processor import ProcessingError, process_csv

logger = logging.getLogger(__name__)


def create_app(config: WorkerConfig | None = None, connection_check=check_connection) -> Flask:
    settings = config or WorkerConfig.from_env()
    configure_logging(settings.log_level)
    app = Flask(__name__)
    app.config["WORKER_CONFIG"] = settings
    activity = {"in_progress": 0, "lock": threading.Lock()}

    @app.get("/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "role": "worker",
                "worker_id": settings.worker_id,
            }
        )

    @app.get("/status")
    def status():
        with activity["lock"]:
            in_progress = activity["in_progress"]
        return jsonify(
            {
                "worker_id": settings.worker_id,
                "availability": "BUSY" if in_progress else "AVAILABLE",
                "in_progress": in_progress,
                "database_reachable": bool(connection_check(settings.database_url)),
            }
        )

    @app.post("/process")
    def process():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Request body must be JSON."}), 400
        with activity["lock"]:
            activity["in_progress"] += 1
        try:
            try:
                result = process_csv(payload.get("csv_text", ""), payload.get("processing_config"))
            except ProcessingError as exc:
                logger.warning("Rejected chunk: %s", exc)
                return jsonify({"error": str(exc)}), 400
        finally:
            with activity["lock"]:
                activity["in_progress"] -= 1
        result["worker_id"] = settings.worker_id
        if "task_id" in payload:
            result["task_id"] = payload["task_id"]
        if "attempt_number" in payload:
            result["attempt_number"] = payload["attempt_number"]
        logger.info(
            "Processed chunk worker_id=%s rows=%s duration_ms=%s",
            settings.worker_id,
            result["total_rows"],
            result["duration_ms"],
        )
        return jsonify(result)

    return app


def main() -> None:
    settings = WorkerConfig.from_env()
    app = create_app(settings)
    app.run(host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
