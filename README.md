# Distributed file processing system

Academic project: a fault-tolerant distributed CSV processor. A coordinator partitions a dataset and sends chunks to worker processes. MariaDB Galera stores job, task, and result metadata.

This repository is at the Phase 2 foundation. Health endpoints and project configuration are in place. Partitioning, scheduling, fault recovery, the dashboard, and benchmarks are later phases.

## Current layout

- `coordinator/` — coordinator process. `GET /health` is available.
- `worker/` — worker process. `GET /health` is available.
- `dashboard/` — Streamlit entry point. Monitoring views arrive in Phase 9.
- `common/` — logging and shared constants.
- `database/schema.sql` — schema file reserved for Phase 3.
- `docs/` — installation and design notes.

## Local check

Create a virtual environment with Python 3.12, install `requirements.txt`, then run:

```bash
pytest
ruff check .
```

Copy `.env.example` to `.env` before connecting to MariaDB. The example file contains placeholders, not a real password.
