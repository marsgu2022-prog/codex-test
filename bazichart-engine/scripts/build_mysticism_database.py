#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "data"
INPUT_PATH = DATA_DIR / "mysticism_library.json"
OUTPUT_PATH = DATA_DIR / "mysticism_library.db"
CRAWL_SCRIPT_PATH = SCRIPT_DIR / "crawl_mysticism_library.py"

SPEC = importlib.util.spec_from_file_location("crawl_mysticism_library_db", CRAWL_SCRIPT_PATH)
MYSTICISM_MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["crawl_mysticism_library_db"] = MYSTICISM_MODULE
SPEC.loader.exec_module(MYSTICISM_MODULE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建玄学资料库 SQLite 数据库")
    parser.add_argument("--input", type=Path, default=INPUT_PATH, help="资料库 JSON 输入文件")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="SQLite 数据库输出文件")
    parser.add_argument("--seed-only", action="store_true", help="只使用内置种子生成数据库，不依赖 JSON 输入")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_seed_payload() -> dict[str, Any]:
    topics = [MYSTICISM_MODULE.build_library_record(seed, None, None, [], []) for seed in MYSTICISM_MODULE.TOPIC_SEEDS]
    cases = MYSTICISM_MODULE.build_case_library()
    return {
        "topics": topics,
        "cases": cases,
        "source_registry": build_seed_source_registry(),
        "term_aliases": build_seed_term_aliases(topics),
        "concept_relations": build_seed_concept_relations(topics),
        "rule_fragments": build_seed_rule_fragments(),
        "case_event_links": build_seed_case_event_links(cases),
        "source_quality_reviews": build_seed_source_quality_reviews(topics, cases),
    }


def load_payload(input_path: Path, seed_only: bool = False) -> dict[str, Any]:
    if not seed_only and input_path.exists():
        return read_json(input_path)
    return build_seed_payload()


def connect_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def rebuild_evolving_tables(conn: sqlite3.Connection) -> None:
    # 这些表仍在快速演进，构建前直接重建以避免旧 schema 残留。
    for table in [
        "mysticism_source_registry",
        "mysticism_source_quality_reviews",
    ]:
        conn.execute(f"DROP TABLE IF EXISTS {table}")


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode = WAL;

        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mysticism_topics (
            topic_key TEXT PRIMARY KEY,
            title_zh_hans TEXT NOT NULL,
            title_zh_hant TEXT NOT NULL,
            title_en TEXT NOT NULL,
            summary_zh_hans TEXT NOT NULL,
            summary_zh_hant TEXT NOT NULL,
            summary_en TEXT NOT NULL,
            category TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_priority INTEGER NOT NULL,
            quality_tier TEXT NOT NULL,
            source_url TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mysticism_topic_tags (
            topic_key TEXT NOT NULL,
            tag TEXT NOT NULL,
            PRIMARY KEY (topic_key, tag)
        );

        CREATE TABLE IF NOT EXISTS mysticism_topic_related_titles (
            topic_key TEXT NOT NULL,
            related_title TEXT NOT NULL,
            display_order INTEGER NOT NULL,
            PRIMARY KEY (topic_key, related_title)
        );

        CREATE TABLE IF NOT EXISTS mysticism_cases (
            case_id TEXT PRIMARY KEY,
            case_type TEXT NOT NULL,
            title_zh_hans TEXT NOT NULL,
            title_zh_hant TEXT NOT NULL,
            title_en TEXT NOT NULL,
            summary_zh_hans TEXT NOT NULL,
            summary_zh_hant TEXT NOT NULL,
            summary_en TEXT NOT NULL,
            source_url TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_priority INTEGER NOT NULL,
            quality_tier TEXT NOT NULL,
            evidence_level TEXT NOT NULL,
            verification_notes TEXT NOT NULL,
            birth_date TEXT,
            birth_time TEXT,
            birth_city TEXT,
            gender TEXT,
            pillars_json TEXT,
            day_master TEXT,
            major_structure TEXT,
            property_type TEXT,
            layout_features_json TEXT,
            issue TEXT,
            adjustment TEXT,
            outcome TEXT,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mysticism_case_tags (
            case_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            PRIMARY KEY (case_id, tag)
        );

        CREATE TABLE IF NOT EXISTS mysticism_case_events (
            case_id TEXT NOT NULL,
            event_index INTEGER NOT NULL,
            event_year INTEGER,
            event_text TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            PRIMARY KEY (case_id, event_index)
        );

        CREATE TABLE IF NOT EXISTS mysticism_term_aliases (
            alias_id TEXT PRIMARY KEY,
            canonical_key TEXT NOT NULL,
            alias_text TEXT NOT NULL,
            language TEXT NOT NULL,
            alias_type TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mysticism_source_registry (
            source_type TEXT PRIMARY KEY,
            source_name TEXT NOT NULL,
            default_priority INTEGER NOT NULL,
            default_quality_tier TEXT NOT NULL,
            review_status TEXT NOT NULL,
            requires_manual_approval INTEGER NOT NULL,
            allowed_for_ingestion INTEGER NOT NULL,
            note TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mysticism_concept_relations (
            relation_id TEXT PRIMARY KEY,
            source_key TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            target_key TEXT NOT NULL,
            evidence_level TEXT NOT NULL,
            note TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mysticism_rule_fragments (
            fragment_id TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            title TEXT NOT NULL,
            condition_text TEXT NOT NULL,
            interpretation_text TEXT NOT NULL,
            confidence_level TEXT NOT NULL,
            source_key TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mysticism_case_event_links (
            link_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            event_index INTEGER NOT NULL,
            topic_key TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            note TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mysticism_source_quality_reviews (
            review_id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            source_key TEXT NOT NULL,
            quality_tier TEXT NOT NULL,
            review_scope TEXT NOT NULL,
            review_status TEXT NOT NULL,
            requires_manual_approval INTEGER NOT NULL,
            reviewed_by TEXT NOT NULL,
            reviewer_note TEXT NOT NULL
        );
        """
    )


def reset_tables(conn: sqlite3.Connection) -> None:
    for table in [
        "metadata",
        "mysticism_topics",
        "mysticism_topic_tags",
        "mysticism_topic_related_titles",
        "mysticism_cases",
        "mysticism_case_tags",
        "mysticism_case_events",
        "mysticism_term_aliases",
        "mysticism_source_registry",
        "mysticism_concept_relations",
        "mysticism_rule_fragments",
        "mysticism_case_event_links",
        "mysticism_source_quality_reviews",
    ]:
        conn.execute(f"DELETE FROM {table}")


def insert_topics(conn: sqlite3.Connection, topics: list[dict[str, Any]]) -> None:
    for topic in topics:
        conn.execute(
            """
            INSERT INTO mysticism_topics (
                topic_key, title_zh_hans, title_zh_hant, title_en,
                summary_zh_hans, summary_zh_hant, summary_en, category,
                source_type, source_priority, quality_tier, source_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic["key"],
                topic["title_zh_hans"],
                topic["title_zh_hant"],
                topic["title_en"],
                topic["summary_zh_hans"],
                topic["summary_zh_hant"],
                topic["summary_en"],
                topic["category"],
                topic["source_type"],
                topic["source_priority"],
                topic["quality_tier"],
                topic["source_url"],
            ),
        )
        for tag in topic.get("tags", []):
            conn.execute("INSERT INTO mysticism_topic_tags (topic_key, tag) VALUES (?, ?)", (topic["key"], tag))
        for index, related_title in enumerate(topic.get("related_titles", [])):
            conn.execute(
                "INSERT INTO mysticism_topic_related_titles (topic_key, related_title, display_order) VALUES (?, ?, ?)",
                (topic["key"], related_title, index),
            )


def normalize_event(event: Any) -> tuple[int | None, str, str]:
    if isinstance(event, dict):
        year = event.get("year")
        text = str(event.get("event", "")).strip()
        return (int(year) if isinstance(year, int) else None, text, json.dumps(event, ensure_ascii=False))
    text = str(event).strip()
    return (None, text, json.dumps({"event": text}, ensure_ascii=False))


def build_seed_term_aliases(topics: list[dict[str, Any]]) -> list[dict[str, str]]:
    aliases: list[dict[str, str]] = []
    for topic in topics:
        aliases.append(
            {
                "alias_id": f"{topic['key']}:zh_hans",
                "canonical_key": topic["key"],
                "alias_text": topic["title_zh_hans"],
                "language": "zh-Hans",
                "alias_type": "canonical",
            }
        )
        aliases.append(
            {
                "alias_id": f"{topic['key']}:zh_hant",
                "canonical_key": topic["key"],
                "alias_text": topic["title_zh_hant"],
                "language": "zh-Hant",
                "alias_type": "canonical",
            }
        )
        aliases.append(
            {
                "alias_id": f"{topic['key']}:en",
                "canonical_key": topic["key"],
                "alias_text": topic["title_en"],
                "language": "en",
                "alias_type": "canonical",
            }
        )
    return aliases


def build_seed_source_registry() -> list[dict[str, Any]]:
    return [
        {
            "source_type": "wikipedia",
            "source_name": "Wikipedia",
            "default_priority": 1,
            "default_quality_tier": "A",
            "review_status": "approved",
            "requires_manual_approval": 0,
            "allowed_for_ingestion": 1,
            "note": "一级来源，允许直接入库，作为主题知识的默认结构化入口。",
        },
        {
            "source_type": "wikipedia_seed",
            "source_name": "Wikipedia Seed Case",
            "default_priority": 1,
            "default_quality_tier": "A",
            "review_status": "approved",
            "requires_manual_approval": 0,
            "allowed_for_ingestion": 1,
            "note": "当前案例种子来源，后续应逐步替换为真实可验证案例。",
        },
        {
            "source_type": "external_pending_review",
            "source_name": "External Pending Review",
            "default_priority": 5,
            "default_quality_tier": "C",
            "review_status": "pending",
            "requires_manual_approval": 1,
            "allowed_for_ingestion": 0,
            "note": "除 Wikipedia 外的新来源默认先进入待审核注册态，审核前不得入库。",
        },
    ]


def build_seed_concept_relations(topics: list[dict[str, Any]]) -> list[dict[str, str]]:
    topic_keys = {item["key"] for item in topics}
    relations: list[dict[str, str]] = []
    if {"bazi", "yinyang_wuxing"}.issubset(topic_keys):
        relations.append(
            {
                "relation_id": "bazi-depends-on-wuxing",
                "source_key": "bazi",
                "relation_type": "depends_on",
                "target_key": "yinyang_wuxing",
                "evidence_level": "A",
                "note": "八字解释依赖阴阳五行体系。",
            }
        )
    if {"feng_shui", "kanyu"}.issubset(topic_keys):
        relations.append(
            {
                "relation_id": "fengshui-related-to-kanyu",
                "source_key": "feng_shui",
                "relation_type": "related_to",
                "target_key": "kanyu",
                "evidence_level": "A",
                "note": "风水与堪舆在现代语境中高度相关。",
            }
        )
    if {"yijing", "bazi"}.issubset(topic_keys):
        relations.append(
            {
                "relation_id": "yijing-influences-bazi",
                "source_key": "yijing",
                "relation_type": "influences",
                "target_key": "bazi",
                "evidence_level": "B",
                "note": "易经思想影响八字命理解释框架。",
            }
        )
    return relations


def build_seed_rule_fragments() -> list[dict[str, str]]:
    return [
        {
            "fragment_id": "bazi-day-master-wuxing-balance",
            "domain": "bazi",
            "title": "日主与五行平衡",
            "condition_text": "日主强且同类五行过旺",
            "interpretation_text": "优先关注泄耗与制衡，而不是继续扶助。",
            "confidence_level": "B",
            "source_key": "bazi",
        },
        {
            "fragment_id": "fengshui-entry-flow",
            "domain": "fengshui",
            "title": "入户动线与气流",
            "condition_text": "入户直冲、无遮挡且动线过快",
            "interpretation_text": "常被视为气流不聚，宜设置缓冲或分隔。",
            "confidence_level": "B",
            "source_key": "feng_shui",
        },
    ]


def build_seed_case_event_links(cases: list[dict[str, Any]]) -> list[dict[str, str | int]]:
    links: list[dict[str, str | int]] = []
    for case in cases:
        topic_key = {"bazi": "bazi", "ziwei": "ziwei_doushu", "fengshui": "feng_shui"}[case["case_type"]]
        links.append(
            {
                "link_id": f"{case['case_id']}:seed",
                "case_id": case["case_id"],
                "event_index": 0,
                "topic_key": topic_key,
                "relation_type": "illustrates",
                "note": "占位案例与核心主题的示例关联。",
            }
        )
    return links


def build_seed_source_quality_reviews(topics: list[dict[str, Any]], cases: list[dict[str, Any]]) -> list[dict[str, str]]:
    reviews: list[dict[str, str]] = []
    for topic in topics:
        reviews.append(
            {
                "review_id": f"topic:{topic['key']}",
                "source_type": topic["source_type"],
                "source_key": topic["key"],
                "quality_tier": topic["quality_tier"],
                "review_scope": "topic",
                "review_status": "approved",
                "requires_manual_approval": "0",
                "reviewed_by": "system_seed_policy",
                "reviewer_note": "Wikipedia 主题种子，适合作为一级结构化入口。",
            }
        )
    for case in cases:
        reviews.append(
            {
                "review_id": f"case:{case['case_id']}",
                "source_type": case["source_type"],
                "source_key": case["case_id"],
                "quality_tier": case["quality_tier"],
                "review_scope": "case",
                "review_status": "approved",
                "requires_manual_approval": "0",
                "reviewed_by": "system_seed_policy",
                "reviewer_note": "案例占位种子，后续需用真实可验证案例替换。",
            }
        )
    return reviews


def insert_cases(conn: sqlite3.Connection, cases: list[dict[str, Any]]) -> None:
    for item in cases:
        conn.execute(
            """
            INSERT INTO mysticism_cases (
                case_id, case_type, title_zh_hans, title_zh_hant, title_en,
                summary_zh_hans, summary_zh_hant, summary_en,
                source_url, source_type, source_priority, quality_tier, evidence_level, verification_notes,
                birth_date, birth_time, birth_city, gender, pillars_json, day_master, major_structure,
                property_type, layout_features_json, issue, adjustment, outcome, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["case_id"],
                item["case_type"],
                item["title_zh_hans"],
                item["title_zh_hant"],
                item["title_en"],
                item["summary_zh_hans"],
                item["summary_zh_hant"],
                item["summary_en"],
                item["source_url"],
                item["source_type"],
                item["source_priority"],
                item["quality_tier"],
                item["evidence_level"],
                item["verification_notes"],
                item.get("birth_date"),
                item.get("birth_time"),
                item.get("birth_city"),
                item.get("gender"),
                json.dumps(item.get("pillars", {}), ensure_ascii=False),
                item.get("day_master"),
                item.get("major_structure"),
                item.get("property_type"),
                json.dumps(item.get("layout_features", []), ensure_ascii=False),
                item.get("issue"),
                item.get("adjustment"),
                item.get("outcome"),
                json.dumps(item, ensure_ascii=False),
            ),
        )
        for tag in item.get("tags", []):
            conn.execute("INSERT INTO mysticism_case_tags (case_id, tag) VALUES (?, ?)", (item["case_id"], tag))
        for index, event in enumerate(item.get("events", [])):
            year, text, raw_json = normalize_event(event)
            conn.execute(
                """
                INSERT INTO mysticism_case_events (case_id, event_index, event_year, event_text, raw_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item["case_id"], index, year, text, raw_json),
            )


def insert_term_aliases(conn: sqlite3.Connection, aliases: list[dict[str, str]]) -> None:
    for item in aliases:
        conn.execute(
            """
            INSERT INTO mysticism_term_aliases (alias_id, canonical_key, alias_text, language, alias_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (item["alias_id"], item["canonical_key"], item["alias_text"], item["language"], item["alias_type"]),
        )


def insert_source_registry(conn: sqlite3.Connection, registry_items: list[dict[str, Any]]) -> None:
    for item in registry_items:
        conn.execute(
            """
            INSERT INTO mysticism_source_registry (
                source_type, source_name, default_priority, default_quality_tier,
                review_status, requires_manual_approval, allowed_for_ingestion, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["source_type"],
                item["source_name"],
                item["default_priority"],
                item["default_quality_tier"],
                item["review_status"],
                item["requires_manual_approval"],
                item["allowed_for_ingestion"],
                item["note"],
            ),
        )


def insert_concept_relations(conn: sqlite3.Connection, relations: list[dict[str, str]]) -> None:
    for item in relations:
        conn.execute(
            """
            INSERT INTO mysticism_concept_relations (relation_id, source_key, relation_type, target_key, evidence_level, note)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (item["relation_id"], item["source_key"], item["relation_type"], item["target_key"], item["evidence_level"], item["note"]),
        )


def insert_rule_fragments(conn: sqlite3.Connection, fragments: list[dict[str, str]]) -> None:
    for item in fragments:
        conn.execute(
            """
            INSERT INTO mysticism_rule_fragments (fragment_id, domain, title, condition_text, interpretation_text, confidence_level, source_key)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["fragment_id"],
                item["domain"],
                item["title"],
                item["condition_text"],
                item["interpretation_text"],
                item["confidence_level"],
                item["source_key"],
            ),
        )


def insert_case_event_links(conn: sqlite3.Connection, links: list[dict[str, Any]]) -> None:
    for item in links:
        conn.execute(
            """
            INSERT INTO mysticism_case_event_links (link_id, case_id, event_index, topic_key, relation_type, note)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (item["link_id"], item["case_id"], item["event_index"], item["topic_key"], item["relation_type"], item["note"]),
        )


def insert_source_quality_reviews(conn: sqlite3.Connection, reviews: list[dict[str, str]]) -> None:
    for item in reviews:
        conn.execute(
            """
            INSERT INTO mysticism_source_quality_reviews (
                review_id, source_type, source_key, quality_tier,
                review_scope, review_status, requires_manual_approval, reviewed_by, reviewer_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["review_id"],
                item["source_type"],
                item["source_key"],
                item["quality_tier"],
                item["review_scope"],
                item["review_status"],
                item["requires_manual_approval"],
                item["reviewed_by"],
                item["reviewer_note"],
            ),
        )


def write_metadata(conn: sqlite3.Connection, topics: list[dict[str, Any]], cases: list[dict[str, Any]], source_name: str) -> None:
    metadata = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source_name": source_name,
        "topic_count": str(len(topics)),
        "case_count": str(len(cases)),
    }
    for key, value in metadata.items():
        conn.execute("INSERT INTO metadata (key, value) VALUES (?, ?)", (key, value))


def build_database(input_path: Path, output_path: Path, seed_only: bool = False) -> dict[str, int]:
    payload = load_payload(input_path, seed_only=seed_only)
    topics = payload.get("topics", [])
    cases = payload.get("cases", [])
    source_registry = payload.get("source_registry", build_seed_source_registry())
    term_aliases = payload.get("term_aliases", build_seed_term_aliases(topics))
    concept_relations = payload.get("concept_relations", build_seed_concept_relations(topics))
    rule_fragments = payload.get("rule_fragments", build_seed_rule_fragments())
    case_event_links = payload.get("case_event_links", build_seed_case_event_links(cases))
    source_quality_reviews = payload.get("source_quality_reviews", build_seed_source_quality_reviews(topics, cases))
    conn = connect_database(output_path)
    try:
        rebuild_evolving_tables(conn)
        create_schema(conn)
        reset_tables(conn)
        insert_topics(conn, topics)
        insert_cases(conn, cases)
        insert_term_aliases(conn, term_aliases)
        insert_source_registry(conn, source_registry)
        insert_concept_relations(conn, concept_relations)
        insert_rule_fragments(conn, rule_fragments)
        insert_case_event_links(conn, case_event_links)
        insert_source_quality_reviews(conn, source_quality_reviews)
        write_metadata(conn, topics, cases, "seed_only" if seed_only or not input_path.exists() else str(input_path))
        conn.commit()
    finally:
        conn.close()
    return {
        "topics": len(topics),
        "cases": len(cases),
        "source_registry": len(source_registry),
        "term_aliases": len(term_aliases),
        "concept_relations": len(concept_relations),
        "rule_fragments": len(rule_fragments),
        "case_event_links": len(case_event_links),
        "source_quality_reviews": len(source_quality_reviews),
    }


def main() -> int:
    args = parse_args()
    summary = build_database(args.input, args.output, seed_only=args.seed_only)
    print(f"输出完成：{args.output}")
    print(f"主题条数：{summary['topics']}")
    print(f"案例条数：{summary['cases']}")
    print(f"来源条数：{summary['source_registry']}")
    print(f"别名条数：{summary['term_aliases']}")
    print(f"关系条数：{summary['concept_relations']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
