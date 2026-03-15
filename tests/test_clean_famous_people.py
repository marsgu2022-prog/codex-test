from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "scripts" / "clean_famous_people.py"
SPEC = spec_from_file_location("clean_famous_people", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["clean_famous_people"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_clean_people_removes_strict_blacklist_person():
    people = [
        {"id": "Q1", "name_zh": "东条英机", "name_en": "Hideki Tojo", "birth_date": "1884-12-30"},
        {"id": "Q2", "name_zh": "爱因斯坦", "name_en": "Albert Einstein", "birth_date": "1879-03-14"},
    ]

    cleaned, deleted, review = MODULE.clean_people(people)

    assert [item["id"] for item in cleaned] == ["Q2"]
    assert deleted[0]["name_zh"] == "东条英机"
    assert review == []


def test_clean_people_marks_review_for_sensitive_activist_description():
    people = [
        {
            "id": "Q1",
            "name_zh": "某人物",
            "name_en": "Someone",
            "birth_date": "1970-01-01",
            "summary": "知名人权活动家与异议人士",
        }
    ]

    cleaned, deleted, review = MODULE.clean_people(people)

    assert len(cleaned) == 1
    assert deleted == []
    assert review[0]["category"] == "政治敏感"


def test_detect_early_death_deletes_under_30_accidental_death():
    person = {
        "id": "Q1",
        "name_zh": "甲",
        "name_en": "A",
        "birth_date": "1990-01-01",
        "summary": "Singer (1990-2015), died in plane crash",
    }

    decision, matched = MODULE.evaluate_person(person, MODULE.compile_strict_aliases())

    assert decision == "delete"
    assert matched is not None
    assert matched["category"] == "心理不适"
