from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from fastapi.testclient import TestClient


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "liunian_detail.py"
SPEC = spec_from_file_location("bazi_liunian_detail", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["bazi_liunian_detail"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

API_MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "api.py"
API_SPEC = spec_from_file_location("bazi_liunian_detail_api", API_MODULE_PATH)
API_MODULE = module_from_spec(API_SPEC)
sys.modules["bazi_liunian_detail_api"] = API_MODULE
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


def test_generate_liunian_detail_returns_complete_structure():
    result = MODULE.generate_liunian_detail(sample_pillars(), "庚辰", "丙午", "male")
    required = {"ganzhi", "shishen", "overall", "career", "wealth", "relationship", "health", "advice"}
    assert required.issubset(result.keys())
    assert {"score", "text"} == set(result["career"].keys())
    assert {"zh", "en"} == set(result["career"]["text"].keys())
    assert {"zh", "en"} == set(result["advice"].keys())


def test_interpret_liunian_items_include_detail():
    response = client.post(
        "/api/interpret",
        json={
            "year": 1990,
            "month": 1,
            "day": 1,
            "hour": 11,
            "minute": 0,
            "gender": "男",
            "city": "上海",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["liunian"]
    assert "detail" in body["liunian"][0]
    assert body["liunian"][0]["detail"]["career"]["text"]["zh"]
