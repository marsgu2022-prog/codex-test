from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


FONT_NAME = "NotoSansSC"
FONT_PATH = Path(__file__).resolve().parent / "fonts" / "NotoSansSC-Regular.ttf"
FALLBACK_FONT_NAME = "STSong-Light"
PAGE_SIZE = A4
PAGE_WIDTH, PAGE_HEIGHT = PAGE_SIZE
LEFT_MARGIN = 60
RIGHT_MARGIN = 60
TOP_MARGIN = 50
BOTTOM_MARGIN = 50
TITLE_COLOR = colors.HexColor("#8B6914")
SECTION_COLOR = colors.HexColor("#5C4A1E")
BODY_COLOR = colors.HexColor("#333333")
RULE_COLOR = colors.HexColor("#D4A537")
SUBTITLE_COLOR = colors.HexColor("#666666")
TABLE_HEADER_BG = colors.HexColor("#F5E6C8")
TABLE_DANGER_HEADER_BG = colors.HexColor("#E9E9E9")


def _register_chinese_font() -> str:
    if FONT_PATH.exists():
        if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))
        pdfmetrics.registerFontFamily(FONT_NAME, normal=FONT_NAME, bold=FONT_NAME)
        return FONT_NAME

    if FALLBACK_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(FALLBACK_FONT_NAME))
    pdfmetrics.registerFontFamily(FALLBACK_FONT_NAME, normal=FALLBACK_FONT_NAME, bold=FALLBACK_FONT_NAME)
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
        stem = str(_pick_first_value(pillar, ["heavenly_stem", "stem", "tiangan", "gan", "天干"]) or "")
        branch = str(_pick_first_value(pillar, ["earthly_branch", "branch", "dizhi", "zhi", "地支"]) or "")
        return stem, branch

    if isinstance(pillar, str):
        text = pillar.strip()
        if len(text) >= 2:
            return text[0], text[1]
        return text, ""

    return "", ""


def _extract_four_pillars(data: dict[str, Any]) -> list[tuple[str, str, str]]:
    pillars_container = _pick_first_dict(data, ["four_pillars", "pillars", "bazi", "chart", "natal_chart"])
    labels = [
        ("年柱", ["year", "year_pillar", "年柱"]),
        ("月柱", ["month", "month_pillar", "月柱"]),
        ("日柱", ["day", "day_pillar", "日柱"]),
        ("时柱", ["hour", "hour_pillar", "time", "时柱"]),
    ]

    result: list[tuple[str, str, str]] = []
    for label, keys in labels:
        pillar_value = _pick_first_value(pillars_container, keys)
        stem, branch = _normalize_pillar(pillar_value)
        result.append((label, stem or "未提供", branch or "未提供"))
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


def _extract_birth_info(data: dict[str, Any]) -> str:
    raw_input = _pick_first_dict(data, ["input", "request", "birth_info"])
    year = _pick_first_value(raw_input, ["birth_year", "year", "年"])
    month = _pick_first_value(raw_input, ["birth_month", "month", "月"])
    day = _pick_first_value(raw_input, ["birth_day", "day", "日"])
    hour = _pick_first_value(raw_input, ["birth_hour", "hour", "时"])
    gender = _pick_first_value(raw_input, ["gender", "sex", "性别"])
    birthplace = _pick_first_value(raw_input, ["birthplace", "location", "出生地"])

    parts = []
    if year is not None and month is not None and day is not None and hour is not None:
        parts.append(f"出生信息：{year}年{month}月{day}日 {hour}时")
    elif raw_input:
        parts.append("出生信息：已提供")
    else:
        parts.append("出生信息：未提供")

    if gender:
        parts.append(f"性别：{gender}")
    if birthplace:
        parts.append(f"出生地：{birthplace}")
    return " | ".join(parts)


def _build_styles(font_name: str) -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TitlePageTitle",
            parent=sample["Title"],
            fontName=font_name,
            fontSize=24,
            leading=30,
            alignment=TA_CENTER,
            textColor=TITLE_COLOR,
            spaceAfter=16,
        ),
        "subtitle": ParagraphStyle(
            "TitlePageSubtitle",
            parent=sample["BodyText"],
            fontName=font_name,
            fontSize=12,
            leading=18,
            alignment=TA_CENTER,
            textColor=SUBTITLE_COLOR,
            spaceAfter=8,
        ),
        "meta": ParagraphStyle(
            "TitlePageMeta",
            parent=sample["BodyText"],
            fontName=font_name,
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
            textColor=SUBTITLE_COLOR,
            spaceAfter=18,
        ),
        "section": ParagraphStyle(
            "SectionTitle",
            parent=sample["Heading2"],
            fontName=font_name,
            fontSize=16,
            leading=22,
            alignment=TA_LEFT,
            textColor=TITLE_COLOR,
            spaceAfter=10,
        ),
        "subheading": ParagraphStyle(
            "Subheading",
            parent=sample["Heading3"],
            fontName=font_name,
            fontSize=13,
            leading=18,
            alignment=TA_LEFT,
            textColor=SECTION_COLOR,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=sample["BodyText"],
            fontName=font_name,
            fontSize=11,
            leading=15.4,
            alignment=TA_LEFT,
            textColor=BODY_COLOR,
            spaceAfter=6,
        ),
        "table": ParagraphStyle(
            "TableText",
            parent=sample["BodyText"],
            fontName=font_name,
            fontSize=11,
            leading=15,
            alignment=TA_CENTER,
            textColor=BODY_COLOR,
        ),
    }


def _build_title_page(styles: dict[str, ParagraphStyle], interpretation_data: dict[str, Any]) -> list[Any]:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    story: list[Any] = [
        Spacer(1, 180),
        Paragraph("八字命盘分析报告", styles["title"]),
        Paragraph(_extract_birth_info(interpretation_data), styles["subtitle"]),
        Paragraph(f"生成日期：{generated_at}", styles["meta"]),
        Spacer(1, 12),
        HRFlowable(width="70%", thickness=1, color=RULE_COLOR, spaceBefore=6, spaceAfter=0),
        PageBreak(),
    ]
    return story


def _build_section_title(styles: dict[str, ParagraphStyle], title: str) -> list[Any]:
    return [
        HRFlowable(width="100%", thickness=0.8, color=RULE_COLOR, spaceBefore=8, spaceAfter=8),
        Paragraph(title, styles["section"]),
    ]


def _build_four_pillars_table(styles: dict[str, ParagraphStyle], interpretation_data: dict[str, Any]) -> Table:
    pillars = _extract_four_pillars(interpretation_data)
    table_data = [
        [Paragraph(label, styles["table"]) for label, _stem, _branch in pillars],
        [Paragraph(f"天干<br/>{stem}", styles["table"]) for _label, stem, _branch in pillars],
        [Paragraph(f"地支<br/>{branch}", styles["table"]) for _label, _stem, branch in pillars],
    ]
    table = Table(table_data, colWidths=[(PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN) / 4.0] * 4)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, -1), BODY_COLOR),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("INNERGRID", (0, 0), (-1, -1), 0.6, RULE_COLOR),
                ("BOX", (0, 0), (-1, -1), 0.8, RULE_COLOR),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _build_standard_table(table_data: list[list[Any]], col_widths: list[float]) -> Table:
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, -1), BODY_COLOR),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("INNERGRID", (0, 0), (-1, -1), 0.6, RULE_COLOR),
                ("BOX", (0, 0), (-1, -1), 0.8, RULE_COLOR),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _build_wuxing_table(styles: dict[str, ParagraphStyle], interpretation_data: dict[str, Any]) -> list[Any]:
    wuxing_analysis = interpretation_data.get("wuxing_analysis")
    if not isinstance(wuxing_analysis, dict):
        return []

    scores = wuxing_analysis.get("wuxing_scores", {})
    percentages = wuxing_analysis.get("wuxing_percentages", {})
    elements = ["金", "木", "水", "火", "土"]
    table_data = [
        [Paragraph(element, styles["table"]) for element in elements],
        [Paragraph(str(scores.get(element, 0)), styles["table"]) for element in elements],
        [Paragraph(f"{percentages.get(element, 0)}%", styles["table"]) for element in elements],
    ]
    table = _build_standard_table(
        table_data,
        [(PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN) / 5.0] * 5,
    )

    summary_parts = [
        f"日主{wuxing_analysis.get('day_master', '未知')}{wuxing_analysis.get('day_master_element', '')}",
        f"身势：{wuxing_analysis.get('day_master_strength', '未知')}",
    ]
    favorable = wuxing_analysis.get("favorable_elements")
    if favorable:
        summary_parts.append(f"喜用神：{'、'.join(favorable)}")
    unfavorable = wuxing_analysis.get("unfavorable_elements")
    if unfavorable:
        summary_parts.append(f"忌神：{'、'.join(unfavorable)}")

    story: list[Any] = [table, Spacer(1, 10), Paragraph(" | ".join(summary_parts), styles["body"])]
    analysis_text = _coerce_text(wuxing_analysis.get("analysis"))
    if analysis_text:
        story.append(Paragraph(analysis_text, styles["body"]))
    story.append(Spacer(1, 12))
    return story


def _chunk_items(items: list[Any], size: int) -> list[list[Any]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _build_luck_table(styles: dict[str, ParagraphStyle], items: list[dict[str, Any]], chunk_size: int, key_type: str) -> list[Any]:
    if not items:
        return []

    story: list[Any] = []
    available_width = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
    for chunk in _chunk_items(items, chunk_size):
        if key_type == "dayun":
            headers = [
                Paragraph(f"{item.get('start_age', '')}-{item.get('end_age', '')}岁", styles["table"])
                for item in chunk
            ]
            values = [
                Paragraph(f"{item.get('tiangan', '')}{item.get('dizhi', '')}", styles["table"])
                for item in chunk
            ]
        else:
            headers = [Paragraph(str(item.get("year", "")), styles["table"]) for item in chunk]
            values = [
                Paragraph(f"{item.get('tiangan', '')}{item.get('dizhi', '')}", styles["table"])
                for item in chunk
            ]

        table = _build_standard_table(
            [headers, values],
            [available_width / len(chunk)] * len(chunk),
        )
        story.append(table)
        story.append(Spacer(1, 10))
    return story


def _build_shensha_tables(styles: dict[str, ParagraphStyle], interpretation_data: dict[str, Any]) -> list[Any]:
    shensha = interpretation_data.get("shensha")
    if not isinstance(shensha, list) or not shensha:
        return []

    groups = [("吉神", "吉", TABLE_HEADER_BG), ("凶煞", "凶", TABLE_DANGER_HEADER_BG)]
    col_widths = [90, 50, 90, PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN - 230]
    story: list[Any] = []

    for title, shensha_type, header_bg in groups:
        items = [item for item in shensha if item.get("type") == shensha_type]
        if not items:
            continue

        story.append(Paragraph(f"<b>{title}</b>", styles["subheading"]))
        table_data = [
            [Paragraph(text, styles["table"]) for text in ["神煞名", "吉/凶", "出现位置", "说明"]]
        ]
        for item in items:
            table_data.append(
                [
                    Paragraph(str(item.get("name", "")), styles["table"]),
                    Paragraph(str(item.get("type", "")), styles["table"]),
                    Paragraph(str(item.get("position", "")), styles["table"]),
                    Paragraph(_coerce_text(item.get("description")), styles["body"]),
                ]
            )

        table = _build_standard_table(table_data, col_widths)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), header_bg),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 12))
    return story


def _build_named_paragraphs(
    styles: dict[str, ParagraphStyle],
    items: list[tuple[str, str]],
    empty_text: str,
) -> list[Any]:
    if not items:
        return [Paragraph(empty_text, styles["body"])]

    story: list[Any] = []
    for title, text in items:
        story.append(Paragraph(f"<b>{title}</b>", styles["subheading"]))
        for paragraph in (text.splitlines() or [""]):
            content = paragraph.strip()
            if content:
                story.append(Paragraph(content, styles["body"]))
    return story


def _draw_footer(canvas_obj, _doc):
    canvas_obj.saveState()
    canvas_obj.setFont(FALLBACK_FONT_NAME if FALLBACK_FONT_NAME in pdfmetrics.getRegisteredFontNames() else FONT_NAME, 9)
    canvas_obj.setFillColor(SUBTITLE_COLOR)
    footer = f"- {canvas_obj.getPageNumber()} -"
    canvas_obj.drawCentredString(PAGE_WIDTH / 2, 24, footer)
    canvas_obj.restoreState()


def generate_bazi_report(interpretation_data: dict) -> bytes:
    font_name = _register_chinese_font()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=PAGE_SIZE,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title="八字命盘分析报告",
    )
    styles = _build_styles(font_name)

    story: list[Any] = []
    story.extend(_build_title_page(styles, interpretation_data))

    story.extend(_build_section_title(styles, "第一节：四柱信息"))
    story.append(_build_four_pillars_table(styles, interpretation_data))
    story.append(Spacer(1, 18))

    story.extend(_build_section_title(styles, "第二节：十神分析"))
    story.extend(_build_named_paragraphs(styles, _extract_ten_gods(interpretation_data), "未提供十神分析。"))
    story.append(Spacer(1, 12))

    story.extend(_build_section_title(styles, "第三节：心理学分析"))
    story.extend(_build_named_paragraphs(styles, _extract_psychology(interpretation_data), "未提供心理学分析。"))

    wuxing_story = _build_wuxing_table(styles, interpretation_data)
    if wuxing_story:
        story.extend(_build_section_title(styles, "第四节：五行力量分析"))
        story.extend(wuxing_story)

    dayun = interpretation_data.get("dayun")
    liunian = interpretation_data.get("liunian")
    if isinstance(dayun, list) or isinstance(liunian, list):
        story.extend(_build_section_title(styles, "第五节：大运流年"))
        if isinstance(dayun, list) and dayun:
            story.append(Paragraph("<b>大运</b>", styles["subheading"]))
            story.extend(_build_luck_table(styles, dayun, 4, "dayun"))
        if isinstance(liunian, list) and liunian:
            story.append(Paragraph("<b>流年</b>", styles["subheading"]))
            story.extend(_build_luck_table(styles, liunian, 5, "liunian"))

    shensha_story = _build_shensha_tables(styles, interpretation_data)
    if shensha_story:
        story.extend(_build_section_title(styles, "第六节：神煞"))
        story.extend(shensha_story)

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return buffer.getvalue()
