from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.config import EXPORTS_DIR


BACKGROUND = "#F5EFE3"
GRID = "#E3D6C1"
INK = "#33271F"


def _should_draw_labels(geojson: dict[str, Any]) -> bool:
    metadata = geojson.get("metadata", {})
    label_mode = metadata.get("labelMode", "auto")
    if label_mode == "none":
        return False
    if label_mode == "always":
        return True
    return len(geojson.get("features", [])) <= 20


def _theme_colors(geojson: dict[str, Any]) -> dict[str, str]:
    if geojson.get("metadata", {}).get("mapTheme") == "dark":
        return {
            "background": "#0C1320",
            "grid": "#162338",
            "ink": "#EEF5FF",
            "muted": "#9CB4D4",
            "panel_fill": "#111B2C",
            "panel_outline": "#223553",
            "hole_fill": "#0C1320",
            "label_fill": "#13243A",
            "label_outline": "#385274",
        }
    return {
        "background": BACKGROUND,
        "grid": GRID,
        "ink": INK,
        "muted": "#6B5A4B",
        "panel_fill": "#FFF9F0",
        "panel_outline": "#D9C9AE",
        "hole_fill": BACKGROUND,
        "label_fill": "#FFF9F0",
        "label_outline": "#9C8A73",
    }


def _font_candidates() -> list[Path]:
    candidates: list[Path] = []
    windir = Path(os.environ.get("WINDIR", "C:/Windows"))
    candidates.extend(
        [
            windir / "Fonts" / "arial.ttf",
            windir / "Fonts" / "arialbd.ttf",
            windir / "Fonts" / "DejaVuSans.ttf",
        ]
    )
    candidates.extend(
        [
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
        ]
    )
    return candidates


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for font_path in _font_candidates():
        try:
            return ImageFont.truetype(str(font_path), size=size)
        except OSError:
            continue
    for font_name in ("DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _register_pdf_fonts() -> tuple[str, str]:
    regular_candidates = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arial.ttf",
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "DejaVuSans.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    bold_candidates = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arialbd.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
    ]

    regular_path = next((path for path in regular_candidates if path.exists()), None)
    bold_path = next((path for path in bold_candidates if path.exists()), regular_path)

    if regular_path:
        if "CartoVisionRegular" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("CartoVisionRegular", str(regular_path)))
        if bold_path and "CartoVisionBold" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("CartoVisionBold", str(bold_path)))
        return "CartoVisionRegular", "CartoVisionBold"

    return "Helvetica", "Helvetica-Bold"


def _iter_points(coords: Any) -> Iterable[list[float]]:
    if not coords:
        return
    if isinstance(coords[0], (float, int)):
        yield coords
        return
    for item in coords:
        yield from _iter_points(item)


def _project_bounds(features: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for feature in features:
        for point in _iter_points(feature["geometry"]["coordinates"]):
            xs.append(point[0])
            ys.append(point[1])
    return min(xs), min(ys), max(xs), max(ys)


def _to_canvas(
    x: float,
    y: float,
    *,
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
    width: int,
    height: int,
    padding: int,
) -> tuple[float, float]:
    usable_width = width - padding * 2
    usable_height = height - padding * 2
    scale = min(
        usable_width / (max_x - min_x or 1),
        usable_height / (max_y - min_y or 1),
    )
    actual_width = (max_x - min_x) * scale
    actual_height = (max_y - min_y) * scale
    offset_x = padding + (usable_width - actual_width) / 2
    offset_y = padding + (usable_height - actual_height) / 2
    px = offset_x + (x - min_x) * scale
    py = height - (offset_y + (y - min_y) * scale)
    return px, py


def _feature_center(feature: dict[str, Any]) -> tuple[float, float]:
    points = list(_iter_points(feature["geometry"]["coordinates"]))
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)


def _draw_feature_label(
    draw: ImageDraw.ImageDraw,
    *,
    feature: dict[str, Any],
    width: int,
    height: int,
    padding: int,
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    colors: dict[str, str],
) -> None:
    props = feature.get("properties", {})
    label = props.get("short_label") or props.get("code") or props.get("name_ru") or props.get("name_en")
    label_x = props.get("label_x")
    label_y = props.get("label_y")
    if not label:
        return
    if label_x is None or label_y is None:
        label_x, label_y = _feature_center(feature)

    px, py = _to_canvas(
        label_x,
        label_y,
        min_x=min_x,
        min_y=min_y,
        max_x=max_x,
        max_y=max_y,
        width=width,
        height=height,
        padding=padding,
    )
    left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
    text_width = right - left
    text_height = bottom - top
    box = (
        px - text_width / 2 - 10,
        py - text_height / 2 - 6,
        px + text_width / 2 + 10,
        py + text_height / 2 + 6,
    )
    draw.rounded_rectangle(box, radius=10, fill=colors["label_fill"], outline=colors["label_outline"], width=1)
    draw.text(
        (px - text_width / 2, py - text_height / 2 - 1),
        label,
        fill=colors["ink"],
        font=font,
    )


def export_geojson(path: Path, geojson: dict[str, Any]) -> Path:
    path.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def export_csv(path: Path, records: list[dict[str, Any]]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["region_id", "region_name", "raw_value", "display_value"],
        )
        writer.writeheader()
        writer.writerows(records)
    return path


def export_png(
    *,
    path: Path,
    title: str,
    geojson: dict[str, Any],
    legend: list[dict[str, Any]],
    summary: dict[str, Any],
) -> Path:
    colors = _theme_colors(geojson)
    width, height = 1800, 1100
    map_area_width = 1240
    padding = 70
    image = Image.new("RGB", (width, height), colors["background"])
    draw = ImageDraw.Draw(image)
    title_font = _load_font(28)
    body_font = _load_font(18)
    small_font = _load_font(15)
    label_font = _load_font(17)

    for step in range(0, map_area_width, 80):
        draw.line((step, 0, step, height), fill=colors["grid"], width=1)
    for step in range(0, height, 80):
        draw.line((0, step, map_area_width, step), fill=colors["grid"], width=1)

    features = geojson["features"]
    min_x, min_y, max_x, max_y = _project_bounds(features)

    for feature in features:
        geometry = feature["geometry"]
        fill = feature["properties"].get("fill", "#D9D5CF")
        outline = feature["properties"].get("stroke", "#3F352D")

        polygons = (
            geometry["coordinates"]
            if geometry["type"] == "MultiPolygon"
            else [geometry["coordinates"]]
        )
        for polygon in polygons:
            outer_ring = polygon[0]
            outer_points = [
                _to_canvas(
                    point[0],
                    point[1],
                    min_x=min_x,
                    min_y=min_y,
                    max_x=max_x,
                    max_y=max_y,
                    width=map_area_width,
                    height=height,
                    padding=padding,
                )
                for point in outer_ring
            ]
            draw.polygon(outer_points, fill=fill, outline=outline)

            for hole in polygon[1:]:
                hole_points = [
                    _to_canvas(
                        point[0],
                        point[1],
                        min_x=min_x,
                        min_y=min_y,
                        max_x=max_x,
                        max_y=max_y,
                        width=map_area_width,
                        height=height,
                        padding=padding,
                    )
                    for point in hole
                ]
                draw.polygon(hole_points, fill=colors["hole_fill"], outline=outline)

    if _should_draw_labels(geojson):
        for feature in features:
            _draw_feature_label(
                draw,
                feature=feature,
                width=map_area_width,
                height=height,
                padding=padding,
                min_x=min_x,
                min_y=min_y,
                max_x=max_x,
                max_y=max_y,
                font=label_font,
                colors=colors,
            )

    panel_x = map_area_width + 40
    draw.rounded_rectangle(
        (panel_x, 40, width - 40, height - 40),
        radius=28,
        fill=colors["panel_fill"],
        outline=colors["panel_outline"],
        width=2,
    )
    draw.text((padding, 32), title, fill=colors["ink"], font=title_font)
    draw.text(
        (padding, 68),
        "Экспорт картограммы для защиты дипломного проекта",
        fill=colors["muted"],
        font=small_font,
    )

    draw.text((panel_x + 28, 70), "Сводка", fill=colors["ink"], font=title_font)
    summary_lines = [
        f"Метод классификации: {summary.get('classificationMethod', 'n/a')}",
        f"Показатель: {summary.get('metricLabel', 'n/a')}",
        f"Покрытие регионов: {summary.get('matchedRegions', 0)} / {len(features)}",
        f"Min: {summary.get('min', 0)}",
        f"Max: {summary.get('max', 0)}",
        f"Среднее: {summary.get('mean', 0)}",
        f"Медиана: {summary.get('median', 0)}",
    ]
    y_cursor = 120
    for line in summary_lines:
        draw.text((panel_x + 28, y_cursor), line, fill=colors["ink"], font=body_font)
        y_cursor += 34

    draw.text((panel_x + 28, y_cursor + 30), "Легенда", fill=colors["ink"], font=title_font)
    y_cursor += 84
    for item in legend:
        draw.rounded_rectangle(
            (panel_x + 30, y_cursor, panel_x + 72, y_cursor + 24),
            radius=6,
            fill=item["color"],
            outline="#3F352D",
        )
        draw.text(
            (panel_x + 88, y_cursor - 2),
            f"{item['label']} ({item['count']})",
            fill=colors["ink"],
            font=body_font,
        )
        y_cursor += 38

    image.save(path)
    return path


def export_pdf(
    *,
    path: Path,
    title: str,
    png_path: Path,
    summary: dict[str, Any],
) -> Path:
    regular_font, bold_font = _register_pdf_fonts()
    pdf = canvas.Canvas(str(path), pagesize=landscape(A4))
    page_width, page_height = landscape(A4)
    pdf.setTitle(title)
    pdf.setFont(bold_font, 20)
    pdf.drawString(36, page_height - 36, title)
    pdf.setFont(regular_font, 11)
    pdf.drawString(
        36,
        page_height - 56,
        "Офлайн-экспорт картограммы из дипломного демо-приложения.",
    )
    pdf.drawImage(
        ImageReader(str(png_path)),
        36,
        90,
        width=page_width - 72,
        height=page_height - 170,
        preserveAspectRatio=True,
        mask="auto",
    )
    pdf.drawString(
        36,
        62,
        f"Метод классификации: {summary.get('classificationMethod', 'n/a')}",
    )
    pdf.drawString(
        300,
        62,
        f"Покрытие регионов: {summary.get('matchedRegions', 0)}",
    )
    pdf.drawString(
        520,
        62,
        f"Показатель: {summary.get('metricLabel', 'n/a')}",
    )
    pdf.save()
    return path


def build_export_bundle(session_id: int, state: dict[str, Any]) -> dict[str, str]:
    export_dir = EXPORTS_DIR / f"session_{session_id}"
    export_dir.mkdir(parents=True, exist_ok=True)

    title = state["session"]["name"]
    geojson_path = export_geojson(
        export_dir / "cartogram.geojson",
        state["cartogram"]["geojson"],
    )
    csv_path = export_csv(
        export_dir / "cartogram.csv",
        state["cartogram"]["records"],
    )
    png_path = export_png(
        path=export_dir / "cartogram.png",
        title=title,
        geojson=state["cartogram"]["geojson"],
        legend=state["cartogram"]["legend"],
        summary=state["cartogram"]["summary"],
    )
    pdf_path = export_pdf(
        path=export_dir / "cartogram.pdf",
        title=title,
        png_path=png_path,
        summary=state["cartogram"]["summary"],
    )

    return {
        "geojson": str(geojson_path),
        "csv": str(csv_path),
        "png": str(png_path),
        "pdf": str(pdf_path),
    }
