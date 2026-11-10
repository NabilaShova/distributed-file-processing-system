"""Partitioning tests begin in Phase 5."""

import coordinator.partitioner as partitioner


def test_partitioner_module_imports() -> None:
    assert partitioner.__doc__
