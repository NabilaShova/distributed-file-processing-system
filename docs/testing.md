# Testing

Unit tests cover configuration parsing, task-state names, health endpoints, and the application tables. Table tests use SQLite. They do not connect to the virtual machines or MariaDB.

GitHub Actions runs `ruff check .` and `pytest` on Ubuntu with Python 3.12. Tests that need the three live nodes stay out of that workflow.
