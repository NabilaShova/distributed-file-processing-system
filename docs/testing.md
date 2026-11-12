# Testing

Unit tests cover configuration parsing, task-state names, health and worker endpoints, chunk metrics, CSV partitioning, job creation, parallel dispatch, result aggregation, and the application tables. Dispatch tests start local worker servers. Table and job tests use SQLite. They do not connect to the virtual machines or MariaDB.

GitHub Actions runs `ruff check .` and `pytest` on Ubuntu with Python 3.12. Tests that need the three live nodes stay out of that workflow.
