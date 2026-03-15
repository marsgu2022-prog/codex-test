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
    return {"topics": topics, "cases": cases}


def load_payload(input_path: Path, seed_only: bool = False) -> dict[str, Any]:
    if not seed_only and input_path.exists():
        return read_json(input_path)
    return build_seed_payload()


def connect_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


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
    conn = connect_database(output_path)
    try:
        create_schema(conn)
        reset_tables(conn)
        insert_topics(conn, topics)
        insert_cases(conn, cases)
        write_metadata(conn, topics, cases, "seed_only" if seed_only or not input_path.exists() else str(input_path))
        conn.commit()
    finally:
        conn.close()
    return {"topics": len(topics), "cases": len(cases)}


def main() -> int:
    args = parse_args()
    summary = build_database(args.input, args.output, seed_only=args.seed_only)
    print(f"输出完成：{args.output}")
    print(f"主题条数：{summary['topics']}")
    print(f"案例条数：{summary['cases']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
