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
