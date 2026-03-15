from importlib.util import module_from_spec, spec_from_file_location
import sqlite3
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "scripts" / "build_mysticism_database.py"
SPEC = spec_from_file_location("build_mysticism_database", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["build_mysticism_database"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_build_database_from_seed_payload(tmp_path):
    db_path = tmp_path / "mysticism_library.db"

    summary = MODULE.build_database(tmp_path / "missing.json", db_path, seed_only=True)

    assert summary == {"topics": len(MODULE.MYSTICISM_MODULE.TOPIC_SEEDS), "cases": len(MODULE.MYSTICISM_MODULE.CASE_SEEDS)}
    conn = sqlite3.connect(db_path)
    try:
        topic_count = conn.execute("SELECT COUNT(*) FROM mysticism_topics").fetchone()[0]
        case_count = conn.execute("SELECT COUNT(*) FROM mysticism_cases").fetchone()[0]
        topic_source = conn.execute("SELECT source_type, source_priority, quality_tier FROM mysticism_topics LIMIT 1").fetchone()
        case_source = conn.execute("SELECT source_type, source_priority, quality_tier FROM mysticism_cases LIMIT 1").fetchone()
        metadata = dict(conn.execute("SELECT key, value FROM metadata").fetchall())
    finally:
        conn.close()

    assert topic_count == len(MODULE.MYSTICISM_MODULE.TOPIC_SEEDS)
    assert case_count == len(MODULE.MYSTICISM_MODULE.CASE_SEEDS)
    assert topic_source == ("wikipedia", 1, "A")
    assert case_source == ("wikipedia_seed", 1, "A")
    assert metadata["source_name"] == "seed_only"


def test_normalize_event_supports_dict_and_string():
    dict_event = MODULE.normalize_event({"year": 2007, "event": "发布 iPhone"})
    text_event = MODULE.normalize_event("搬家后财运改善")

    assert dict_event[0] == 2007
    assert dict_event[1] == "发布 iPhone"
    assert text_event[0] is None
    assert text_event[1] == "搬家后财运改善"
