"""Database tests begin in Phase 3."""

import coordinator.database as coordinator_database
import worker.database as worker_database


def test_database_modules_import() -> None:
    assert coordinator_database.__doc__
    assert worker_database.__doc__
