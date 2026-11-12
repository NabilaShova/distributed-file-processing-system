"""Aggregation tests."""

from coordinator.aggregator import aggregate_task_metrics


def test_global_average_uses_total_sum_and_total_count() -> None:
    combined = aggregate_task_metrics(
        [
            {
                "total_rows": 2,
                "condition_count": 1,
                "columns": {
                    "delay": {
                        "valid_count": 2,
                        "sum": 10.0,
                        "average": 5.0,
                        "minimum": 0.0,
                        "maximum": 10.0,
                        "missing_count": 0,
                        "invalid_count": 0,
                    }
                },
            },
            {
                "total_rows": 1,
                "condition_count": 1,
                "columns": {
                    "delay": {
                        "valid_count": 1,
                        "sum": 30.0,
                        "average": 30.0,
                        "minimum": 30.0,
                        "maximum": 30.0,
                        "missing_count": 0,
                        "invalid_count": 0,
                    }
                },
            },
        ]
    )
    delay = combined["columns"]["delay"]
    assert delay["sum"] == 40.0
    assert delay["valid_count"] == 3
    assert delay["average"] == 40.0 / 3.0
    assert delay["average"] != (5.0 + 30.0) / 2.0
    assert delay["minimum"] == 0.0
    assert delay["maximum"] == 30.0
    assert combined["condition_count"] == 2
