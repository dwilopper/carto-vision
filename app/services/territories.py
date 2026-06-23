from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from app.config import LAYERS_DIR
from app.database import execute, fetch_all, fetch_one, utc_now


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip().lower())
    return slug.strip("_") or "layer"


def list_layers() -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT id, slug, name, description, file_path, feature_count, created_at
        FROM layers
        ORDER BY id DESC
        """
    )


def get_layer(layer_id: int) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT id, slug, name, description, file_path, feature_count, created_at
        FROM layers
        WHERE id = ?
        """,
        (layer_id,),
    )


def load_layer_geojson(layer_id: int) -> dict[str, Any]:
    layer = get_layer(layer_id)
    if not layer:
        raise ValueError("Картографический слой не найден.")
    path = Path(layer["file_path"])
    if not path.exists():
        raise ValueError("Файл картографического слоя не найден.")
    return json.loads(path.read_text(encoding="utf-8"))


def register_layer(name: str, description: str, source_path: Path) -> dict[str, Any]:
    slug = _slugify(name)
    target = LAYERS_DIR / f"{slug}.geojson"
    shutil.copy2(source_path, target)
    data = json.loads(target.read_text(encoding="utf-8"))
    feature_count = len(data.get("features", [])) if data.get("type") == "FeatureCollection" else 1
    layer_id = execute(
        """
        INSERT INTO layers (slug, name, description, file_path, feature_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (slug, name, description, str(target), feature_count, utc_now()),
    )
    return get_layer(layer_id) or {}
