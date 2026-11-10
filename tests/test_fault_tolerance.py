"""Fault-tolerance tests begin in Phase 7."""

from common.schemas import FAILED, PENDING


def test_retry_states_are_distinct() -> None:
    assert PENDING != FAILED
