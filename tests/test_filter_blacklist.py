from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "scripts" / "filter_blacklist.py"
SPEC = spec_from_file_location("filter_blacklist", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["filter_blacklist"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_filter_people_matches_blacklist_keyword():
    people = [
        {"id": "1", "name_zh": "甲", "occupation": ["企业家"], "bio_zh": "著名企业家"},
        {"id": "2", "name_zh": "乙", "occupation": ["演员"], "bio_zh": "连环杀手题材人物"},
    ]
    config = {"strict": [], "categories": {"violence": ["连环杀手"]}}

    kept, report = MODULE.filter_people(people, config)

    assert [item["id"] for item in kept] == ["1"]
    assert report["filtered_count"] == 1
    assert report["reason_breakdown"]["violence"] == 1
    assert report["filtered_records"][0]["matched_keyword"] == "连环杀手"
