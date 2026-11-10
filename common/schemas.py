"""Shared status values.

Request and result schemas are added with the worker and coordinator APIs.
"""

PENDING = "PENDING"
RUNNING = "RUNNING"
COMPLETED = "COMPLETED"
FAILED = "FAILED"

TASK_STATUSES = (PENDING, RUNNING, COMPLETED, FAILED)
