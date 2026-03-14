from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from fastapi.testclient import TestClient


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "hehun.py"
SPEC = spec_from_file_location("bazi_hehun", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["bazi_hehun"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

API_MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "api.py"
API_SPEC = spec_from_file_location("bazi_hehun_api", API_MODULE_PATH)
API_MODULE = module_from_spec(API_SPEC)
sys.modules["bazi_hehun_api"] = API_MODULE
assert API_SPEC and API_SPEC.loader
API_SPEC.loader.exec_module(API_MODULE)

client = TestClient(API_MODULE.app)


def test_hehun_returns_complete_structure():
    result = MODULE.analyze_hehun(
        {
            "year": {"heavenly_stem": "庚", "earthly_branch": "午"},
            "month": {"heavenly_stem": "癸", "earthly_branch": "丑"},
            "day": {"heavenly_stem": "甲", "earthly_branch": "寅"},
            "hour": {"heavenly_stem": "丁", "earthly_branch": "未"},
        },
        {
            "year": {"heavenly_stem": "辛", "earthly_branch": "未"},
            "month": {"heavenly_stem": "甲", "earthly_branch": "子"},
            "day": {"heavenly_stem": "己", "earthly_branch": "卯"},
            "hour": {"heavenly_stem": "庚", "earthly_branch": "申"},
        },
        male_analysis={
            "wuxing_scores": {"金": 1.0, "木": 2.8, "水": 0.8, "火": 2.0, "土": 1.0},
            "favorable_elements": ["水", "金"],
        },
        female_analysis={
            "wuxing_scores": {"金": 2.6, "木": 1.2, "水": 2.5, "火": 0.8, "土": 1.4},
            "favorable_elements": ["木", "火"],
        },
    )
    assert {"score", "level", "day_gan_he", "year_zhi", "yongshen_match", "wuxing_complement", "summary"}.issubset(
        result.keys()
    )
    assert 0 <= result["score"] <= 100
    assert result["level"]


def test_hehun_endpoint_returns_scored_result():
    response = client.post(
        "/api/hehun",
        json={
            "male_year": 1990,
            "male_month": 1,
            "male_day": 1,
            "male_hour": 11,
            "male_gender": "男",
            "female_year": 1991,
            "female_month": 2,
            "female_day": 2,
            "female_hour": 9,
            "female_gender": "女",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["score"] <= 100
    assert body["level"]
