"""Chunk metric tests."""

import pytest

from worker.processor import ProcessingError, process_csv

SAMPLE = "departure_delay,arrival_delay\n10,5\n,bad\n20,15\n"


def test_metrics_separate_missing_invalid_and_valid_values() -> None:
    result = process_csv(
        SAMPLE,
        {
            "numeric_columns": ["departure_delay", "arrival_delay"],
            "condition": {"column": "departure_delay", "op": ">", "value": 15},
        },
    )

    departure = result["columns"]["departure_delay"]
    arrival = result["columns"]["arrival_delay"]
    assert result["total_rows"] == 3
    assert departure == {
        "valid_count": 2,
        "sum": 30.0,
        "average": 15.0,
        "minimum": 10.0,
        "maximum": 20.0,
        "missing_count": 1,
        "invalid_count": 0,
    }
    assert arrival["valid_count"] == 2
    assert arrival["sum"] == 20.0
    assert arrival["missing_count"] == 0
    assert arrival["invalid_count"] == 1
    assert result["condition_count"] == 1
    assert result["duration_ms"] >= 0


def test_average_is_absent_when_no_value_is_valid() -> None:
    result = process_csv("delay\n\nbad\n", {"numeric_columns": ["delay"]})
    assert result["columns"]["delay"]["valid_count"] == 0
    assert result["columns"]["delay"]["sum"] == 0.0
    assert result["columns"]["delay"]["average"] is None
    assert result["condition_count"] is None


def test_unknown_column_is_rejected() -> None:
    with pytest.raises(ProcessingError, match="missing columns"):
        process_csv("delay\n1\n", {"numeric_columns": ["arrival_delay"]})
