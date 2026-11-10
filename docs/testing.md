# Testing

Phase 2 unit tests cover configuration parsing, task-state names, and the coordinator and worker health endpoints. They do not connect to the virtual machines or MariaDB.

GitHub Actions runs `ruff check .` and `pytest` on Ubuntu with Python 3.12. Tests that need the three live nodes stay out of that workflow.
