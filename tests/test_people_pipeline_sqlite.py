from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import json
import sys


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "scripts" / "people_pipeline_sqlite.py"
SPEC = spec_from_file_location("people_pipeline_sqlite", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["people_pipeline_sqlite"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_import_and_export_unified_prefers_higher_quality(tmp_path):
    db_path = tmp_path / "people.db"
    astro_path = tmp_path / "astro.json"
    wiki_path = tmp_path / "wiki.json"

    astro_path.write_text(json.dumps([
        {
            "name_en": "Jane Doe",
            "birth_date": "1980-01-02",
            "birth_time": "08:30",
            "birth_time_reliability": "high",
            "birth_city": "Paris",
            "birth_country": "France",
            "occupation": ["作家"],
            "bio": "High quality source",
            "notable_events": [],
            "source_urls": ["https://astro.example/jane"],
            "data_quality_score": 0.9,
            "rodden_rating": "AA",
        }
    ], ensure_ascii=False), encoding="utf-8")
    wiki_path.write_text(json.dumps([
        {
            "id": "wiki-jane",
            "name_en": "Jane Doe",
            "birth_date": "1980-01-02",
            "has_birth_hour": False,
            "occupation": ["演员"],
            "bio_en": "Low quality source",
            "nationality_en": "France",
            "source": {"url": "https://wiki.example/jane"},
        }
    ], ensure_ascii=False), encoding="utf-8")

    conn = MODULE.connect_database(db_path)
    try:
        MODULE.create_schema(conn)
        assert MODULE.import_source(conn, "astrodatabank_a", astro_path) == 1
        assert MODULE.import_source(conn, "wikipedia", wiki_path) == 1
        conn.commit()

        unified = MODULE.export_unified(conn)
        report = MODULE.build_report(
            conn,
            unified,
            {"astrodatabank_a": 1, "wikipedia": 1},
        )
    finally:
        conn.close()

    assert len(unified) == 1
    assert unified[0]["name_en"] == "Jane Doe"
    assert unified[0]["birth_time"] == "08:30"
    assert unified[0]["source"] == "astrodatabank_a"
    assert unified[0]["source_count"] == 2
    assert report["raw_total"] == 2
    assert report["unified_total"] == 1
    assert report["timed_total"] == 1
    assert report["high_confidence_timed_total"] == 1


def test_identity_key_falls_back_to_chinese_name():
    key = MODULE.identity_key(None, "张 三", "1990-05-06")
    assert key == "张三|1990-05-06"


def test_people_store_session_updates_outputs(tmp_path):
    store_module_path = Path(__file__).resolve().parents[1] / "bazichart-engine" / "scripts" / "people_store.py"
    spec = spec_from_file_location("people_store", store_module_path)
    store_module = module_from_spec(spec)
    sys.modules["people_store"] = store_module
    assert spec and spec.loader
    spec.loader.exec_module(store_module)

    store = store_module.PeopleStoreSession(
        tmp_path / "people.db",
        unified_output=tmp_path / "unified.json",
        report_output=tmp_path / "report.json",
    )
    try:
        inserted = store.upsert(
            "astrotheme",
            [{
                "name_en": "Live Person",
                "birth_date": "2001-02-03",
                "birth_time": "09:00",
                "birth_time_reliability": "high",
                "source_urls": ["https://example.com/live"],
                "occupation": ["作家"],
                "notable_events": [],
                "data_quality_score": 0.8,
            }],
            refresh_outputs=True,
        )
    finally:
        store.close()

    assert inserted == 1
    assert (tmp_path / "unified.json").exists()
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["raw_total"] == 1
    assert report["unified_total"] == 1
