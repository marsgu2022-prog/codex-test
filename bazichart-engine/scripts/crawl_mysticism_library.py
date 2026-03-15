#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
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
CATEGORY_MEMBER_LIMIT = 50
MAX_ACCEPTABLE_RETRY_AFTER = 30
SOURCE_POLICY = {
    "wikipedia": {"priority": 1, "quality_tier": "A"},
    "wikibooks": {"priority": 2, "quality_tier": "B"},
    "archive_org": {"priority": 3, "quality_tier": "B"},
    "academic": {"priority": 4, "quality_tier": "A"},
}
MAX_REPORTED_FAILURES = 50

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
    {
        "key": "yuan_hai_zi_ping",
        "title_zh_hans": "渊海子平",
        "title_en": "Yuan Hai Zi Ping",
        "category": "book",
        "tags": ["八字", "子平", "经典", "书籍"],
    },
    {
        "key": "san_ming_tong_hui",
        "title_zh_hans": "三命通会",
        "title_en": "San Ming Tong Hui",
        "category": "book",
        "tags": ["八字", "命理", "经典", "书籍"],
    },
    {
        "key": "di_tian_sui",
        "title_zh_hans": "滴天髓",
        "title_en": "Di Tian Sui",
        "category": "book",
        "tags": ["八字", "命理", "经典", "书籍"],
    },
    {
        "key": "zi_ping_zhen_quan",
        "title_zh_hans": "子平真诠",
        "title_en": "Zi Ping Zhen Quan",
        "category": "book",
        "tags": ["八字", "子平", "经典", "书籍"],
    },
    {
        "key": "qiong_tong_bao_jian",
        "title_zh_hans": "穷通宝鉴",
        "title_en": "Qiong Tong Bao Jian",
        "category": "book",
        "tags": ["八字", "调候", "经典", "书籍"],
    },
    {
        "key": "ziwei_doushu_quanshu",
        "title_zh_hans": "紫微斗数全书",
        "title_en": "Complete Book of Zi Wei Dou Shu",
        "category": "book",
        "tags": ["紫微斗数", "经典", "书籍", "星曜"],
    },
    {
        "key": "ziwei_doushu_mingpan",
        "title_zh_hans": "紫微斗数命盘",
        "title_en": "Zi Wei Dou Shu Natal Chart",
        "category": "work",
        "tags": ["紫微斗数", "命盘", "宫位", "参考"],
    },
    {
        "key": "ni_haixia_tianji",
        "title_zh_hans": "倪海厦天纪",
        "title_en": "Ni Haixia Tian Ji",
        "category": "work",
        "tags": ["倪海厦", "天纪", "命理", "公开资料"],
    },
    {
        "key": "ni_haixia_renji",
        "title_zh_hans": "倪海厦人纪",
        "title_en": "Ni Haixia Ren Ji",
        "category": "work",
        "tags": ["倪海厦", "人纪", "中医", "公开资料"],
    },
]
TOPIC_CATEGORIES = [
    {"language": "zh", "category": "Category:風水"},
    {"language": "zh", "category": "Category:命理學"},
    {"language": "zh", "category": "Category:易經"},
    {"language": "zh", "category": "Category:道教占卜"},
    {"language": "en", "category": "Category:Feng shui"},
    {"language": "en", "category": "Category:Chinese astrology"},
    {"language": "en", "category": "Category:I Ching"},
    {"language": "en", "category": "Category:Divination"},
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
    payload = get_json_with_retry(session, REST_SUMMARY_URLS[language].format(title=quote(title)))
    return {
        "title": payload.get("title", title),
        "summary": normalize_text(payload.get("extract", "")),
        "source_url": payload.get("content_urls", {}).get("desktop", {}).get("page") or build_source_url(language, payload.get("title", title)),
    }


def fetch_page_links(session: requests.Session, language: str, title: str, limit: int = LINK_FETCH_LIMIT) -> list[str]:
    api_url = ZH_WIKIPEDIA_API_URL if language == "zh" else EN_WIKIPEDIA_API_URL
    data = get_json_with_retry(
        session,
        api_url,
        params={
            "action": "query",
            "format": "json",
            "prop": "links",
            "titles": title,
            "pllimit": str(limit),
        },
    ).get("query", {}).get("pages", {})
    links: list[str] = []
    for page in data.values():
        for item in page.get("links", []):
            if item.get("ns") == 0 and item.get("title"):
                links.append(item["title"])
    return links


def fetch_category_titles(session: requests.Session, language: str, category: str, limit: int = CATEGORY_MEMBER_LIMIT) -> list[str]:
    api_url = ZH_WIKIPEDIA_API_URL if language == "zh" else EN_WIKIPEDIA_API_URL
    items = get_json_with_retry(
        session,
        api_url,
        params={
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": category,
            "cmtype": "page",
            "cmlimit": str(min(limit, 50)),
        },
    ).get("query", {}).get("categorymembers", [])
    return [normalize_text(item.get("title", "")) for item in items if item.get("title")]


def get_json_with_retry(session: requests.Session, url: str, params: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
    params = params or {}
    last_error: Exception | None = None
    for attempt in range(5):
        response = None
        try:
            response = session.get(url, params=params, timeout=timeout)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "5"))
                retry_after = min(retry_after, MAX_ACCEPTABLE_RETRY_AFTER)
                time.sleep(retry_after + attempt)
                continue
            response.raise_for_status()
            time.sleep(0.6)
            return response.json()
        except requests.RequestException as exc:
            if response is not None and 400 <= response.status_code < 500 and response.status_code != 429:
                raise
            last_error = exc
            time.sleep(2 + attempt)
    if last_error is not None:
        raise last_error
    raise RuntimeError("请求失败但未捕获具体异常")


def record_failure(
    failure_log: list[dict[str, str]] | None,
    *,
    stage: str,
    language: str,
    target: str,
    message: str,
) -> None:
    if failure_log is None:
        return
    failure_log.append(
        {
            "stage": stage,
            "language": language,
            "target": target,
            "message": normalize_text(message),
        }
    )


def create_progress_report() -> dict[str, dict[str, int]]:
    return {
        "categories": {
            "requested": 0,
            "completed": 0,
            "failed": 0,
        },
        "topics": {
            "requested": 0,
            "completed": 0,
            "partial": 0,
            "skipped": 0,
        },
    }


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


def slugify_topic_key(language: str, title: str) -> str:
    normalized = normalize_text(title).lower().replace(" ", "_")
    ascii_only = "".join(char if char.isalnum() or char == "_" else "_" for char in normalized)
    compact = "_".join(part for part in ascii_only.split("_") if part)
    return f"{language}_{compact}" if compact else f"{language}_topic"


def build_expanded_topic_seed(language: str, title: str) -> dict[str, Any]:
    if language == "zh":
        return {
            "key": slugify_topic_key(language, title),
            "title_zh_hans": title,
            "title_en": title,
            "category": "reference",
            "tags": ["玄学", "扩展"],
        }
    return {
        "key": slugify_topic_key(language, title),
        "title_zh_hans": title,
        "title_en": title,
        "category": "reference",
        "tags": ["mysticism", "reference"],
    }


def expand_topic_seeds_from_categories(
    session: requests.Session,
    limit_per_category: int = CATEGORY_MEMBER_LIMIT,
    *,
    failure_log: list[dict[str, str]] | None = None,
    progress: dict[str, dict[str, int]] | None = None,
) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    seen_keys = {seed["key"] for seed in TOPIC_SEEDS}
    for item in TOPIC_CATEGORIES:
        if progress is not None:
            progress["categories"]["requested"] += 1
        try:
            titles = fetch_category_titles(session, item["language"], item["category"], limit=limit_per_category)
        except requests.RequestException as exc:
            if progress is not None:
                progress["categories"]["failed"] += 1
            record_failure(
                failure_log,
                stage="category",
                language=item["language"],
                target=item["category"],
                message=str(exc),
            )
            continue
        if progress is not None:
            progress["categories"]["completed"] += 1
        for title in titles:
            seed = build_expanded_topic_seed(item["language"], title)
            if seed["key"] in seen_keys:
                continue
            seen_keys.add(seed["key"])
            expanded.append(seed)
    return expanded


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


def summarize_failures(failures: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    by_stage: dict[str, int] = {}
    by_language: dict[str, int] = {}
    for item in failures:
        stage = item.get("stage", "unknown")
        language = item.get("language", "unknown")
        by_stage[stage] = by_stage.get(stage, 0) + 1
        by_language[language] = by_language.get(language, 0) + 1
    return {
        "by_stage": by_stage,
        "by_language": by_language,
    }


def build_topic_library(
    session: requests.Session,
    seeds: list[dict[str, Any]] | None = None,
    *,
    include_categories: bool = False,
    category_limit: int = CATEGORY_MEMBER_LIMIT,
    failure_log: list[dict[str, str]] | None = None,
    progress: dict[str, dict[str, int]] | None = None,
) -> list[dict[str, Any]]:
    seeds = TOPIC_SEEDS if seeds is None else seeds
    expanded_seeds = list(seeds)
    if include_categories:
        expanded_seeds.extend(
            expand_topic_seeds_from_categories(
                session,
                limit_per_category=category_limit,
                failure_log=failure_log,
                progress=progress,
            )
        )
    records: list[dict[str, Any]] = []
    for seed in expanded_seeds:
        if progress is not None:
            progress["topics"]["requested"] += 1
        zh_page = None
        en_page = None
        zh_links: list[str] = []
        en_links: list[str] = []
        topic_has_failure = False

        try:
            zh_page = fetch_page_summary(session, "zh", seed["title_zh_hans"])
        except requests.RequestException as exc:
            topic_has_failure = True
            record_failure(
                failure_log,
                stage="summary",
                language="zh",
                target=seed["title_zh_hans"],
                message=str(exc),
            )

        try:
            en_page = fetch_page_summary(session, "en", seed["title_en"])
        except requests.RequestException as exc:
            topic_has_failure = True
            record_failure(
                failure_log,
                stage="summary",
                language="en",
                target=seed["title_en"],
                message=str(exc),
            )

        if zh_page is None and en_page is None:
            if progress is not None:
                progress["topics"]["skipped"] += 1
            record_failure(
                failure_log,
                stage="record",
                language="multi",
                target=seed["key"],
                message="zh/en 页面均抓取失败，已跳过该主题。",
            )
            continue

        if zh_page is not None:
            try:
                zh_links = fetch_page_links(session, "zh", zh_page["title"])
            except requests.RequestException as exc:
                topic_has_failure = True
                record_failure(
                    failure_log,
                    stage="links",
                    language="zh",
                    target=zh_page["title"],
                    message=str(exc),
                )

        if en_page is not None:
            try:
                en_links = fetch_page_links(session, "en", en_page["title"])
            except requests.RequestException as exc:
                topic_has_failure = True
                record_failure(
                    failure_log,
                    stage="links",
                    language="en",
                    target=en_page["title"],
                    message=str(exc),
                )

        records.append(build_library_record(seed, zh_page, en_page, zh_links, en_links))
        if progress is not None:
            if topic_has_failure:
                progress["topics"]["partial"] += 1
            else:
                progress["topics"]["completed"] += 1
    return records


def build_report(
    records: list[dict[str, Any]],
    failures: list[dict[str, str]] | None = None,
    *,
    requested_seed_count: int | None = None,
    include_categories: bool = False,
    category_limit: int | None = None,
    progress: dict[str, dict[str, int]] | None = None,
) -> dict[str, Any]:
    categories: dict[str, int] = {}
    for item in records:
        categories[item["category"]] = categories.get(item["category"], 0) + 1
    failures = failures or []
    progress = progress or create_progress_report()
    skipped_keys = {
        item["target"]
        for item in failures
        if item.get("stage") == "record" and item.get("target")
    }
    failure_summary = summarize_failures(failures)
    return {
        "generated_at": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
        "total_records": len(records),
        "categories": categories,
        "requested_seed_count": requested_seed_count if requested_seed_count is not None else len(records),
        "succeeded_topics": len(records),
        "skipped_topics": len(skipped_keys),
        "completed_stats": progress,
        "include_categories": include_categories,
        "category_limit": category_limit,
        "failed_requests": len(failures),
        "failure_summary": failure_summary,
        "failures": failures[:MAX_REPORTED_FAILURES],
        "seed_keys": [item["key"] for item in records],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="抓取 Wikipedia 玄学主题资料库")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="资料库输出文件")
    parser.add_argument("--report", type=Path, default=REPORT_PATH, help="抓取报告输出文件")
    parser.add_argument("--include-categories", action="store_true", help="额外抓取 Wikipedia 分类页扩展主题")
    parser.add_argument("--category-limit", type=int, default=CATEGORY_MEMBER_LIMIT, help="每个分类最多扩展多少条主题")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    failures: list[dict[str, str]] = []
    progress = create_progress_report()
    records = build_topic_library(
        session,
        include_categories=args.include_categories,
        category_limit=args.category_limit,
        failure_log=failures,
        progress=progress,
    )
    case_records = build_case_library()
    payload = {
        "topics": records,
        "cases": case_records,
    }
    report = build_report(
        records,
        failures,
        requested_seed_count=len(TOPIC_SEEDS),
        include_categories=args.include_categories,
        category_limit=args.category_limit,
        progress=progress,
    )
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
