# Deployment

Deployment commands for the three Ubuntu nodes are added in Phase 8.

The Galera cluster is already running:

| Node | Address | Application role |
|---|---|---|
| node01 | 10.10.10.10 | Coordinator port 8000 and worker port 8001 |
| node02 | 10.10.10.20 | Worker port 8001 |
| node03 | 10.10.10.30 | Worker port 8001 |

MariaDB listens on port 3306. Galera listens on port 4567. The application database `distributed_processing` is created in Phase 3.
