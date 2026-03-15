#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

try:
    from opencc import OpenCC
except ImportError:  # pragma: no cover
    OpenCC = None


ZH_WIKIPEDIA_API_URL = "https://zh.wikipedia.org/w/api.php"
EN_WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
REST_SUMMARY_URLS = {
    "zh": "https://zh.wikipedia.org/api/rest_v1/page/summary/{title}",
    "en": "https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
}
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "mysticism_library.json"
REPORT_PATH = Path(__file__).resolve().parent.parent / "data" / "mysticism_library_report.json"
USER_AGENT = "bazichart-engine/1.0 (mysticism library crawler)"
MAX_RELATED_TITLES = 12
LINK_FETCH_LIMIT = 20
SOURCE_POLICY = {
    "wikipedia": {"priority": 1, "quality_tier": "A"},
    "wikibooks": {"priority": 2, "quality_tier": "B"},
    "archive_org": {"priority": 3, "quality_tier": "B"},
    "academic": {"priority": 4, "quality_tier": "A"},
}

TOPIC_SEEDS = [
    {
        "key": "bazi",
        "title_zh_hans": "八字",
        "title_en": "Four Pillars of Destiny",
        "category": "concept",
        "tags": ["八字", "四柱", "命理", "干支"],
    },
    {
        "key": "feng_shui",
        "title_zh_hans": "风水",
        "title_en": "Feng shui",
        "category": "practice",
        "tags": ["风水", "堪舆", "环境", "气"],
    },
    {
        "key": "ziwei_doushu",
        "title_zh_hans": "紫微斗数",
        "title_en": "Zi Wei Dou Shu",
        "category": "concept",
        "tags": ["紫微斗数", "命盘", "星曜", "术数"],
    },
    {
        "key": "kanyu",
        "title_zh_hans": "堪舆",
        "title_en": "Kanyu",
        "category": "practice",
        "tags": ["堪舆", "风水", "地理", "术数"],
    },
    {
        "key": "yijing",
        "title_zh_hans": "易经",
        "title_en": "I Ching",
        "category": "classic",
        "tags": ["易经", "周易", "卦象", "经典"],
    },
    {
        "key": "yinyang_wuxing",
        "title_zh_hans": "阴阳五行",
        "title_en": "Wuxing (Chinese philosophy)",
        "category": "concept",
        "tags": ["阴阳五行", "五行", "阴阳", "哲学"],
    },
]
CASE_SEEDS = [
    {
        "case_id": "bazi-sample-001",
        "case_type": "bazi",
        "title_zh_hans": "八字案例占位样本",
        "title_en": "Bazi sample case",
        "summary_zh_hans": "用于后续接入真实八字验证案例的占位记录。",
        "summary_en": "Placeholder record for future verified bazi cases.",
        "source_url": "https://zh.wikipedia.org/wiki/八字",
        "source_type": "wikipedia_seed",
        "evidence_level": "C",
        "tags": ["八字", "案例", "命理"],
        "events": [],
        "verification_notes": "TODO: 接入真实可验证出生与事件时间线。",
        "birth_date": None,
        "birth_time": None,
        "birth_city": None,
        "gender": None,
        "pillars": {},
        "day_master": None,
        "major_structure": None,
    },
    {
        "case_id": "ziwei-sample-001",
        "case_type": "ziwei",
        "title_zh_hans": "紫微斗数案例占位样本",
        "title_en": "Ziwei sample case",
        "summary_zh_hans": "用于后续接入真实紫微斗数命例的占位记录。",
        "summary_en": "Placeholder record for future verified ziwei cases.",
        "source_url": "https://zh.wikipedia.org/wiki/紫微斗数",
        "source_type": "wikipedia_seed",
        "evidence_level": "C",
        "tags": ["紫微斗数", "案例", "命盘"],
        "events": [],
        "verification_notes": "TODO: 接入宫位、星曜与人生事件对应案例。",
        "birth_date": None,
        "birth_time": None,
        "birth_city": None,
        "gender": None,
        "pillars": {},
        "day_master": None,
        "major_structure": None,
    },
    {
        "case_id": "fengshui-sample-001",
        "case_type": "fengshui",
        "title_zh_hans": "风水案例占位样本",
        "title_en": "Feng shui sample case",
        "summary_zh_hans": "用于后续接入真实风水调整前后反馈案例的占位记录。",
        "summary_en": "Placeholder record for future verified feng shui cases.",
        "source_url": "https://zh.wikipedia.org/wiki/风水",
        "source_type": "wikipedia_seed",
        "evidence_level": "C",
        "tags": ["风水", "案例", "堪舆"],
        "events": [],
        "verification_notes": "TODO: 接入户型、调整动作与结果反馈。",
        "property_type": None,
        "layout_features": [],
        "issue": None,
        "adjustment": None,
        "outcome": None,
    },
]


class IdentityConverter:
    def convert(self, text: str) -> str:
        return text


def get_converter():
    if OpenCC is None:
        print("警告：未安装 opencc，繁体转换将跳过。", file=sys.stderr)
        return IdentityConverter()
    return OpenCC("s2t")


TRADITIONAL_CONVERTER = get_converter()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_text(value: str) -> str:
    return " ".join(value.split()).strip()


def to_traditional(text: str) -> str:
    if not text:
        return ""
    return TRADITIONAL_CONVERTER.convert(text)


def build_source_url(language: str, title: str) -> str:
    base = "https://zh.wikipedia.org/wiki/" if language == "zh" else "https://en.wikipedia.org/wiki/"
    return f"{base}{quote(title.replace(' ', '_'))}"


def fetch_page_summary(session: requests.Session, language: str, title: str) -> dict[str, Any]:
    response = session.get(REST_SUMMARY_URLS[language].format(title=quote(title)), timeout=30)
    response.raise_for_status()
    payload = response.json()
    return {
        "title": payload.get("title", title),
        "summary": normalize_text(payload.get("extract", "")),
        "source_url": payload.get("content_urls", {}).get("desktop", {}).get("page") or build_source_url(language, payload.get("title", title)),
    }


def fetch_page_links(session: requests.Session, language: str, title: str, limit: int = LINK_FETCH_LIMIT) -> list[str]:
    api_url = ZH_WIKIPEDIA_API_URL if language == "zh" else EN_WIKIPEDIA_API_URL
    payload = session.get(
        api_url,
        params={
            "action": "query",
            "format": "json",
            "prop": "links",
            "titles": title,
            "pllimit": str(limit),
        },
        timeout=30,
    )
    payload.raise_for_status()
    data = payload.json().get("query", {}).get("pages", {})
    links: list[str] = []
    for page in data.values():
        for item in page.get("links", []):
            if item.get("ns") == 0 and item.get("title"):
                links.append(item["title"])
    return links


def dedupe_titles(values: list[str], limit: int = MAX_RELATED_TITLES) -> list[str]:
    deduped: list[str] = []
    for value in values:
        normalized = normalize_text(value)
        if normalized and normalized not in deduped:
            deduped.append(normalized)
        if len(deduped) >= limit:
            break
    return deduped


def build_library_record(
    seed: dict[str, Any],
    zh_page: dict[str, Any] | None,
    en_page: dict[str, Any] | None,
    zh_links: list[str] | None = None,
    en_links: list[str] | None = None,
) -> dict[str, Any]:
    zh_title = normalize_text((zh_page or {}).get("title") or seed["title_zh_hans"])
    en_title = normalize_text((en_page or {}).get("title") or seed["title_en"])
    zh_summary = normalize_text((zh_page or {}).get("summary") or "")
    en_summary = normalize_text((en_page or {}).get("summary") or "")
    source_url = (
        (zh_page or {}).get("source_url")
        or (en_page or {}).get("source_url")
        or build_source_url("zh", zh_title)
    )
    related_titles = dedupe_titles([*(zh_links or []), *(en_links or [])])
    return {
        "key": seed["key"],
        "title_zh_hans": zh_title,
        "title_zh_hant": to_traditional(zh_title),
        "title_en": en_title,
        "summary_zh_hans": zh_summary or en_summary,
        "summary_zh_hant": to_traditional(zh_summary or en_summary),
        "summary_en": en_summary or zh_summary,
        "category": seed["category"],
        "tags": list(seed["tags"]),
        "source_type": "wikipedia",
        "source_priority": SOURCE_POLICY["wikipedia"]["priority"],
        "quality_tier": SOURCE_POLICY["wikipedia"]["quality_tier"],
        "source_url": source_url,
        "related_titles": related_titles,
    }


def build_case_record(seed: dict[str, Any]) -> dict[str, Any]:
    summary_zh_hans = normalize_text(seed["summary_zh_hans"])
    title_zh_hans = normalize_text(seed["title_zh_hans"])
    record = {
        "case_id": seed["case_id"],
        "case_type": seed["case_type"],
        "title_zh_hans": title_zh_hans,
        "title_zh_hant": to_traditional(title_zh_hans),
        "title_en": normalize_text(seed["title_en"]),
        "summary_zh_hans": summary_zh_hans,
        "summary_zh_hant": to_traditional(summary_zh_hans),
        "summary_en": normalize_text(seed["summary_en"]),
        "source_url": seed["source_url"],
        "source_type": seed["source_type"],
        "source_priority": SOURCE_POLICY["wikipedia"]["priority"],
        "quality_tier": SOURCE_POLICY["wikipedia"]["quality_tier"],
        "evidence_level": seed["evidence_level"],
        "tags": list(seed["tags"]),
        "events": list(seed["events"]),
        "verification_notes": normalize_text(seed["verification_notes"]),
    }
    if seed["case_type"] in {"bazi", "ziwei"}:
        record.update(
            {
                "birth_date": seed.get("birth_date"),
                "birth_time": seed.get("birth_time"),
                "birth_city": seed.get("birth_city"),
                "gender": seed.get("gender"),
                "pillars": dict(seed.get("pillars", {})),
                "day_master": seed.get("day_master"),
                "major_structure": seed.get("major_structure"),
            }
        )
    if seed["case_type"] == "fengshui":
        record.update(
            {
                "property_type": seed.get("property_type"),
                "layout_features": list(seed.get("layout_features", [])),
                "issue": seed.get("issue"),
                "adjustment": seed.get("adjustment"),
                "outcome": seed.get("outcome"),
            }
        )
    return record


def build_case_library(seeds: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    seeds = CASE_SEEDS if seeds is None else seeds
    return [build_case_record(seed) for seed in seeds]


def build_topic_library(session: requests.Session, seeds: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    seeds = TOPIC_SEEDS if seeds is None else seeds
    records: list[dict[str, Any]] = []
    for seed in seeds:
        zh_page = fetch_page_summary(session, "zh", seed["title_zh_hans"])
        en_page = fetch_page_summary(session, "en", seed["title_en"])
        zh_links = fetch_page_links(session, "zh", zh_page["title"])
        en_links = fetch_page_links(session, "en", en_page["title"])
        records.append(build_library_record(seed, zh_page, en_page, zh_links, en_links))
    return records


def build_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    categories: dict[str, int] = {}
    for item in records:
        categories[item["category"]] = categories.get(item["category"], 0) + 1
    return {
        "generated_at": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
        "total_records": len(records),
        "categories": categories,
        "seed_keys": [item["key"] for item in records],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="抓取 Wikipedia 玄学主题资料库")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="资料库输出文件")
    parser.add_argument("--report", type=Path, default=REPORT_PATH, help="抓取报告输出文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    records = build_topic_library(session)
    case_records = build_case_library()
    payload = {
        "topics": records,
        "cases": case_records,
    }
    report = build_report(records)
    report["case_count"] = len(case_records)
    report["case_types"] = {
        "bazi": sum(1 for item in case_records if item["case_type"] == "bazi"),
        "ziwei": sum(1 for item in case_records if item["case_type"] == "ziwei"),
        "fengshui": sum(1 for item in case_records if item["case_type"] == "fengshui"),
    }
    write_json(args.output, payload)
    write_json(args.report, report)
    print(f"输出完成：{args.output}")
    print(f"输出完成：{args.report}")
    print(f"主题条数：{len(records)}")
    print(f"案例条数：{len(case_records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
