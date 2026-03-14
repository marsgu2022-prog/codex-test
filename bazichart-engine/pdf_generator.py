from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


FONT_NAME = "NotoSansSC"
FONT_PATH = Path(__file__).resolve().parent / "fonts" / "NotoSansSC-Regular.ttf"
FALLBACK_FONT_NAME = "STSong-Light"
PAGE_SIZE = A4
PAGE_WIDTH, PAGE_HEIGHT = PAGE_SIZE
LEFT_MARGIN = 72
RIGHT_MARGIN = 72
TOP_MARGIN = 72
BOTTOM_MARGIN = 72
LINE_HEIGHT = 18
SECTION_GAP = 10


def _register_chinese_font() -> str:
    if FONT_PATH.exists():
        if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))
        return FONT_NAME

    if FALLBACK_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(FALLBACK_FONT_NAME))
    return FALLBACK_FONT_NAME


def _pick_first_dict(source: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    for key in keys:
        value = source.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _pick_first_value(source: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in source:
            return source[key]
    return None


def _normalize_pillar(pillar: Any) -> tuple[str, str]:
    if isinstance(pillar, dict):
        stem = str(
            _pick_first_value(
                pillar,
                ["heavenly_stem", "stem", "tiangan", "gan", "天干"],
            )
            or ""
        )
        branch = str(
            _pick_first_value(
                pillar,
                ["earthly_branch", "branch", "dizhi", "zhi", "地支"],
            )
            or ""
        )
        return stem, branch

    if isinstance(pillar, str):
        text = pillar.strip()
        if len(text) >= 2:
            return text[0], text[1]
        return text, ""

    return "", ""


def _extract_four_pillars(data: dict[str, Any]) -> list[str]:
    pillars_container = _pick_first_dict(
        data,
        ["four_pillars", "pillars", "bazi", "chart", "natal_chart"],
    )
    labels = [
        ("年柱", ["year", "year_pillar", "年柱"]),
        ("月柱", ["month", "month_pillar", "月柱"]),
        ("日柱", ["day", "day_pillar", "日柱"]),
        ("时柱", ["hour", "hour_pillar", "time", "hour_pillar", "时柱"]),
    ]

    result: list[str] = []
    for label, keys in labels:
        pillar_value = _pick_first_value(pillars_container, keys)
        stem, branch = _normalize_pillar(pillar_value)
        if stem or branch:
            result.append(f"{label}：天干 {stem or '未提供'}，地支 {branch or '未提供'}")
        else:
            result.append(f"{label}：未提供")
    return result


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        parts = [_coerce_text(item) for item in value]
        return "\n".join(part for part in parts if part)
    if isinstance(value, dict):
        preferred = _pick_first_value(value, ["interpretation", "analysis", "text", "description", "summary", "content"])
        if preferred is not None:
            return _coerce_text(preferred)
        parts = []
        for key, item in value.items():
            text = _coerce_text(item)
            if text:
                parts.append(f"{key}：{text}")
        return "\n".join(parts)
    return str(value)


def _extract_ten_gods(data: dict[str, Any]) -> list[tuple[str, str]]:
    raw = _pick_first_value(data, ["ten_gods_analysis", "ten_gods", "shishen_analysis", "十神分析"])
    if isinstance(raw, dict):
        items = []
        for name, value in raw.items():
            text = _coerce_text(value)
            if text:
                items.append((str(name), text))
        return items

    if isinstance(raw, list):
        items = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = str(_pick_first_value(item, ["name", "god", "title", "十神"]) or "未命名十神")
            text = _coerce_text(item)
            if text:
                items.append((name, text))
        return items

    return []


def _extract_psychology(data: dict[str, Any]) -> list[tuple[str, str]]:
    raw = _pick_first_value(
        data,
        ["psychological_analysis", "psychology_analysis", "psychology", "psychological", "心理学分析"],
    )
    if isinstance(raw, dict):
        items = []
        for key, value in raw.items():
            text = _coerce_text(value)
            if text:
                items.append((str(key), text))
        return items

    if isinstance(raw, list):
        items = []
        for index, item in enumerate(raw, start=1):
            text = _coerce_text(item)
            if text:
                items.append((f"条目 {index}", text))
        return items

    text = _coerce_text(raw)
    return [("心理学分析", text)] if text else []


def _wrap_text(text: str, font_name: str, font_size: int, max_width: float) -> list[str]:
    if not text:
        return [""]

    wrapped_lines: list[str] = []
    for raw_line in text.splitlines() or [""]:
        current = ""
        for char in raw_line:
            candidate = f"{current}{char}"
            if current and pdfmetrics.stringWidth(candidate, font_name, font_size) > max_width:
                wrapped_lines.append(current)
                current = char
            else:
                current = candidate
        wrapped_lines.append(current)
    return wrapped_lines or [""]


def _new_page(pdf: canvas.Canvas, font_name: str, title: str | None = None) -> float:
    pdf.showPage()
    if title:
        pdf.setFont(font_name, 16)
        pdf.drawString(LEFT_MARGIN, PAGE_HEIGHT - TOP_MARGIN, title)
        return PAGE_HEIGHT - TOP_MARGIN - 30
    return PAGE_HEIGHT - TOP_MARGIN


def _draw_paragraphs(
    pdf: canvas.Canvas,
    paragraphs: list[str],
    font_name: str,
    font_size: int,
    cursor_y: float,
    section_title: str | None = None,
) -> float:
    max_width = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
    if section_title:
        if cursor_y < BOTTOM_MARGIN + 40:
            cursor_y = _new_page(pdf, font_name)
        pdf.setFont(font_name, 16)
        pdf.drawString(LEFT_MARGIN, cursor_y, section_title)
        cursor_y -= 30

    pdf.setFont(font_name, font_size)
    for paragraph in paragraphs:
        for line in _wrap_text(paragraph, font_name, font_size, max_width):
            if cursor_y < BOTTOM_MARGIN:
                cursor_y = _new_page(pdf, font_name)
                pdf.setFont(font_name, font_size)
            pdf.drawString(LEFT_MARGIN, cursor_y, line)
            cursor_y -= LINE_HEIGHT
        cursor_y -= SECTION_GAP
    return cursor_y


def generate_bazi_report(interpretation_data: dict) -> bytes:
    font_name = _register_chinese_font()
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=PAGE_SIZE)
    pdf.setTitle("八字命盘分析报告")

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    pdf.setFont(font_name, 24)
    pdf.drawString(LEFT_MARGIN, PAGE_HEIGHT - 140, "八字命盘分析报告")
    pdf.setFont(font_name, 12)
    pdf.drawString(LEFT_MARGIN, PAGE_HEIGHT - 175, f"生成日期：{generated_at}")

    cursor_y = _new_page(pdf, font_name, "第一节：四柱信息")
    cursor_y = _draw_paragraphs(pdf, _extract_four_pillars(interpretation_data), font_name, 12, cursor_y)

    ten_gods = _extract_ten_gods(interpretation_data)
    ten_god_paragraphs = []
    for title, text in ten_gods:
        ten_god_paragraphs.append(f"{title}")
        ten_god_paragraphs.append(text)
    if not ten_god_paragraphs:
        ten_god_paragraphs.append("未提供十神分析。")
    cursor_y = _draw_paragraphs(pdf, ten_god_paragraphs, font_name, 12, cursor_y, "第二节：十神分析")

    psychology = _extract_psychology(interpretation_data)
    psychology_paragraphs = []
    for title, text in psychology:
        psychology_paragraphs.append(f"{title}")
        psychology_paragraphs.append(text)
    if not psychology_paragraphs:
        psychology_paragraphs.append("未提供心理学分析。")
    _draw_paragraphs(pdf, psychology_paragraphs, font_name, 12, cursor_y, "第三节：心理学分析")

    pdf.save()
    return buffer.getvalue()
