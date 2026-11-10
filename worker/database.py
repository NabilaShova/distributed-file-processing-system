"""Worker database connectivity.

Workers may check that the database is reachable. The coordinator remains the
only component that writes job, task, and result rows.
"""

from common.db import check_connection

__all__ = ["check_connection"]
