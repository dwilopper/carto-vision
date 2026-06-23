from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LAYERS_DIR = DATA_DIR / "layers"
SAMPLE_DIR = DATA_DIR / "sample"
STORAGE_DIR = Path(os.getenv("CARTOVISION_STORAGE_DIR", str(BASE_DIR / "storage"))).resolve()
UPLOADS_DIR = STORAGE_DIR / "uploads"
EXPORTS_DIR = STORAGE_DIR / "exports"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
VENDOR_DIR = BASE_DIR / "vendor"
DB_PATH = Path(os.getenv("CARTOVISION_DB_PATH", str(BASE_DIR / "app_state.sqlite3"))).resolve()

APP_NAME = "CartoVision"
APP_DESCRIPTION = "Веб-приложение для обработки статистических данных и генерации картограмм."
COOKIE_NAME = "cartovision_auth"
SECRET_KEY = os.getenv(
    "CARTOVISION_SECRET",
    "cartovision-demo-secret-2026",
)

DEFAULT_LAYER_SLUG = "russia_regions"
DEFAULT_LAYER_FILE = LAYERS_DIR / "russia_regions.geojson"
SCHEMATIC_LAYER_FILE = LAYERS_DIR / "russia_federal_districts.geojson"

PALETTES = {
    "copper": ["#F4E4C1", "#E2BC74", "#C78A2C", "#8A5A18", "#4F2F0A"],
    "baltic": ["#DDF1EF", "#8CC9C0", "#4E9B98", "#296C70", "#173F46"],
    "ember": ["#FFF0DD", "#F7BF74", "#E88239", "#B44B1D", "#6D240E"],
    "berry": ["#F9E4EF", "#DE9FBE", "#BE6C96", "#87496C", "#4F2740"],
    "forest": ["#E4F1E8", "#9CC6A4", "#5B8C66", "#356043", "#1B3A26"],
}

DEMO_USERS = [
    {
        "username": "demo",
        "email": "demo@cartovision.local",
        "password": "demo123",
        "role": "user",
    },
    {
        "username": "admin",
        "email": "admin@cartovision.local",
        "password": "admin123",
        "role": "admin",
    },
]

DEFAULT_SOURCES = [
    {
        "name": "Регионы России 2023-2025",
        "description": "Набор по субъектам РФ: население, ВРП, инвестиции, цифровизация и занятость.",
        "kind": "sample",
        "format": "csv",
        "url": "",
        "file_path": str(SAMPLE_DIR / "russia_regions_demo_2023_2025.csv"),
    },
    {
        "name": "Инновационные округа 2024",
        "description": "Набор по федеральным округам: цифровые сервисы, инновационная активность, экспорт и стартапы.",
        "kind": "sample",
        "format": "csv",
        "url": "",
        "file_path": str(SAMPLE_DIR / "innovation_districts_2024.csv"),
    },
    {
        "name": "Социально-экономические округа 2022-2024",
        "description": "Многопериодный набор по округам: население, ВРП, безработица, инвестиции и экспорт.",
        "kind": "sample",
        "format": "csv/xlsx",
        "url": "",
        "file_path": str(SAMPLE_DIR / "socioeconomic_districts_2022_2024.csv"),
    },
]

DEFAULT_LAYERS = [
    {
        "slug": DEFAULT_LAYER_SLUG,
        "name": "Субъекты Российской Федерации",
        "description": "Контуры субъектов РФ, подготовленные для построения картограмм.",
        "file_path": str(DEFAULT_LAYER_FILE),
    },
    {
        "slug": "russia_federal_districts",
        "name": "Федеральные округа России",
        "description": "Упрощенный слой федеральных округов России для обзорных картограмм.",
        "file_path": str(SCHEMATIC_LAYER_FILE),
    },
]


def ensure_directories() -> None:
    for path in (
        DATA_DIR,
        LAYERS_DIR,
        SAMPLE_DIR,
        STORAGE_DIR,
        UPLOADS_DIR,
        EXPORTS_DIR,
        STATIC_DIR,
        TEMPLATES_DIR,
        VENDOR_DIR,
        DB_PATH.parent,
    ):
        path.mkdir(parents=True, exist_ok=True)
