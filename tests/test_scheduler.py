"""Scheduler tests begin in Phases 6 and 7."""

from common.schemas import TASK_STATUSES


def test_task_states_match_the_design() -> None:
    assert TASK_STATUSES == ("PENDING", "RUNNING", "COMPLETED", "FAILED")
