"""Aggregation tests begin in Phase 6."""

import coordinator.aggregator as aggregator


def test_aggregator_module_imports() -> None:
    assert aggregator.__doc__
