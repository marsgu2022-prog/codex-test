from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from fastapi.testclient import TestClient


SOLAR_MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "solar_time.py"
SOLAR_SPEC = spec_from_file_location("bazi_solar_time", SOLAR_MODULE_PATH)
SOLAR_MODULE = module_from_spec(SOLAR_SPEC)
sys.modules["bazi_solar_time"] = SOLAR_MODULE
assert SOLAR_SPEC and SOLAR_SPEC.loader
SOLAR_SPEC.loader.exec_module(SOLAR_MODULE)

API_MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "api.py"
API_SPEC = spec_from_file_location("bazi_solar_api", API_MODULE_PATH)
API_MODULE = module_from_spec(API_SPEC)
sys.modules["bazi_solar_api"] = API_MODULE
assert API_SPEC and API_SPEC.loader
API_SPEC.loader.exec_module(API_MODULE)

client = TestClient(API_MODULE.app)


def test_shanghai_longitude_correction_matches_formula():
    result = SOLAR_MODULE.calculate_true_solar_time(2026, 3, 14, 12, 30, 121.47)
    assert abs(result["longitude_correction"] - 5.88) < 0.2


def test_urumqi_longitude_correction_is_about_negative_two_hours():
    result = SOLAR_MODULE.calculate_true_solar_time(2026, 3, 14, 12, 30, 87.62)
    assert abs(result["longitude_correction"] - (-129.52)) < 0.5
    assert result["shichen_changed"] is True


def test_beijing_longitude_correction_matches_formula():
    result = SOLAR_MODULE.calculate_true_solar_time(2026, 3, 14, 12, 30, 116.40)
    assert abs(result["longitude_correction"] - (-14.4)) < 0.2


def test_new_york_non_china_longitude_is_supported():
    result = SOLAR_MODULE.calculate_true_solar_time(2026, 3, 14, 12, 30, -74.01)
    assert result["longitude"] == -74.01
    assert result["true_solar_time"]


def test_interpret_returns_solar_time_info_when_city_is_provided():
    response = client.post(
        "/api/interpret",
        json={
            "year": 1990,
            "month": 7,
            "day": 15,
            "hour": 12,
            "minute": 30,
            "gender": "女",
            "city": "上海",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "solar_time_info" in body
    assert body["solar_time_info"]["longitude"] == 121.47
