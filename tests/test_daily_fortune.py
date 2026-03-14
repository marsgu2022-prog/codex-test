from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from fastapi.testclient import TestClient


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "daily_fortune.py"
SPEC = spec_from_file_location("bazi_daily_fortune", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["bazi_daily_fortune"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

API_MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "api.py"
API_SPEC = spec_from_file_location("bazi_daily_api", API_MODULE_PATH)
API_MODULE = module_from_spec(API_SPEC)
sys.modules["bazi_daily_api"] = API_MODULE
assert API_SPEC and API_SPEC.loader
API_SPEC.loader.exec_module(API_MODULE)

client = TestClient(API_MODULE.app)


def test_generate_daily_fortune_returns_complete_structure():
    result = MODULE.generate_daily_fortune("2026-03-14", {"day_master": "壬"})
    required_fields = {
        "date",
        "day_ganzhi",
        "day_wuxing",
        "liunian_ganzhi",
        "liuyue_ganzhi",
        "fortune_level",
        "lucky_color",
        "lucky_direction",
        "lucky_number",
        "general_message",
        "wallpaper_text",
        "blessing",
        "personal_message",
    }
    assert required_fields.issubset(result.keys())
    assert result["general_message"]
    assert result["personal_message"]


def test_daily_fortune_uses_jieqi_boundaries_for_year_and_month():
    before_lichun = MODULE.generate_daily_fortune("2024-02-04")
    after_lichun = MODULE.generate_daily_fortune("2024-02-05")
    before_jingzhe = MODULE.generate_daily_fortune("2024-03-05")
    after_jingzhe = MODULE.generate_daily_fortune("2024-03-06")

    assert before_lichun["liunian_ganzhi"] == "癸卯"
    assert after_lichun["liunian_ganzhi"] == "甲辰"
    assert before_jingzhe["liuyue_ganzhi"] == "丙寅"
    assert after_jingzhe["liuyue_ganzhi"] == "丁卯"


def test_different_dates_return_different_results():
    first = MODULE.generate_daily_fortune("2026-03-14")
    second = MODULE.generate_daily_fortune("2026-03-15")
    assert first["day_ganzhi"] != second["day_ganzhi"]


def test_daily_fortune_supports_english_output():
    result = MODULE.generate_daily_fortune("2026-03-14", {"day_master": "壬"}, lang="en")
    assert result["general_message"]
    assert result["blessing"]
    assert any(char.isalpha() for char in result["general_message"])


def test_daily_fortune_endpoint_returns_non_empty_messages():
    response = client.get(
        "/api/daily-fortune",
        params={
            "date": "2026-03-14",
            "year": 1990,
            "month": 1,
            "day": 1,
            "hour": 11,
            "gender": "男",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["general_message"]
    assert body["personal_message"]
