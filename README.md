# Distributed file processing system

A fault-tolerant distributed CSV processor. A coordinator partitions a dataset and sends chunks to worker processes. MariaDB Galera stores job, task, and result metadata.

## Current layout

- `coordinator/` — coordinator process. `GET /health` is available.
- `worker/` — worker process. `GET /health` is available.
- `dashboard/` — Streamlit entry point. Monitoring views arrive in Phase 9.
- `common/` — logging and shared constants.
- `database/schema.sql` — schema file reserved for Phase 3.
- `docs/` — installation and design notes.

## Local check

Virtual environment created with Python 3.12
