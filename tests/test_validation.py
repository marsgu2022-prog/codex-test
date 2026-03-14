from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from fastapi.testclient import TestClient


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "api.py"
SPEC = spec_from_file_location("bazi_validation_api", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["bazi_validation_api"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

client = TestClient(MODULE.app)


def valid_payload():
    return {
        "year": 1990,
        "month": 7,
        "day": 15,
        "hour": 9,
        "minute": 0,
        "gender": "女",
        "city": "上海",
    }


def test_year_out_of_range_returns_chinese_error():
    payload = valid_payload()
    payload["year"] = 1899
    response = client.post("/api/interpret", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "年份范围为1900-2030"}


def test_month_invalid_returns_chinese_error():
    payload = valid_payload()
    payload["month"] = 13
    response = client.post("/api/interpret", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "月份范围为1-12"}


def test_day_invalid_returns_chinese_error():
    payload = valid_payload()
    payload["day"] = 32
    response = client.post("/api/interpret", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "日期范围为1-31"}


def test_hour_invalid_returns_chinese_error():
    payload = valid_payload()
    payload["hour"] = 24
    response = client.post("/api/interpret", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "时辰范围为0-23"}


def test_gender_invalid_returns_chinese_error():
    payload = valid_payload()
    payload["gender"] = "其他"
    response = client.post("/api/interpret", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "请选择性别"}


def test_invalid_calendar_date_returns_chinese_error():
    payload = valid_payload()
    payload["month"] = 2
    payload["day"] = 30
    response = client.post("/api/interpret", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "日期无效"}


def test_gender_is_normalized_to_english():
    response = client.post("/api/interpret", json=valid_payload())
    assert response.status_code == 200
    assert response.json()["input"]["gender"] == "female"


def test_empty_city_uses_default_timezone():
    payload = valid_payload()
    payload["city"] = ""
    response = client.post("/api/interpret", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["input"]["birthplace"] == ""
    assert body["input"]["timezone"] == "Asia/Shanghai"
