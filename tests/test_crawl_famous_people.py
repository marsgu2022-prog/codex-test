from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "scripts" / "crawl_famous_people.py"
SPEC = importlib.util.spec_from_file_location("crawl_famous_people", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_parse_birth_datetime_respects_precision():
    parsed = MODULE.parse_birth_datetime("+1893-12-26T00:00:00Z", 11)
    assert parsed == {
        "year": 1893,
        "month": 12,
        "day": 26,
        "hour": None,
        "minute": 0,
        "second": 0,
        "precision": 11,
    }


def test_build_pillars_and_day_master_are_stable():
    birth = {"year": 1893, "month": 12, "day": 26, "hour": None, "minute": 0, "second": 0, "precision": 11}
    pillars = MODULE.build_pillars(birth)
    assert pillars["year"]
    assert pillars["month"]
    assert pillars["day"]
    assert pillars["hour"] is None
    assert len(pillars["day"]) == 2


def test_build_day_pillar_index_groups_people():
    people = [
        {
            "id": "Q1",
            "name_zh": "甲",
            "name_en": "A",
            "birth_date": "1900-01-01",
            "nationality_zh": "中国",
            "field_zh": "政治家",
            "summary": "简介",
            "day_pillar": "甲子",
        },
        {
            "id": "Q2",
            "name_zh": "乙",
            "name_en": "B",
            "birth_date": "1900-01-02",
            "nationality_zh": "美国",
            "field_zh": "科学家",
            "summary": "简介",
            "day_pillar": "甲子",
        },
    ]
    index = MODULE.build_day_pillar_index(people)
    assert list(index) == ["甲子"]
    assert len(index["甲子"]) == 2


def test_validate_people_flags_missing_required_fields():
    people = [
        {
            "id": "Q1",
            "name_zh": "甲",
            "name_en": "A",
            "birth_date": "1900-01-01",
            "day_pillar": "甲子",
            "day_master": "甲",
        },
        {
            "id": "Q2",
            "name_zh": "",
            "name_en": "B",
            "birth_date": "1900-01-02",
            "day_pillar": "乙丑",
            "day_master": "乙",
        },
    ]
    summary = MODULE.validate_people(people)
    assert summary["total_people"] == 2
    assert summary["invalid_count"] == 1
    assert summary["invalid_ids"] == ["Q2"]


def test_build_runtime_configs_smoke_uses_small_scope():
    configs, min_total_people, output_suffix = MODULE.build_runtime_configs("smoke")
    assert min_total_people == MODULE.SMOKE_MIN_TOTAL_PEOPLE
    assert output_suffix == "_smoke"
    assert configs["china_like"]["country_qids"] == MODULE.CHINA_LIKE_QIDS[:1]
    assert configs["china_like"]["occupations"] == ["politician", "writer"]
    assert configs["china_like"]["pages"] == 1
    assert configs["china_like"]["per_query_limit"] == 5
    assert configs["western"]["extra_country_names"] == []


def test_build_runtime_configs_full_preserves_default_scope():
    configs, min_total_people, output_suffix = MODULE.build_runtime_configs("full")
    assert min_total_people == MODULE.MIN_TOTAL_PEOPLE
    assert output_suffix == ""
    assert configs["western"]["country_qids"] == MODULE.WESTERN_COUNTRY_QIDS
    assert configs["global_extra"]["pages"] == MODULE.COHORT_CONFIGS["global_extra"]["pages"]


def test_pipeline_state_records_cache_and_failure_queue(tmp_path):
    original_file = MODULE.__file__
    try:
        MODULE.__file__ = str(tmp_path / "scripts" / "crawl_famous_people.py")
        state = MODULE.load_pipeline_state("_smoke")
        job = MODULE.build_query_job("western", "en", "Q30", "scientist", 5, 0)

        MODULE.cache_query_rows(state, job, [{"person": {"value": "https://www.wikidata.org/entity/Q1"}}])
        MODULE.record_failed_job(state, job, "timeout")

        reloaded = MODULE.load_pipeline_state("_smoke")
        assert MODULE.get_cached_rows(reloaded, job) == [{"person": {"value": "https://www.wikidata.org/entity/Q1"}}]
        assert len(reloaded["failure_queue"]["jobs"]) == 1
        assert reloaded["failure_queue"]["jobs"][0]["error"] == "timeout"
    finally:
        MODULE.__file__ = original_file


def test_clear_failed_job_and_pipeline_summary(tmp_path):
    original_file = MODULE.__file__
    try:
        MODULE.__file__ = str(tmp_path / "scripts" / "crawl_famous_people.py")
        state = MODULE.load_pipeline_state("_smoke")
        job = MODULE.build_query_job("china_like", "zh", "Q148", "writer", 5, 0)

        MODULE.cache_query_rows(state, job, [])
        MODULE.record_failed_job(state, job, "dns")
        MODULE.clear_failed_job(state, job)

        summary = MODULE.build_pipeline_summary(state)
        assert summary == {"candidate_pages": 1, "failed_jobs": 0}
    finally:
        MODULE.__file__ = original_file
