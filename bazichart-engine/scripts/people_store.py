from __future__ import annotations

import json
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "data"
DEFAULT_DB = DATA_DIR / "people_pipeline.db"
DEFAULT_UNIFIED_OUTPUT = DATA_DIR / "unified_people_sqlite.json"
DEFAULT_REPORT_OUTPUT = DATA_DIR / "people_pipeline_sqlite_report.json"


def connect_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS people_raw (
            source TEXT NOT NULL,
            source_key TEXT NOT NULL,
            identity_key TEXT NOT NULL,
            name_en TEXT,
            name_zh TEXT,
            birth_date TEXT,
            birth_time TEXT,
            birth_time_reliability TEXT,
            birth_time_source TEXT,
            birth_city TEXT,
            birth_country TEXT,
            gender TEXT,
            occupation_json TEXT NOT NULL,
            bio TEXT,
            notable_events_json TEXT NOT NULL,
            source_url TEXT,
            data_quality_score REAL NOT NULL,
            rodden_rating TEXT,
            raw_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (source, source_key)
        );

        CREATE INDEX IF NOT EXISTS idx_people_raw_identity
        ON people_raw(identity_key, data_quality_score DESC);
        """
    )


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(normalized.split()).casefold()


def identity_key(name_en: str | None, name_zh: str | None, birth_date: str | None) -> str:
    primary_name = normalize_name(name_en) or normalize_name(name_zh)
    return f"{primary_name}|{birth_date or ''}"


def source_key_for_record(record: dict[str, Any]) -> str:
    urls = record.get("source_urls") or []
    if urls:
        return urls[0]
    if record.get("source_url"):
        return str(record["source_url"])
    if record.get("id"):
        return str(record["id"])
    return f"{record.get('name_en') or record.get('name_zh') or 'unknown'}|{record.get('birth_date') or ''}"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def upsert_records(conn: sqlite3.Connection, source: str, records: list[dict[str, Any]]) -> int:
    rows = []
    for item in records:
        item_identity = identity_key(item.get("name_en"), item.get("name_zh"), item.get("birth_date"))
        rows.append(
            (
                source,
                source_key_for_record(item),
                item_identity,
                item.get("name_en"),
                item.get("name_zh"),
                item.get("birth_date"),
                item.get("birth_time"),
                item.get("birth_time_reliability"),
                item.get("birth_time_source"),
                item.get("birth_city"),
                item.get("birth_country"),
                item.get("gender"),
                json.dumps(item.get("occupation", []), ensure_ascii=False),
                item.get("bio"),
                json.dumps(item.get("notable_events", []), ensure_ascii=False),
                item.get("source_url") or ((item.get("source_urls") or [""])[0]),
                float(item.get("data_quality_score", 0.5) or 0.5),
                item.get("rodden_rating"),
                json.dumps(item, ensure_ascii=False),
            )
        )
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
    return len(rows)


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


def build_report(
    conn: sqlite3.Connection,
    unified_records: list[dict[str, Any]],
    source_imported_counts: dict[str, int],
) -> dict[str, Any]:
    raw_total = conn.execute("SELECT COUNT(*) FROM people_raw").fetchone()[0]
    timed_total = sum(1 for item in unified_records if item.get("birth_time"))
    high_conf_total = sum(1 for item in unified_records if item.get("birth_time_reliability") == "high")
    source_counts = {
        row["source"]: row["count"]
        for row in conn.execute("SELECT source, COUNT(*) AS count FROM people_raw GROUP BY source ORDER BY count DESC")
    }
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "raw_total": raw_total,
        "unified_total": len(unified_records),
        "timed_total": timed_total,
        "high_confidence_timed_total": high_conf_total,
        "source_raw_counts": source_counts,
        "source_imported_counts": source_imported_counts,
    }


def sync_source_snapshots(
    db_path: Path,
    source_records: dict[str, list[dict[str, Any]]],
    *,
    unified_output: Path = DEFAULT_UNIFIED_OUTPUT,
    report_output: Path = DEFAULT_REPORT_OUTPUT,
) -> dict[str, Any]:
    conn = connect_database(db_path)
    try:
        create_schema(conn)
        imported_counts = {source: upsert_records(conn, source, records) for source, records in source_records.items()}
        conn.commit()
        unified_records = export_unified(conn)
        write_json(unified_output, unified_records)
        report = build_report(conn, unified_records, imported_counts)
        write_json(report_output, report)
        return report
    finally:
        conn.close()
