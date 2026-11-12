"""CSV partitioning.

Chunk files are written under the coordinator data directory. MariaDB stores
only the relative path and the row range.
"""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from uuid import uuid4

import pandas as pd
from pandas.errors import ParserError

_OPERATORS = {">", ">=", "<", "<=", "==", "!="}


class DatasetError(ValueError):
    """The uploaded CSV or its processing configuration cannot be used."""


def read_dataset(csv_text: str) -> pd.DataFrame:
    if not isinstance(csv_text, str) or csv_text.strip() == "":
        raise DatasetError("A CSV document is required.")
    try:
        frame = pd.read_csv(StringIO(csv_text))
    except ParserError as exc:
        raise DatasetError("The upload is not a valid CSV document.") from exc
    if len(frame.columns) == 0:
        raise DatasetError("The CSV must include a header row.")
    if len(frame) == 0:
        raise DatasetError("The CSV must include at least one data row.")
    return frame


def parse_processing_config(raw: object) -> dict:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DatasetError("processing_config must be JSON.") from exc
    if not isinstance(raw, dict):
        raise DatasetError("processing_config is required.")
    return raw


def validate_dataset(frame: pd.DataFrame, processing_config: dict) -> None:
    columns = processing_config.get("numeric_columns")
    if not isinstance(columns, list) or not columns:
        raise DatasetError("processing_config.numeric_columns must list at least one column.")
    if any(not isinstance(name, str) or name.strip() == "" for name in columns):
        raise DatasetError("numeric column names must be non-empty strings.")
    if len(columns) != len(set(columns)):
        raise DatasetError("numeric_columns contains a duplicate name.")
    missing = [name for name in columns if name not in frame.columns]
    if missing:
        raise DatasetError(f"CSV is missing columns: {', '.join(missing)}.")
    condition = processing_config.get("condition")
    if condition is None:
        return
    if not isinstance(condition, dict):
        raise DatasetError("processing_config.condition must be an object.")
    if condition.get("column") not in columns:
        raise DatasetError("condition.column must be one of numeric_columns.")
    if condition.get("op") not in _OPERATORS:
        raise DatasetError("condition.op must be one of >, >=, <, <=, ==, !=.")
    value = condition.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DatasetError("condition.value must be numeric.")


def partition_frame(frame: pd.DataFrame, chunk_size: int) -> list[pd.DataFrame]:
    if chunk_size < 1:
        raise DatasetError("chunk_size must be at least 1.")
    return [
        frame.iloc[start : start + chunk_size].copy()
        for start in range(0, len(frame), chunk_size)
    ]


def write_chunks(chunks_dir: Path, job_id: str, frames: list[pd.DataFrame]) -> list[dict]:
    """Write chunk files and return task metadata. Paths are relative."""
    job_dir = chunks_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    records = []
    row = 0
    for index, frame in enumerate(frames):
        task_id = str(uuid4())
        relative = f"{job_id}/{task_id}.csv"
        frame.to_csv(chunks_dir / relative, index=False)
        records.append(
            {
                "task_id": task_id,
                "chunk_index": index,
                "row_start": row,
                "row_end": row + len(frame),
                "chunk_path": relative,
            }
        )
        row += len(frame)
    return records
