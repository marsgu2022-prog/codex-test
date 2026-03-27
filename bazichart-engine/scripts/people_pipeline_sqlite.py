#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from people_store import (
    DEFAULT_DB,
    DEFAULT_REPORT_OUTPUT,
    DEFAULT_UNIFIED_OUTPUT,
    build_report,
    connect_database,
    create_schema,
    export_unified,
    write_json,
)
DATA_DIR = SCRIPT_DIR.parent / "data"


@dataclass(frozen=True)
class SourceConfig:
    name: str
    path: Path


SOURCE_CONFIGS = {
    "astrodatabank_a": SourceConfig("astrodatabank_a", DATA_DIR / "famous_people_astro.json"),
    "astrodatabank_b": SourceConfig("astrodatabank_b", DATA_DIR / "famous_people_astro_b.json"),
    "astrotheme": SourceConfig("astrotheme", DATA_DIR / "famous_people_astrotheme.json"),
    "wikipedia": SourceConfig("wikipedia", DATA_DIR / "famous_people.json"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将多路名人数据导入 SQLite 并导出统一名人库")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--sources", nargs="+", choices=sorted(SOURCE_CONFIGS), default=list(SOURCE_CONFIGS))
    parser.add_argument("--export-unified", type=Path, default=DEFAULT_UNIFIED_OUTPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(normalized.split()).casefold()


def identity_key(name_en: str | None, name_zh: str | None, birth_date: str | None) -> str:
    primary_name = normalize_name(name_en) or normalize_name(name_zh)
    return f"{primary_name}|{birth_date or ''}"


def source_key_for_record(source: str, record: dict[str, Any]) -> str:
    if source == "wikipedia":
        return record.get("id") or str(uuid.uuid4())
    urls = record.get("source_urls") or []
    if urls:
        return urls[0]
    return f"{record.get('name_en') or record.get('name_zh') or 'unknown'}|{record.get('birth_date') or ''}"


def map_record(source: str, item: dict[str, Any]) -> dict[str, Any]:
    if source == "wikipedia":
        source_info = item.get("source", {})
        source_url = source_info.get("url", "") if isinstance(source_info, dict) else ""
        birth_time = None
        birth_hour = item.get("birth_hour")
        if item.get("has_birth_hour") and birth_hour is not None:
            if isinstance(birth_hour, str) and ":" in birth_hour:
                birth_time = birth_hour
            elif isinstance(birth_hour, (int, float)):
                birth_time = f"{int(birth_hour):02d}:00"
        return {
            "source": source,
            "source_key": source_key_for_record(source, item),
            "name_en": item.get("name_en", ""),
            "name_zh": item.get("name_zh") or item.get("name_zh_hans"),
            "birth_date": item.get("birth_date"),
            "birth_time": birth_time,
            "birth_time_reliability": "low" if birth_time else "unknown",
            "birth_time_source": "wikipedia" if birth_time else None,
            "birth_city": "",
            "birth_country": item.get("nationality_en", ""),
            "gender": item.get("gender", ""),
            "occupation": item.get("occupation", []) if isinstance(item.get("occupation", []), list) else [item.get("occupation")],
            "bio": item.get("bio_en") or item.get("summary") or "",
            "notable_events": [],
            "source_url": source_url,
            "data_quality_score": 0.5 if birth_time else 0.3,
            "rodden_rating": None,
            "raw_json": item,
        }
    return {
        "source": source,
        "source_key": source_key_for_record(source, item),
        "name_en": item.get("name_en", ""),
        "name_zh": item.get("name_zh"),
        "birth_date": item.get("birth_date"),
        "birth_time": item.get("birth_time"),
        "birth_time_reliability": item.get("birth_time_reliability", "unknown"),
        "birth_time_source": item.get("birth_time_source"),
        "birth_city": item.get("birth_city", ""),
        "birth_country": item.get("birth_country", ""),
        "gender": item.get("gender", ""),
        "occupation": item.get("occupation", []),
        "bio": item.get("bio", ""),
        "notable_events": item.get("notable_events", []),
        "source_url": (item.get("source_urls") or [""])[0],
        "data_quality_score": float(item.get("data_quality_score", 0.5) or 0.5),
        "rodden_rating": item.get("rodden_rating"),
        "raw_json": item,
    }


def import_source(conn: sqlite3.Connection, source: str, path: Path) -> int:
    if not path.exists():
        return 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return 0
    imported = 0
    rows = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        mapped = map_record(source, item)
        mapped["identity_key"] = identity_key(mapped["name_en"], mapped["name_zh"], mapped["birth_date"])
        rows.append(
            (
                mapped["source"],
                mapped["source_key"],
                mapped["identity_key"],
                mapped["name_en"],
                mapped["name_zh"],
                mapped["birth_date"],
                mapped["birth_time"],
                mapped["birth_time_reliability"],
                mapped["birth_time_source"],
                mapped["birth_city"],
                mapped["birth_country"],
                mapped["gender"],
                json.dumps(mapped["occupation"], ensure_ascii=False),
                mapped["bio"],
                json.dumps(mapped["notable_events"], ensure_ascii=False),
                mapped["source_url"],
                mapped["data_quality_score"],
                mapped["rodden_rating"],
                json.dumps(mapped["raw_json"], ensure_ascii=False),
            )
        )
        imported += 1
    conn.executemany(
        """
        INSERT INTO people_raw (
            source, source_key, identity_key, name_en, name_zh, birth_date, birth_time,
            birth_time_reliability, birth_time_source, birth_city, birth_country, gender,
            occupation_json, bio, notable_events_json, source_url, data_quality_score,
            rodden_rating, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source, source_key) DO UPDATE SET
            identity_key=excluded.identity_key,
            name_en=excluded.name_en,
            name_zh=excluded.name_zh,
            birth_date=excluded.birth_date,
            birth_time=excluded.birth_time,
            birth_time_reliability=excluded.birth_time_reliability,
            birth_time_source=excluded.birth_time_source,
            birth_city=excluded.birth_city,
            birth_country=excluded.birth_country,
            gender=excluded.gender,
            occupation_json=excluded.occupation_json,
            bio=excluded.bio,
            notable_events_json=excluded.notable_events_json,
            source_url=excluded.source_url,
            data_quality_score=excluded.data_quality_score,
            rodden_rating=excluded.rodden_rating,
            raw_json=excluded.raw_json,
            updated_at=CURRENT_TIMESTAMP
        """,
        rows,
    )
    return imported


def export_unified(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        WITH ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY identity_key
                    ORDER BY data_quality_score DESC, birth_time DESC, source ASC
                ) AS rank_no,
                COUNT(*) OVER (PARTITION BY identity_key) AS source_count
            FROM people_raw
        )
        SELECT * FROM ranked
        WHERE rank_no = 1
        ORDER BY data_quality_score DESC, birth_date ASC, name_en ASC
        """
    ).fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        results.append(
            {
                "id": row["identity_key"],
                "name_en": row["name_en"],
                "name_zh": row["name_zh"],
                "birth_date": row["birth_date"],
                "birth_time": row["birth_time"],
                "birth_time_reliability": row["birth_time_reliability"],
                "birth_time_source": row["birth_time_source"],
                "birth_city": row["birth_city"],
                "birth_country": row["birth_country"],
                "gender": row["gender"],
                "occupation": json.loads(row["occupation_json"]),
                "bio": row["bio"],
                "notable_events": json.loads(row["notable_events_json"]),
                "source": row["source"],
                "source_url": row["source_url"],
                "data_quality_score": row["data_quality_score"],
                "rodden_rating": row["rodden_rating"],
                "source_count": row["source_count"],
            }
        )
    return results


def build_report(conn: sqlite3.Connection, unified_records: list[dict[str, Any]], imported_counts: dict[str, int]) -> dict[str, Any]:
    raw_total = conn.execute("SELECT COUNT(*) FROM people_raw").fetchone()[0]
    timed_total = sum(1 for item in unified_records if item.get("birth_time"))
    high_conf_total = sum(1 for item in unified_records if item.get("birth_time_reliability") == "high")
    source_counts = {
        row["source"]: row["count"]
        for row in conn.execute("SELECT source, COUNT(*) AS count FROM people_raw GROUP BY source ORDER BY count DESC")
    }
    return {
        "generated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "raw_total": raw_total,
        "unified_total": len(unified_records),
        "timed_total": timed_total,
        "high_confidence_timed_total": high_conf_total,
        "source_raw_counts": source_counts,
        "source_imported_counts": imported_counts,
    }


def main() -> None:
    args = parse_args()
    conn = connect_database(args.db)
    try:
        create_schema(conn)
        imported_counts: dict[str, int] = {}
        for source in args.sources:
            imported_counts[source] = import_source(conn, source, SOURCE_CONFIGS[source].path)
        conn.commit()
        unified_records = export_unified(conn)
        write_json(args.export_unified, unified_records)
        report = build_report(conn, unified_records, imported_counts)
        write_json(args.report_output, report)
        print(f"sqlite_raw_total={report['raw_total']}")
        print(f"sqlite_unified_total={report['unified_total']}")
        print(f"sqlite_timed_total={report['timed_total']}")
        print(f"sqlite_high_conf_timed_total={report['high_confidence_timed_total']}")
        print(f"sqlite_db={args.db}")
        print(f"unified_output={args.export_unified}")
        print(f"report_output={args.report_output}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
