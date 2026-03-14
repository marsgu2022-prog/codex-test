from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from fastapi.testclient import TestClient


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "wuxing_analysis.py"
SPEC = spec_from_file_location("bazi_wuxing", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["bazi_wuxing"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

API_MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "api.py"
API_SPEC = spec_from_file_location("bazi_wuxing_api", API_MODULE_PATH)
API_MODULE = module_from_spec(API_SPEC)
sys.modules["bazi_wuxing_api"] = API_MODULE
assert API_SPEC and API_SPEC.loader
API_SPEC.loader.exec_module(API_MODULE)

client = TestClient(API_MODULE.app)


def sample_pillars():
    return {
        "year": {"heavenly_stem": "庚", "earthly_branch": "午"},
        "month": {"heavenly_stem": "壬", "earthly_branch": "子"},
        "day": {"heavenly_stem": "壬", "earthly_branch": "寅"},
        "hour": {"heavenly_stem": "乙", "earthly_branch": "丑"},
    }


def test_hidden_stem_table_is_complete():
    assert len(MODULE.BRANCH_HIDDEN_STEMS) == 12
    assert set(MODULE.BRANCH_HIDDEN_STEMS.keys()) == set("子丑寅卯辰巳午未申酉戌亥")


def test_wuxing_scores_sum_matches_total():
    result = MODULE.analyze_wuxing(sample_pillars())
    total = round(sum(result["wuxing_scores"].values()), 2)
    assert total == round(sum(result["wuxing_scores"].values()), 2)


def test_wuxing_percentage_sum_is_100():
    result = MODULE.analyze_wuxing(sample_pillars())
    assert round(sum(result["wuxing_percentages"].values()), 2) == 100.0


def test_day_master_is_extracted_correctly():
    result = MODULE.analyze_wuxing(sample_pillars())
    assert result["day_master"] == "壬"
    assert result["day_master_element"] == "水"


def test_interpret_contains_wuxing_analysis():
    response = client.post(
        "/api/interpret",
        json={
            "year": 1990,
            "month": 7,
            "day": 15,
            "hour": 9,
            "minute": 0,
            "gender": "女",
            "city": "上海",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "wuxing_analysis" in body
    assert body["wuxing_analysis"]["day_master"]
