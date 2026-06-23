from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlretrieve

import pandas as pd

from app.config import UPLOADS_DIR
from app.database import execute, fetch_all, fetch_one, utc_now


def sanitize_name(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip())
    return slug or "dataset"


def list_datasets() -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT d.id, d.name, d.description, d.source_type, d.source_name, d.file_path, d.schema_json, d.uploaded_by, d.created_at
        FROM datasets d
        INNER JOIN (
            SELECT name, MAX(id) AS max_id
            FROM datasets
            GROUP BY name
        ) latest ON latest.max_id = d.id
        ORDER BY d.id DESC
        """
    )


def get_dataset(dataset_id: int) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT id, name, description, source_type, source_name, file_path, schema_json, uploaded_by, created_at
        FROM datasets
        WHERE id = ?
        """,
        (dataset_id,),
    )


def read_dataset(file_path: str | Path) -> pd.DataFrame:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return pd.DataFrame(raw)
        raise ValueError("JSON-датасет должен содержать массив объектов.")
    raise ValueError(f"Неподдерживаемый формат данных: {suffix}")


def infer_schema(frame: pd.DataFrame) -> dict[str, Any]:
    preview_rows = frame.head(8).fillna("").to_dict(orient="records")
    columns: list[dict[str, Any]] = []
    numeric_columns: list[str] = []
    categorical_columns: list[str] = []

    for column in frame.columns:
        series = frame[column]
        if pd.api.types.is_numeric_dtype(series):
            kind = "numeric"
            numeric_columns.append(column)
        else:
            kind = "text"
            categorical_columns.append(column)
        sample_values = [str(item) for item in series.dropna().astype(str).head(4).tolist()]
        columns.append(
            {
                "name": column,
                "kind": kind,
                "sampleValues": sample_values,
            }
        )

    return {
        "rowCount": int(len(frame)),
        "columns": columns,
        "numericColumns": numeric_columns,
        "categoricalColumns": categorical_columns,
        "previewRows": preview_rows,
    }


def create_dataset_record(
    *,
    name: str,
    description: str,
    source_type: str,
    source_name: str,
    file_path: Path,
    uploaded_by: int | None,
) -> dict[str, Any]:
    path = Path(file_path)
    frame = read_dataset(path)
    schema = infer_schema(frame)
    dataset_id = execute(
        """
        INSERT INTO datasets (name, description, source_type, source_name, file_path, schema_json, uploaded_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            description,
            source_type,
            source_name,
            str(path),
            json.dumps(schema, ensure_ascii=False),
            uploaded_by,
            utc_now(),
        ),
    )
    return get_dataset(dataset_id) or {}


def register_uploaded_file(
    *,
    upload_name: str,
    source_path: Path,
    dataset_name: str,
    description: str,
    uploaded_by: int | None,
) -> dict[str, Any]:
    safe_name = sanitize_name(upload_name)
    target = UPLOADS_DIR / f"{utc_now().replace(':', '-')}_{safe_name}"
    shutil.copy2(source_path, target)
    return create_dataset_record(
        name=dataset_name,
        description=description,
        source_type="upload",
        source_name=upload_name,
        file_path=target,
        uploaded_by=uploaded_by,
    )


def _find_existing_dataset_for_source(*, dataset_name: str, source_name: str) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT id, name, description, source_type, source_name, file_path, schema_json, uploaded_by, created_at
        FROM datasets
        WHERE source_name = ? OR name = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (source_name, dataset_name),
    )


def load_dataset_from_source(source_id: int, uploaded_by: int | None) -> tuple[dict[str, Any], bool]:
    source = fetch_one("SELECT * FROM sources WHERE id = ?", (source_id,))
    if not source:
        raise ValueError("Источник данных не найден.")

    if source["kind"] == "sample":
        source_path = Path(source["file_path"])
        if not source_path.exists():
            raise ValueError("Готовый источник данных недоступен.")

        existing = _find_existing_dataset_for_source(
            dataset_name=source["name"],
            source_name=source_path.name,
        )
        if existing:
            return existing, True

        dataset = register_uploaded_file(
            upload_name=source_path.name,
            source_path=source_path,
            dataset_name=source["name"],
            description=source["description"],
            uploaded_by=uploaded_by,
        )
        return dataset, False

    if source["kind"] == "url":
        existing = _find_existing_dataset_for_source(
            dataset_name=source["name"],
            source_name=source["url"],
        )
        if existing:
            return existing, True

        parsed = urlparse(source["url"])
        filename = Path(parsed.path).name or f"source_{source_id}.csv"
        target = UPLOADS_DIR / f"{utc_now().replace(':', '-')}_{sanitize_name(filename)}"
        urlretrieve(source["url"], target)
        dataset = create_dataset_record(
            name=source["name"],
            description=source["description"],
            source_type="url",
            source_name=source["url"],
            file_path=target,
            uploaded_by=uploaded_by,
        )
        return dataset, False

    raise ValueError("Неподдерживаемый тип источника данных.")


def create_dataset_from_source(source_id: int, uploaded_by: int | None) -> dict[str, Any]:
    dataset, _ = load_dataset_from_source(source_id, uploaded_by)
    return dataset


def add_source(name: str, description: str, kind: str, fmt: str, url: str, file_path: str) -> int:
    return execute(
        """
        INSERT INTO sources (name, description, kind, format, url, file_path, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (name, description, kind, fmt, url, file_path, utc_now()),
    )


def list_sources() -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT id, name, description, kind, format, url, file_path, created_at
        FROM sources
        ORDER BY id DESC
        """
    )


def _clean_text_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip()


def _apply_normalization(
    frame: pd.DataFrame,
    *,
    value_column: str,
    normalization: str,
    denominator_column: str | None,
    multiplier: float,
) -> tuple[pd.Series, str]:
    values = frame[value_column].astype(float)
    if normalization == "per_unit" and denominator_column:
        denominator = pd.to_numeric(frame[denominator_column], errors="coerce")
        safe_denominator = denominator.replace({0: pd.NA})
        normalized = values / safe_denominator.astype(float) * multiplier
        return normalized.fillna(0.0), f"{value_column} на {multiplier:g} единиц"
    if normalization == "minmax":
        lower = float(values.min())
        upper = float(values.max())
        if lower == upper:
            return values * 0 + 1, f"{value_column} (min-max)"
        return (values - lower) / (upper - lower), f"{value_column} (min-max)"
    if normalization == "zscore":
        mean = float(values.mean())
        deviation = float(values.std(ddof=0))
        if deviation == 0:
            return values * 0, f"{value_column} (z-score)"
        return (values - mean) / deviation, f"{value_column} (z-score)"
    return values, value_column


def prepare_dataset(dataset: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    frame = read_dataset(dataset["file_path"])

    region_id_column = settings["regionIdColumn"]
    region_name_column = settings["regionNameColumn"]
    value_column = settings["valueColumn"]
    filter_column = settings.get("filterColumn") or ""
    filter_value = settings.get("filterValue")
    aggregation = settings.get("aggregation") or "sum"
    normalization = settings.get("normalization") or "none"
    denominator_column = settings.get("denominatorColumn") or None
    multiplier = float(settings.get("multiplier") or 1)

    required = [region_id_column, region_name_column, value_column]
    missing_columns = [column for column in required if column not in frame.columns]
    if missing_columns:
        raise ValueError(
            f"В наборе данных отсутствуют обязательные колонки: {', '.join(missing_columns)}"
        )

    if filter_column:
        if filter_column not in frame.columns:
            raise ValueError("Указанное поле фильтра отсутствует в наборе данных.")
        if filter_value not in (None, ""):
            frame = frame[frame[filter_column].astype(str) == str(filter_value)]

    work = frame.copy()
    work[region_id_column] = _clean_text_series(work[region_id_column])
    work[region_name_column] = _clean_text_series(work[region_name_column])
    work[value_column] = pd.to_numeric(work[value_column], errors="coerce")

    if denominator_column:
        if denominator_column not in work.columns:
            raise ValueError("Поле нормализации не найдено в наборе данных.")
        work[denominator_column] = pd.to_numeric(work[denominator_column], errors="coerce")

    work = work.dropna(subset=[region_id_column, value_column])
    work = work.drop_duplicates()

    aggregation_map = {
        "sum": "sum",
        "mean": "mean",
        "median": "median",
        "max": "max",
        "min": "min",
        "last": "last",
    }
    if aggregation not in aggregation_map:
        aggregation = "sum"

    group_columns = [region_id_column, region_name_column]
    aggregation_spec = {value_column: aggregation_map[aggregation]}
    if denominator_column:
        aggregation_spec[denominator_column] = "mean"

    grouped = work.groupby(group_columns, dropna=False, as_index=False).agg(aggregation_spec)

    grouped["display_value"], display_label = _apply_normalization(
        grouped,
        value_column=value_column,
        normalization=normalization,
        denominator_column=denominator_column,
        multiplier=multiplier,
    )

    grouped["raw_value"] = grouped[value_column].astype(float)
    grouped["display_value"] = grouped["display_value"].astype(float)

    records = [
        {
            "region_id": str(row[region_id_column]),
            "region_name": str(row[region_name_column]),
            "raw_value": round(float(row["raw_value"]), 6),
            "display_value": round(float(row["display_value"]), 6),
        }
        for row in grouped.to_dict(orient="records")
    ]

    display_values = [item["display_value"] for item in records]
    raw_values = [item["raw_value"] for item in records]

    return {
        "records": records,
        "metricLabel": display_label,
        "rowCountBefore": int(len(frame)),
        "rowCountAfter": len(records),
        "rawStats": {
            "min": round(min(raw_values), 4) if raw_values else 0.0,
            "max": round(max(raw_values), 4) if raw_values else 0.0,
        },
        "displayStats": {
            "min": round(min(display_values), 4) if display_values else 0.0,
            "max": round(max(display_values), 4) if display_values else 0.0,
        },
    }
