from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from fastapi.testclient import TestClient


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "dayun.py"
SPEC = spec_from_file_location("bazi_dayun", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["bazi_dayun"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

API_MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "api.py"
API_SPEC = spec_from_file_location("bazi_dayun_api", API_MODULE_PATH)
API_MODULE = module_from_spec(API_SPEC)
sys.modules["bazi_dayun_api"] = API_MODULE
assert API_SPEC and API_SPEC.loader
API_SPEC.loader.exec_module(API_MODULE)

client = TestClient(API_MODULE.app)


def test_dayun_returns_eight_steps():
    result = MODULE.calculate_dayun(1990, 1, 1, 11, "male")
    assert len(result) == 8
    assert all(item["tiangan"] and item["dizhi"] for item in result)


def test_yang_year_male_is_forward_and_yin_year_male_is_backward():
    yang_male = MODULE.calculate_dayun(1990, 1, 1, 11, "male")
    yin_male = MODULE.calculate_dayun(1989, 1, 1, 11, "male")
    assert (yang_male[0]["tiangan"], yang_male[0]["dizhi"]) == ("丙", "寅")
    assert (yin_male[0]["tiangan"], yin_male[0]["dizhi"]) == ("甲", "子")


def test_liunian_for_2025_and_2026_matches_expected():
    result = MODULE.calculate_liunian(1990, 2025, 2)
    assert result[0]["year"] == 2025
    assert result[0]["tiangan"] == "乙"
    assert result[0]["dizhi"] == "巳"
    assert result[1]["year"] == 2026
    assert result[1]["tiangan"] == "丙"
    assert result[1]["dizhi"] == "午"


def test_interpret_contains_dayun_and_liunian():
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
    assert len(body["dayun"]) == 8
    assert len(body["liunian"]) == 10
