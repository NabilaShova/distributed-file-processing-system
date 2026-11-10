# Deployment instructions

The Linux deployment steps are written in Phase 8, after the coordinator and workers pass their tests.

Until then:

- Node 01, Node 02, and Node 03 already run MariaDB Galera.
- Do not use these scripts to install or restart MariaDB.
- Application processes will listen on `0.0.0.0` and the port in `.env`.
