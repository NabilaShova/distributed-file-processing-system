# Distributed file processing system

A fault-tolerant distributed CSV processor. A coordinator partitions a dataset and sends chunks to worker processes. MariaDB Galera stores job, task, and result metadata.

## Current layout

- `coordinator/` — coordinator process. `GET /health`, `POST /jobs`, `GET /jobs`, and job, result, and worker reads are available. Dispatch to workers arrives in Phase 6.
- `worker/` — worker process. `GET /health`, `GET /status`, and `POST /process` are available.
- `dashboard/` — Streamlit entry point. Monitoring views arrive in Phase 9.
- `common/` — logging and shared constants.
- `database/schema.sql` — `distributed_processing` table definitions.
- `docs/` — installation and design notes.

## Local check

Virtual environment created with Python 3.12
