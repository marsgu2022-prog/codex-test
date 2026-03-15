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

    assert summary["topics"] == len(MODULE.MYSTICISM_MODULE.TOPIC_SEEDS)
    assert summary["cases"] == len(MODULE.MYSTICISM_MODULE.CASE_SEEDS)
    assert summary["source_registry"] >= 3
    assert summary["term_aliases"] >= len(MODULE.MYSTICISM_MODULE.TOPIC_SEEDS) * 3
    assert summary["concept_relations"] >= 2
    assert summary["rule_fragments"] >= 2
    conn = sqlite3.connect(db_path)
    try:
        topic_count = conn.execute("SELECT COUNT(*) FROM mysticism_topics").fetchone()[0]
        case_count = conn.execute("SELECT COUNT(*) FROM mysticism_cases").fetchone()[0]
        source_registry_count = conn.execute("SELECT COUNT(*) FROM mysticism_source_registry").fetchone()[0]
        alias_count = conn.execute("SELECT COUNT(*) FROM mysticism_term_aliases").fetchone()[0]
        relation_count = conn.execute("SELECT COUNT(*) FROM mysticism_concept_relations").fetchone()[0]
        rule_count = conn.execute("SELECT COUNT(*) FROM mysticism_rule_fragments").fetchone()[0]
        review_count = conn.execute("SELECT COUNT(*) FROM mysticism_source_quality_reviews").fetchone()[0]
        topic_source = conn.execute("SELECT source_type, source_priority, quality_tier FROM mysticism_topics LIMIT 1").fetchone()
        case_source = conn.execute("SELECT source_type, source_priority, quality_tier FROM mysticism_cases LIMIT 1").fetchone()
        wikipedia_registry = conn.execute(
            """
            SELECT source_name, default_priority, default_quality_tier, review_status,
                   requires_manual_approval, allowed_for_ingestion
            FROM mysticism_source_registry
            WHERE source_type = 'wikipedia'
            """
        ).fetchone()
        pending_registry = conn.execute(
            """
            SELECT review_status, requires_manual_approval, allowed_for_ingestion
            FROM mysticism_source_registry
            WHERE source_type = 'external_pending_review'
            """
        ).fetchone()
        review_row = conn.execute(
            """
            SELECT review_scope, review_status, requires_manual_approval, reviewed_by
            FROM mysticism_source_quality_reviews
            WHERE review_id LIKE 'topic:%'
            LIMIT 1
            """
        ).fetchone()
        metadata = dict(conn.execute("SELECT key, value FROM metadata").fetchall())
    finally:
        conn.close()

    assert topic_count == len(MODULE.MYSTICISM_MODULE.TOPIC_SEEDS)
    assert case_count == len(MODULE.MYSTICISM_MODULE.CASE_SEEDS)
    assert source_registry_count >= 3
    assert alias_count >= len(MODULE.MYSTICISM_MODULE.TOPIC_SEEDS) * 3
    assert relation_count >= 2
    assert rule_count >= 2
    assert review_count == topic_count + case_count
    assert topic_source == ("wikipedia", 1, "A")
    assert case_source == ("wikipedia_seed", 1, "A")
    assert wikipedia_registry == ("Wikipedia", 1, "A", "approved", 0, 1)
    assert pending_registry == ("pending", 1, 0)
    assert review_row == ("topic", "approved", 0, "system_seed_policy")
    assert metadata["source_name"] == "seed_only"


def test_normalize_event_supports_dict_and_string():
    dict_event = MODULE.normalize_event({"year": 2007, "event": "发布 iPhone"})
    text_event = MODULE.normalize_event("搬家后财运改善")

    assert dict_event[0] == 2007
    assert dict_event[1] == "发布 iPhone"
    assert text_event[0] is None
    assert text_event[1] == "搬家后财运改善"


def test_seed_metadata_builders_return_expected_shapes():
    topics = [MODULE.MYSTICISM_MODULE.build_library_record(seed, None, None, [], []) for seed in MODULE.MYSTICISM_MODULE.TOPIC_SEEDS]
    cases = MODULE.MYSTICISM_MODULE.build_case_library()

    aliases = MODULE.build_seed_term_aliases(topics)
    relations = MODULE.build_seed_concept_relations(topics)
    fragments = MODULE.build_seed_rule_fragments()
    links = MODULE.build_seed_case_event_links(cases)
    registry = MODULE.build_seed_source_registry()
    reviews = MODULE.build_seed_source_quality_reviews(topics, cases)

    assert aliases[0]["canonical_key"]
    assert relations[0]["relation_type"]
    assert fragments[0]["domain"]
    assert links[0]["topic_key"]
    assert any(item["source_type"] == "wikipedia" and item["allowed_for_ingestion"] == 1 for item in registry)
    assert any(item["source_type"] == "external_pending_review" and item["requires_manual_approval"] == 1 for item in registry)
    assert reviews[0]["review_status"] == "approved"
    assert reviews[0]["reviewed_by"] == "system_seed_policy"
    assert len(reviews) == len(topics) + len(cases)
