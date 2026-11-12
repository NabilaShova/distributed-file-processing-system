"""Combine chunk metrics into one job result.

The global average is the sum of chunk sums divided by the sum of valid counts.
"""

from __future__ import annotations


def aggregate_task_metrics(results: list[dict]) -> dict:
    """Combine worker metrics. Each result is stored once."""
    columns: dict[str, dict] = {}
    total_rows = 0
    condition_count = 0
    saw_condition = False
    for metrics in results:
        total_rows += int(metrics["total_rows"])
        if metrics.get("condition_count") is not None:
            condition_count += int(metrics["condition_count"])
            saw_condition = True
        for name, column in metrics["columns"].items():
            bucket = columns.setdefault(
                name,
                {
                    "valid_count": 0,
                    "sum": 0.0,
                    "minimum": None,
                    "maximum": None,
                    "missing_count": 0,
                    "invalid_count": 0,
                },
            )
            bucket["valid_count"] += int(column["valid_count"])
            bucket["sum"] += float(column["sum"])
            bucket["missing_count"] += int(column["missing_count"])
            bucket["invalid_count"] += int(column["invalid_count"])
            bucket["minimum"] = _min(bucket["minimum"], column["minimum"])
            bucket["maximum"] = _max(bucket["maximum"], column["maximum"])
    for bucket in columns.values():
        count = bucket["valid_count"]
        bucket["average"] = (bucket["sum"] / count) if count else None
    return {
        "total_rows": total_rows,
        "columns": columns,
        "condition_count": condition_count if saw_condition else None,
    }


def _min(current, value):
    if value is None:
        return current
    if current is None:
        return value
    return min(current, value)


def _max(current, value):
    if value is None:
        return current
    if current is None:
        return value
    return max(current, value)
