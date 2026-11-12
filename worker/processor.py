"""CSV chunk metrics.

The worker returns sums and valid counts. A global average is the coordinator's
sum of those sums divided by the sum of those counts.
"""

from __future__ import annotations

import time
from io import StringIO

import pandas as pd
from pandas.errors import ParserError

_OPERATORS = {
    ">": lambda left, right: left > right,
    ">=": lambda left, right: left >= right,
    "<": lambda left, right: left < right,
    "<=": lambda left, right: left <= right,
    "==": lambda left, right: left == right,
    "!=": lambda left, right: left != right,
}


class ProcessingError(ValueError):
    """The chunk or its processing configuration cannot be used."""


def process_csv(csv_text: str, processing_config: dict) -> dict:
    """Return compact metrics for one CSV chunk."""
    started = time.perf_counter()
    frame = _read_frame(csv_text)
    columns = _numeric_columns(processing_config, frame)
    column_metrics = {name: _column_metrics(frame[name]) for name in columns}
    condition_count = _condition_count(frame, processing_config, columns)
    duration_ms = int((time.perf_counter() - started) * 1000)
    return {
        "total_rows": int(len(frame)),
        "columns": column_metrics,
        "condition_count": condition_count,
        "duration_ms": duration_ms,
    }


def _read_frame(csv_text: str) -> pd.DataFrame:
    if not isinstance(csv_text, str) or csv_text.strip() == "":
        raise ProcessingError("csv_text is required.")
    try:
        frame = pd.read_csv(StringIO(csv_text))
    except ParserError as exc:
        raise ProcessingError("csv_text is not a valid CSV document.") from exc
    if frame.empty and len(frame.columns) == 0:
        raise ProcessingError("csv_text must include a header row.")
    return frame


def _numeric_columns(processing_config: dict, frame: pd.DataFrame) -> list[str]:
    if not isinstance(processing_config, dict):
        raise ProcessingError("processing_config is required.")
    raw_columns = processing_config.get("numeric_columns")
    if not isinstance(raw_columns, list) or not raw_columns:
        raise ProcessingError("processing_config.numeric_columns must list at least one column.")
    if any(not isinstance(name, str) or name.strip() == "" for name in raw_columns):
        raise ProcessingError("numeric column names must be non-empty strings.")
    if len(raw_columns) != len(set(raw_columns)):
        raise ProcessingError("numeric_columns contains a duplicate name.")
    missing = [name for name in raw_columns if name not in frame.columns]
    if missing:
        raise ProcessingError(f"CSV is missing columns: {', '.join(missing)}.")
    return raw_columns


def _missing_mask(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip()
    return series.isna() | text.isna() | (text == "")


def _column_metrics(series: pd.Series) -> dict:
    missing = _missing_mask(series)
    numeric = pd.to_numeric(series.mask(missing), errors="coerce")
    invalid = ~missing & numeric.isna()
    valid = numeric.dropna()
    valid_count = int(valid.shape[0])
    total = float(valid.sum()) if valid_count else 0.0
    return {
        "valid_count": valid_count,
        "sum": total,
        "average": (total / valid_count) if valid_count else None,
        "minimum": float(valid.min()) if valid_count else None,
        "maximum": float(valid.max()) if valid_count else None,
        "missing_count": int(missing.sum()),
        "invalid_count": int(invalid.sum()),
    }


def _condition_count(
    frame: pd.DataFrame,
    processing_config: dict,
    numeric_columns: list[str],
) -> int | None:
    condition = processing_config.get("condition")
    if condition is None:
        return None
    if not isinstance(condition, dict):
        raise ProcessingError("processing_config.condition must be an object.")
    column = condition.get("column")
    operator = condition.get("op")
    value = condition.get("value")
    if column not in numeric_columns:
        raise ProcessingError("condition.column must be one of numeric_columns.")
    if operator not in _OPERATORS:
        raise ProcessingError("condition.op must be one of >, >=, <, <=, ==, !=.")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProcessingError("condition.value must be numeric.")
    numeric = pd.to_numeric(frame[column].mask(_missing_mask(frame[column])), errors="coerce")
    matched = _OPERATORS[operator](numeric, value) & numeric.notna()
    return int(matched.sum())
