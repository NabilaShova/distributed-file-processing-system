# Architecture

Phase 2 records the design. The behaviour below is not all implemented yet.

The coordinator on Node 01 (`10.10.10.10:8000`) receives a CSV file, validates it, writes chunks to disk, and creates job and task rows. Three workers, on ports `8001` of Node 01, Node 02 (`10.10.10.20`), and Node 03 (`10.10.10.30`), process one chunk per task.

The coordinator is the only component that writes job, task, and result rows. Workers return compact JSON metrics. MariaDB Galera replicates the coordinator's commits. Full CSV files are not stored in the database.

A global average is the total sum divided by the total count of valid numbers. Task states are `PENDING`, `RUNNING`, `COMPLETED`, and `FAILED`. Version 1 recovers from worker failure while the coordinator process stays available.

The Streamlit dashboard runs on the Windows host and reads the coordinator API.

Phase 4 implements the worker endpoints `GET /health`, `GET /status`, and `POST /process`. A worker returns the sum, valid count, minimum, maximum, missing count, and invalid count for each configured numeric column. Its column average is that column's own sum divided by its own valid count. The coordinator later divides the combined sums by the combined valid counts.

Phase 5 accepts a CSV at `POST /jobs`, checks the configured columns, and writes chunks of the configured size under `data/chunks`. The database stores the job, one task per chunk, and the relative chunk path. It does not store the CSV text. Worker dispatch is Phase 6, so a new job stays `PENDING`.
