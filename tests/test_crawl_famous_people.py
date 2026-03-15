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
            "occupation": ["政治家"],
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
            "occupation": ["科学家"],
            "field_zh": "科学家",
            "summary": "简介",
            "day_pillar": "甲子",
        },
    ]
    index = MODULE.build_day_pillar_index(people)
    assert list(index) == ["甲子"]
    assert len(index["甲子"]) == 2


def test_classify_occupations_maps_standard_categories():
    occupations = MODULE.classify_occupations(
        [MODULE.OCCUPATION_QIDS["mathematician"], MODULE.OCCUPATION_QIDS["writer"]],
        ["数学家", "作家"],
        ["mathematician", "writer"],
    )
    assert occupations == ["科学家", "作家"]


def test_classify_occupations_uses_keyword_fallback():
    occupations = MODULE.classify_occupations([], ["奥运选手", "钢琴家"], ["Olympic athlete", "pianist"])
    assert occupations == ["运动员", "音乐家"]


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


def test_build_runtime_configs_scientists_focus_limits_occupations():
    configs, min_total_people, output_suffix = MODULE.build_runtime_configs("full", "scientists")
    assert min_total_people == MODULE.MIN_TOTAL_PEOPLE_SCIENTISTS
    assert output_suffix == "_scientists"
    assert configs["china_like"]["occupations"] == MODULE.SCIENTIST_OCCUPATIONS
    assert configs["western"]["occupations"] == MODULE.SCIENTIST_OCCUPATIONS


def test_build_runtime_configs_scientists_smoke_has_distinct_suffix():
    configs, min_total_people, output_suffix = MODULE.build_runtime_configs("smoke", "scientists")
    assert min_total_people == MODULE.SMOKE_MIN_TOTAL_PEOPLE
    assert output_suffix == "_scientists_smoke"
    assert configs["global_extra"]["occupations"] == MODULE.SCIENTIST_OCCUPATIONS
    assert configs["global_extra"]["country_qids"] == MODULE.GLOBAL_EXTRA_COUNTRY_QIDS[:1]


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

        summary = MODULE.build_pipeline_summary(state, now=0)
        assert summary == {"candidate_pages": 1, "failed_jobs": 0, "ready_failed_jobs": 0}
    finally:
        MODULE.__file__ = original_file


def test_collect_cached_rows_merges_all_pages(tmp_path):
    original_file = MODULE.__file__
    try:
        MODULE.__file__ = str(tmp_path / "scripts" / "crawl_famous_people.py")
        state = MODULE.load_pipeline_state("_smoke")
        job1 = MODULE.build_query_job("china_like", "zh", "Q148", "politician", 5, 0)
        job2 = MODULE.build_query_job("western", "en", "Q30", "scientist", 5, 0)
        MODULE.cache_query_rows(state, job1, [{"person": {"value": "https://www.wikidata.org/entity/Q1"}}])
        MODULE.cache_query_rows(state, job2, [{"person": {"value": "https://www.wikidata.org/entity/Q2"}}])

        rows = MODULE.collect_cached_rows(state)
        assert rows == [
            {"person": {"value": "https://www.wikidata.org/entity/Q1"}, "_cohort": "china_like"},
            {"person": {"value": "https://www.wikidata.org/entity/Q2"}, "_cohort": "western"},
        ]
    finally:
        MODULE.__file__ = original_file


def test_retry_failed_jobs_updates_cache_and_clears_queue(tmp_path, monkeypatch):
    original_file = MODULE.__file__
    try:
        MODULE.__file__ = str(tmp_path / "scripts" / "crawl_famous_people.py")
        state = MODULE.load_pipeline_state("_smoke")
        job = MODULE.build_query_job("western", "en", "Q30", "politician", 5, 0)
        MODULE.record_failed_job(state, job, "timeout")

        monkeypatch.setattr(
            MODULE,
            "query_wikidata",
            lambda session, query: [{"person": {"value": "https://www.wikidata.org/entity/Q3"}}],
        )
        state["failure_queue"]["jobs"][0]["next_retry_at"] = 0

        retried = MODULE.retry_failed_jobs(object(), state)
        assert retried == {"western": [{"person": {"value": "https://www.wikidata.org/entity/Q3"}}]}
        assert MODULE.get_cached_rows(state, job) == [{"person": {"value": "https://www.wikidata.org/entity/Q3"}}]
        assert state["failure_queue"]["jobs"] == []
    finally:
        MODULE.__file__ = original_file


def test_record_failed_job_updates_attempts_and_cooldown(tmp_path, monkeypatch):
    original_file = MODULE.__file__
    try:
        MODULE.__file__ = str(tmp_path / "scripts" / "crawl_famous_people.py")
        monkeypatch.setattr(MODULE.time, "time", lambda: 1000)
        state = MODULE.load_pipeline_state("_smoke")
        job = MODULE.build_query_job("western", "en", "Q30", "politician", 5, 0)

        MODULE.record_failed_job(state, job, "504 Gateway Timeout")
        first = state["failure_queue"]["jobs"][0]
        assert first["attempt_count"] == 1
        assert first["next_retry_at"] == 1600

        MODULE.record_failed_job(state, job, "504 Gateway Timeout")
        second = state["failure_queue"]["jobs"][0]
        assert second["attempt_count"] == 2
        assert second["next_retry_at"] == 2200
    finally:
        MODULE.__file__ = original_file


def test_get_retryable_failure_jobs_sorts_ready_items(tmp_path):
    original_file = MODULE.__file__
    try:
        MODULE.__file__ = str(tmp_path / "scripts" / "crawl_famous_people.py")
        state = MODULE.load_pipeline_state("_smoke")
        state["failure_queue"]["jobs"] = [
            {
                "job": MODULE.build_query_job("western", "en", "Q30", "politician", 5, 0),
                "attempt_count": 2,
                "next_retry_at": 80,
            },
            {
                "job": MODULE.build_query_job("china_like", "zh", "Q148", "writer", 5, 0),
                "attempt_count": 1,
                "next_retry_at": 70,
            },
            {
                "job": MODULE.build_query_job("global_extra", "en", "Q17", "scientist", 5, 0),
                "attempt_count": 1,
                "next_retry_at": 120,
            },
        ]

        jobs = MODULE.get_retryable_failure_jobs(state, now=100)
        assert [item["job"]["cohort"] for item in jobs] == ["china_like", "western"]
        summary = MODULE.build_pipeline_summary(state, now=100)
        assert summary["ready_failed_jobs"] == 2
    finally:
        MODULE.__file__ = original_file


def test_load_pipeline_state_migrates_legacy_failure_queue(tmp_path, monkeypatch):
    original_file = MODULE.__file__
    try:
        script_path = tmp_path / "scripts" / "crawl_famous_people.py"
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "famous_people_failure_queue_smoke.json").write_text(
            json.dumps(
                {
                    "jobs": [
                        {
                            "job": MODULE.build_query_job("western", "en", "Q30", "politician", 5, 0),
                            "error": "timeout",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        MODULE.__file__ = str(script_path)
        monkeypatch.setattr(MODULE.time, "time", lambda: 1000)

        state = MODULE.load_pipeline_state("_smoke")
        item = state["failure_queue"]["jobs"][0]
        assert item["attempt_count"] == 1
        assert item["next_retry_at"] == 1600
    finally:
        MODULE.__file__ = original_file
