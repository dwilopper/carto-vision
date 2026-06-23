from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import DB_PATH, DEFAULT_LAYERS, DEFAULT_SOURCES, DEMO_USERS
from app.security import hash_password


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                source_type TEXT NOT NULL,
                source_name TEXT DEFAULT '',
                file_path TEXT NOT NULL,
                schema_json TEXT NOT NULL,
                uploaded_by INTEGER,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                kind TEXT NOT NULL,
                format TEXT DEFAULT '',
                url TEXT DEFAULT '',
                file_path TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS layers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                file_path TEXT NOT NULL,
                feature_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS saved_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                dataset_id INTEGER,
                state_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )


def _count_layer_features(file_path: Path) -> int:
    if not file_path.exists():
        return 0
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    if data.get("type") == "FeatureCollection":
        return len(data.get("features", []))
    return 1


def _sample_filename(path_value: str) -> str:
    return Path(path_value).name.lower()


SESSION_TEXT_REPLACEMENTS = {
    "Russia Regions Demo 2023-2025": "Регионы России 2023-2025",
    "Innovation Districts 2024": "Инновационные округа 2024",
    "Socioeconomic Districts 2022-2024": "Социально-экономические округа 2022-2024",
    "GRDP 2024 Demo": "Картограмма ВРП 2024",
    "Smoke Test GRDP 2024": "Картограмма ВРП 2024",
    "демо / ": "Пользовательский набор / ",
}

COLUMN_TEXT_REPLACEMENTS = {
    "territory_id": "Код территории",
    "territory_name": "Территория",
    "year": "Год",
    "population_mln": "Население (млн чел.)",
    "grdp_bln_rub": "ВРП (млрд руб.)",
    "avg_salary_k_rub": "Средняя зарплата (тыс. руб.)",
    "investment_bln_rub": "Инвестиции (млрд руб.)",
    "digitalization_index": "Индекс цифровизации",
    "innovation_index": "Индекс инновационной активности",
    "unemployment_rate": "Безработица (%)",
    "employment_rate": "Занятость (%)",
    "industrial_output_bln_rub": "Промышленный выпуск (млрд руб.)",
    "digital_services_share": "Индекс цифровых сервисов",
    "innovation_activity_index": "Инновационная активность (%)",
    "tech_export_bln_rub": "Технологический экспорт (млрд долл.)",
    "startup_density": "Плотность стартапов",
    "grdp_trln_rub": "ВРП (трлн руб.)",
    "export_bln_rub": "Экспорт (млрд долл.)",
    "emissions_mln_t": "Выбросы (млн т)",
    "grdp_per_capita_k_rub": "ВРП на душу населения (тыс. руб.)",
    "investment_per_capita_k_rub": "Инвестиции на душу населения (тыс. руб.)",
}


def _replace_display_text(value: str) -> str:
    normalized = value
    for old, new in {**SESSION_TEXT_REPLACEMENTS, **COLUMN_TEXT_REPLACEMENTS}.items():
        normalized = normalized.replace(old, new)
    if normalized.startswith("Демо: "):
        normalized = normalized.removeprefix("Демо: ")
    return normalized


def _normalize_saved_state(state: dict[str, Any]) -> bool:
    changed = False

    def update_text(container: dict[str, Any] | None, key: str) -> None:
        nonlocal changed
        if not isinstance(container, dict):
            return
        value = container.get(key)
        if not isinstance(value, str):
            return
        normalized = _replace_display_text(value)
        if normalized != value:
            container[key] = normalized
            changed = True

    update_text(state.get("session"), "name")
    update_text(state.get("dataset"), "name")

    settings = state.get("settings")
    for key in (
        "regionIdColumn",
        "regionNameColumn",
        "valueColumn",
        "filterColumn",
        "denominatorColumn",
        "sessionName",
    ):
        update_text(settings, key)

    summary = state.get("cartogram", {}).get("summary")
    update_text(summary, "metricLabel")

    return changed


def seed_defaults() -> None:
    with connect() as db:
        for user in DEMO_USERS:
            db.execute(
                """
                INSERT OR IGNORE INTO users (username, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user["username"],
                    user["email"],
                    hash_password(user["password"]),
                    user["role"],
                    utc_now(),
                ),
            )

        for source in DEFAULT_SOURCES:
            if not Path(source["file_path"]).exists():
                continue

            existing = db.execute(
                """
                SELECT id FROM sources
                WHERE kind = 'sample' AND file_path = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (source["file_path"],),
            ).fetchone()

            if existing:
                db.execute(
                    """
                    UPDATE sources
                    SET name = ?, description = ?, kind = ?, format = ?, url = ?, file_path = ?
                    WHERE id = ?
                    """,
                    (
                        source["name"],
                        source["description"],
                        source["kind"],
                        source["format"],
                        source["url"],
                        source["file_path"],
                        existing["id"],
                    ),
                )
            else:
                db.execute(
                    """
                    INSERT OR IGNORE INTO sources (name, description, kind, format, url, file_path, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source["name"],
                        source["description"],
                        source["kind"],
                        source["format"],
                        source["url"],
                        source["file_path"],
                        utc_now(),
                    ),
                )

        for layer in DEFAULT_LAYERS:
            if not Path(layer["file_path"]).exists():
                continue

            db.execute(
                """
                INSERT INTO layers (slug, name, description, file_path, feature_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(slug) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    file_path = excluded.file_path,
                    feature_count = excluded.feature_count
                """,
                (
                    layer["slug"],
                    layer["name"],
                    layer["description"],
                    layer["file_path"],
                    _count_layer_features(Path(layer["file_path"])),
                    utc_now(),
                ),
            )

        filename_to_label = {
            _sample_filename(source["file_path"]): source["name"]
            for source in DEFAULT_SOURCES
        }

        rows = db.execute(
            """
            SELECT id, name, source_name
            FROM datasets
            WHERE source_name != ''
            """
        ).fetchall()
        for row in rows:
            sample_name = filename_to_label.get(_sample_filename(row["source_name"]))
            if sample_name and row["name"] != sample_name:
                db.execute(
                    "UPDATE datasets SET name = ? WHERE id = ?",
                    (sample_name, row["id"]),
                )

        session_rows = db.execute(
            """
            SELECT id, name, state_json
            FROM saved_sessions
            """
        ).fetchall()
        for row in session_rows:
            updated_name = _replace_display_text(row["name"])
            updated_state_json = row["state_json"]
            state_changed = False
            try:
                state = json.loads(row["state_json"])
            except Exception:
                state = None
            if isinstance(state, dict):
                state_changed = _normalize_saved_state(state)
                if state_changed:
                    updated_state_json = json.dumps(state, ensure_ascii=False)
            if updated_name != row["name"] or state_changed:
                db.execute(
                    """
                    UPDATE saved_sessions
                    SET name = ?, state_json = ?
                    WHERE id = ?
                    """,
                    (updated_name, updated_state_json, row["id"]),
                )

        db.commit()


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute(query, params).fetchone()
    return dict(row) if row else None


def execute(query: str, params: tuple[Any, ...] = ()) -> int:
    with connect() as db:
        cursor = db.execute(query, params)
        db.commit()
        return cursor.lastrowid
