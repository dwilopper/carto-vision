from __future__ import annotations

import copy
from typing import Any

from app.config import PALETTES
from app.services.classification import assign_range, compute_ranges, summarize_values
from app.services.territories import load_layer_geojson


def _norm(value: str) -> str:
    value = str(value).strip().lower().replace("ё", "е")
    value = value.replace(" - ", " ")
    return " ".join(value.replace(".", " ").replace(",", " ").split())


def _variants(value: str) -> list[str]:
    base = _norm(value)
    compact = base.replace("-", " ")
    filtered = " ".join(
        token
        for token in compact.split()
        if token
        not in {
            "область",
            "край",
            "республика",
            "автономный",
            "автономная",
            "округ",
            "город",
            "федерального",
            "значения",
        }
    )
    variants = {base, compact, filtered}
    return [item for item in variants if item]


def _build_index(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for item in records:
        for key in _variants(item["region_id"]):
            index[key] = item
        for key in _variants(item["region_name"]):
            index[key] = item
    return index


def build_cartogram(
    *,
    layer_id: int,
    prepared_dataset: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    layer = load_layer_geojson(layer_id)
    features = copy.deepcopy(layer.get("features", []))
    records = prepared_dataset["records"]
    record_index = _build_index(records)
    values = [item["display_value"] for item in records]
    colors = PALETTES.get(settings.get("palette"), PALETTES["copper"])
    ranges = compute_ranges(values, settings.get("classificationMethod", "equal"), int(settings.get("classCount", 5)), colors)

    legend_counts = {item.index: 0 for item in ranges}
    matched_regions = 0
    missing_regions: list[str] = []

    for feature in features:
        props = feature.setdefault("properties", {})
        lookup_keys = [
            props.get("region_id", ""),
            props.get("name_ru", ""),
            props.get("name_en", ""),
            props.get("code", ""),
            *(props.get("join_keys", []) or []),
        ]
        record = None
        for key in lookup_keys:
            for variant in _variants(str(key)):
                if variant in record_index:
                    record = record_index[variant]
                    break
            if record:
                break

        if not record:
            props.update(
                {
                    "has_data": False,
                    "raw_value": None,
                    "display_value": None,
                    "class_index": None,
                    "fill": "#D9D5CF",
                    "stroke": "#6F655A",
                    "stroke_width": 1.0,
                    "tooltip": f"{props.get('name_ru', props.get('name_en', 'Регион'))}: нет данных",
                }
            )
            missing_regions.append(props.get("name_ru") or props.get("name_en") or "Неизвестный регион")
            continue

        bucket = assign_range(record["display_value"], ranges)
        legend_counts[bucket.index] += 1
        matched_regions += 1
        props.update(
            {
                "has_data": True,
                "raw_value": record["raw_value"],
                "display_value": record["display_value"],
                "class_index": bucket.index,
                "fill": bucket.color,
                "stroke": "#3F352D",
                "stroke_width": 1.3,
                "tooltip": (
                    f"{props.get('name_ru', props.get('name_en', 'Region'))}\n"
                    f"Исходное значение: {record['raw_value']}\n"
                    f"Отображаемое значение: {record['display_value']}"
                ),
            }
        )

    legend = [
        {
            "index": item.index,
            "label": item.label,
            "color": item.color,
            "count": legend_counts[item.index],
        }
        for item in ranges
    ]

    available_values = [item["display_value"] for item in records]
    summary = summarize_values(available_values)
    summary.update(
        {
            "matchedRegions": matched_regions,
            "missingRegions": len(missing_regions),
            "missingRegionNames": missing_regions,
            "metricLabel": prepared_dataset["metricLabel"],
        }
    )

    return {
        "geojson": {"type": "FeatureCollection", "features": features, "metadata": layer.get("metadata", {})},
        "legend": legend,
        "summary": summary,
        "records": records,
    }
