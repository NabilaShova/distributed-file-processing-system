# Application database

The application uses the existing MariaDB Galera cluster. It adds one database, `distributed_processing`. Cluster membership and the existing `cluster_test` and `students` databases stay unchanged.

CSV bytes are stored on the coordinator filesystem. The database stores identifiers, status, paths, error text, and compact numeric results.

| Table | Purpose | Rule that protects correctness |
|---|---|---|
| `workers` | Worker id, hostname, base URL, heartbeat | Unique base URL |
| `jobs` | Uploaded file name, row count, chunk size, processing settings | Primary key `job_id` |
| `tasks` | One chunk: path, row range, attempts, lease, assigned worker | Unique `(job_id, chunk_index)` |
| `task_results` | One accepted partial result and its metrics JSON | Unique `task_id` |
| `job_results` | One final aggregate for a job | Primary key `job_id` |

Task status values are `PENDING`, `RUNNING`, `COMPLETED`, and `FAILED`. A global average is stored only after the coordinator divides the summed values by the summed valid counts.

Apply `database/schema.sql` once, from Node 01. Galera replicates the new database to the other nodes. The application user `dfps_app` receives `SELECT`, `INSERT`, `UPDATE`, and `DELETE` on this database only. Its password belongs in `.env`, which is not committed.

Unit tests create these tables in SQLite. They do not connect to the virtual machines.
