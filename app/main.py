from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import (
    APP_DESCRIPTION,
    APP_NAME,
    COOKIE_NAME,
    DEFAULT_LAYER_SLUG,
    PALETTES,
    STATIC_DIR,
    TEMPLATES_DIR,
    UPLOADS_DIR,
    VENDOR_DIR,
    ensure_directories,
)
from app.database import execute, fetch_all, fetch_one, init_db, seed_defaults, utc_now
from app.security import decode_auth_token, issue_auth_token, verify_password
from app.services.cartogram import build_cartogram
from app.services.datasets import (
    add_source,
    create_dataset_record,
    get_dataset,
    load_dataset_from_source,
    list_datasets,
    list_sources,
    prepare_dataset,
    sanitize_name,
)
from app.services.exporting import build_export_bundle
from app.services.territories import get_layer, list_layers, register_layer


ensure_directories()
init_db()
seed_defaults()

app = FastAPI(title=APP_NAME, description=APP_DESCRIPTION)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/vendor", StaticFiles(directory=str(VENDOR_DIR)), name="vendor")


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=400)


def current_user(request: Request) -> dict[str, Any] | None:
    payload = decode_auth_token(request.cookies.get(COOKIE_NAME))
    if not payload:
        return None
    return fetch_one("SELECT id, username, email, role FROM users WHERE id = ?", (payload["id"],))


def require_user(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    return user


def require_admin(request: Request) -> dict[str, Any]:
    user = require_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Доступ только для администратора.")
    return user


def _dataset_schema(dataset: dict[str, Any]) -> dict[str, Any]:
    return json.loads(dataset["schema_json"])


def _list_sessions(user_id: int) -> list[dict[str, Any]]:
    sessions = fetch_all(
        """
        SELECT id, name, dataset_id, state_json, created_at, updated_at
        FROM saved_sessions
        WHERE user_id = ?
        ORDER BY updated_at DESC
        """,
        (user_id,),
    )
    parsed = []
    for session in sessions:
        state = json.loads(session["state_json"])
        parsed.append(
            {
                "id": session["id"],
                "name": session["name"],
                "datasetId": session["dataset_id"],
                "updatedAt": session["updated_at"],
                "metricLabel": state["cartogram"]["summary"].get("metricLabel"),
                "classificationMethod": state["cartogram"]["summary"].get("classificationMethod"),
            }
        )
    return parsed


def _bootstrap_payload(user: dict[str, Any]) -> dict[str, Any]:
    datasets = list_datasets()
    dataset_items = []
    for dataset in datasets:
        item = {
            "id": dataset["id"],
            "name": dataset["name"],
            "description": dataset["description"],
            "sourceType": dataset["source_type"],
            "sourceName": dataset["source_name"],
            "createdAt": dataset["created_at"],
            "schema": _dataset_schema(dataset),
        }
        dataset_items.append(item)

    layers = [
        {
            "id": layer["id"],
            "slug": layer["slug"],
            "name": layer["name"],
            "description": layer["description"],
            "featureCount": layer["feature_count"],
        }
        for layer in list_layers()
    ]

    return {
        "user": user,
        "sources": list_sources(),
        "datasets": dataset_items,
        "layers": layers,
        "sessions": _list_sessions(user["id"]),
        "palettes": PALETTES,
        "defaultLayerSlug": DEFAULT_LAYER_SLUG,
    }


@app.get("/", response_class=HTMLResponse, response_model=None)
async def login_page(request: Request) -> HTMLResponse | RedirectResponse:
    user = current_user(request)
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "title": APP_NAME,
        },
    )


@app.post("/auth/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
) -> RedirectResponse:
    user = fetch_one("SELECT * FROM users WHERE username = ?", (username,))
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль.")
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie(COOKIE_NAME, issue_auth_token(user), httponly=True, samesite="lax")
    return response


@app.post("/auth/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    user = require_user(request)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "title": APP_NAME,
            "user": user,
        },
    )


@app.get("/api/bootstrap")
async def bootstrap(request: Request) -> JSONResponse:
    user = require_user(request)
    return JSONResponse(_bootstrap_payload(user))


@app.post("/api/datasets/upload")
async def upload_dataset(
    request: Request,
    file: UploadFile = File(...),
    dataset_name: str = Form(...),
    description: str = Form(""),
) -> JSONResponse:
    user = require_user(request)
    safe_filename = sanitize_name(file.filename or "dataset.csv")
    temp_path = UPLOADS_DIR / f"temp_{utc_now().replace(':', '-')}_{safe_filename}"
    with temp_path.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)

    dataset = create_dataset_record(
        name=dataset_name,
        description=description,
        source_type="upload",
        source_name=file.filename,
        file_path=temp_path,
        uploaded_by=user["id"],
    )
    return JSONResponse(
        {
            "dataset": {
                "id": dataset["id"],
                "name": dataset["name"],
                "description": dataset["description"],
                "sourceType": dataset["source_type"],
                "sourceName": dataset["source_name"],
                "createdAt": dataset["created_at"],
                "schema": _dataset_schema(dataset),
            }
        }
    )


@app.post("/api/datasets/from-source/{source_id}")
async def dataset_from_source(source_id: int, request: Request) -> JSONResponse:
    user = require_user(request)
    dataset, already_loaded = load_dataset_from_source(source_id, user["id"])
    return JSONResponse(
        {
            "dataset": {
                "id": dataset["id"],
                "name": dataset["name"],
                "description": dataset["description"],
                "sourceType": dataset["source_type"],
                "sourceName": dataset["source_name"],
                "createdAt": dataset["created_at"],
                "schema": _dataset_schema(dataset),
            },
            "alreadyLoaded": already_loaded,
        }
    )


@app.post("/api/admin/sources")
async def create_source(
    request: Request,
    payload: dict[str, Any],
) -> JSONResponse:
    require_admin(request)
    source_id = add_source(
        payload["name"],
        payload.get("description", ""),
        payload.get("kind", "url"),
        payload.get("format", ""),
        payload.get("url", ""),
        payload.get("filePath", ""),
    )
    return JSONResponse({"sourceId": source_id})


@app.post("/api/admin/layers")
async def upload_layer(
    request: Request,
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
) -> JSONResponse:
    require_admin(request)
    temp_path = UPLOADS_DIR / f"layer_{utc_now().replace(':', '-')}_{file.filename}"
    with temp_path.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    layer = register_layer(name, description, temp_path)
    return JSONResponse({"layer": layer})


@app.post("/api/cartograms/generate")
async def generate_cartogram(request: Request, payload: dict[str, Any]) -> JSONResponse:
    user = require_user(request)
    dataset = get_dataset(int(payload["datasetId"]))
    if not dataset:
        raise HTTPException(status_code=404, detail="Набор данных не найден.")
    layer = get_layer(int(payload["layerId"]))
    if not layer:
        raise HTTPException(status_code=404, detail="Слой территорий не найден.")

    prepared = prepare_dataset(dataset, payload)
    cartogram = build_cartogram(layer_id=layer["id"], prepared_dataset=prepared, settings=payload)
    cartogram["summary"]["classificationMethod"] = payload.get("classificationMethod", "equal")

    session_name = payload.get("sessionName") or f"{dataset['name']} - {prepared['metricLabel']}"
    state = {
        "session": {
            "name": session_name,
            "datasetId": dataset["id"],
            "layerId": layer["id"],
            "savedAt": utc_now(),
        },
        "settings": payload,
        "dataset": {
            "id": dataset["id"],
            "name": dataset["name"],
            "description": dataset["description"],
            "sourceName": dataset["source_name"],
        },
        "cartogram": cartogram,
    }

    session_id = execute(
        """
        INSERT INTO saved_sessions (user_id, name, dataset_id, state_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user["id"],
            session_name,
            dataset["id"],
            json.dumps(state, ensure_ascii=False),
            utc_now(),
            utc_now(),
        ),
    )

    export_files = build_export_bundle(session_id, state)

    return JSONResponse(
        {
            "sessionId": session_id,
            "sessionName": session_name,
            "cartogram": cartogram,
            "exports": {
                key: f"/api/exports/{session_id}/{key}"
                for key in export_files
            },
        }
    )


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: int, request: Request) -> JSONResponse:
    user = require_user(request)
    session = fetch_one(
        "SELECT * FROM saved_sessions WHERE id = ? AND user_id = ?",
        (session_id, user["id"]),
    )
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена.")
    return JSONResponse(json.loads(session["state_json"]))


@app.get("/api/exports/{session_id}/{fmt}")
async def export_session(session_id: int, fmt: str, request: Request) -> FileResponse:
    user = require_user(request)
    session = fetch_one(
        "SELECT * FROM saved_sessions WHERE id = ? AND user_id = ?",
        (session_id, user["id"]),
    )
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена.")

    state = json.loads(session["state_json"])
    export_files = build_export_bundle(session_id, state)
    if fmt not in export_files:
        raise HTTPException(status_code=404, detail="Формат экспорта не поддерживается.")
    path = Path(export_files[fmt])
    media_types = {
        "geojson": "application/geo+json",
        "csv": "text/csv",
        "png": "image/png",
        "pdf": "application/pdf",
    }
    return FileResponse(path, media_type=media_types[fmt], filename=path.name)
