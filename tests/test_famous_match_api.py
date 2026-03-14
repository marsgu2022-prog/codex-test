from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from fastapi.testclient import TestClient


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "api.py"
SPEC = spec_from_file_location("bazi_famous_match_api", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["bazi_famous_match_api"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

client = TestClient(MODULE.app)
VALID_DAY_PILLARS = [f"{gan}{zhi}" for gan in MODULE.TIANGAN for zhi in MODULE.DIZHI]


def test_famous_match_returns_people_for_existing_day_pillar():
    response = client.post("/api/famous-match", json={"day_pillar": "丁丑"})

    assert response.status_code == 200
    body = response.json()
    assert body["day_pillar"] == "丁丑"
    assert body["count"] > 0
    assert body["count"] <= 10
    assert body["people"]
    assert {"name_zh", "nationality_zh", "field_zh", "summary"}.issubset(body["people"][0].keys())


def test_famous_match_returns_empty_list_for_unknown_day_pillar():
    response = client.post("/api/famous-match", json={"day_pillar": "甲甲"})

    assert response.status_code == 400
    assert response.json() == {"error": "日柱格式无效"}


def test_famous_match_returns_empty_when_valid_but_not_found():
    indexed = MODULE.FAMOUS_MATCH_MODULE.load_day_pillar_index()
    missing = next(item for item in VALID_DAY_PILLARS if item not in indexed)
    response = client.post("/api/famous-match", json={"day_pillar": missing})

    assert response.status_code == 200
    body = response.json()
    assert body["day_pillar"] == missing
    assert body["count"] == 0
    assert body["people"] == []


def test_interpret_includes_famous_matches():
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
    assert "famous_matches" in body
    assert isinstance(body["famous_matches"], list)
