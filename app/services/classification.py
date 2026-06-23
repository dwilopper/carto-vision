from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from statistics import median

import numpy as np


@dataclass
class ClassRange:
    index: int
    min_value: float
    max_value: float
    label: str
    color: str


def _format_number(value: float) -> str:
    if abs(value) >= 100:
        return f"{value:,.0f}".replace(",", " ")
    if abs(value) >= 10:
        return f"{value:,.1f}".replace(",", " ")
    return f"{value:,.2f}".replace(",", " ")


def _clean_breaks(breaks: list[float]) -> list[float]:
    cleaned: list[float] = []
    for value in breaks:
        rounded = round(float(value), 6)
        if not cleaned or rounded > cleaned[-1]:
            cleaned.append(rounded)
    if len(cleaned) == 1:
        cleaned.append(cleaned[0])
    return cleaned


def equal_interval_breaks(values: list[float], class_count: int) -> list[float]:
    lower = min(values)
    upper = max(values)
    if lower == upper:
        return [lower, upper]
    step = (upper - lower) / class_count
    return _clean_breaks([lower + step * index for index in range(class_count + 1)])


def quantile_breaks(values: list[float], class_count: int) -> list[float]:
    quantiles = np.quantile(values, np.linspace(0, 1, class_count + 1))
    return _clean_breaks([float(item) for item in quantiles])


def jenks_breaks(values: list[float], class_count: int) -> list[float]:
    sorted_values = sorted(values)
    unique_count = len(set(sorted_values))
    target_classes = max(1, min(class_count, unique_count))
    if target_classes == 1:
        return [sorted_values[0], sorted_values[-1]]

    lower = [[0] * (target_classes + 1) for _ in range(len(sorted_values) + 1)]
    variance = [[0.0] * (target_classes + 1) for _ in range(len(sorted_values) + 1)]

    for index in range(1, target_classes + 1):
        lower[1][index] = 1
        variance[1][index] = 0.0
        for row in range(2, len(sorted_values) + 1):
            variance[row][index] = float("inf")

    for length in range(2, len(sorted_values) + 1):
        sum_values = 0.0
        sum_squares = 0.0
        weight = 0.0

        for segment in range(1, length + 1):
            value = sorted_values[length - segment]
            weight += 1
            sum_values += value
            sum_squares += value * value
            variance_current = sum_squares - (sum_values * sum_values) / weight
            lower_class_limit = length - segment + 1

            if lower_class_limit != 1:
                for current_class in range(2, target_classes + 1):
                    candidate = variance_current + variance[lower_class_limit - 1][current_class - 1]
                    if variance[length][current_class] >= candidate:
                        lower[length][current_class] = lower_class_limit
                        variance[length][current_class] = candidate

        lower[length][1] = 1
        variance[length][1] = variance_current

    breaks = [0.0] * (target_classes + 1)
    breaks[target_classes] = sorted_values[-1]
    breaks[0] = sorted_values[0]

    row = len(sorted_values)
    current_class = target_classes
    while current_class > 1:
        lower_class_limit = lower[row][current_class] - 1
        breaks[current_class - 1] = sorted_values[lower_class_limit]
        row = lower_class_limit
        current_class -= 1

    return _clean_breaks(breaks)


def compute_ranges(values: list[float], method: str, class_count: int, colors: list[str]) -> list[ClassRange]:
    if not values:
        return []

    unique_count = len(set(values))
    target_count = max(1, min(class_count, unique_count, len(colors)))

    if method == "quantiles":
        breaks = quantile_breaks(values, target_count)
    elif method == "natural_breaks":
        breaks = jenks_breaks(values, target_count)
    else:
        breaks = equal_interval_breaks(values, target_count)

    if len(breaks) - 1 < target_count:
        target_count = len(breaks) - 1

    ranges: list[ClassRange] = []
    palette = colors[:target_count]
    for index in range(target_count):
        min_value = breaks[index]
        max_value = breaks[index + 1]
        label = f"{_format_number(min_value)} - {_format_number(max_value)}"
        ranges.append(
            ClassRange(
                index=index,
                min_value=min_value,
                max_value=max_value,
                label=label,
                color=palette[index],
            )
        )
    return ranges


def assign_range(value: float, ranges: list[ClassRange]) -> ClassRange:
    for item in ranges[:-1]:
        if item.min_value <= value < item.max_value:
            return item
    return ranges[-1]


def summarize_values(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0, "min": 0.0, "max": 0.0, "mean": 0.0, "median": 0.0}
    return {
        "count": len(values),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "mean": round(float(np.mean(values)), 4),
        "median": round(float(median(values)), 4),
    }
