from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from fastapi.testclient import TestClient


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "shensha.py"
SPEC = spec_from_file_location("bazi_shensha", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["bazi_shensha"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

API_MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "api.py"
API_SPEC = spec_from_file_location("bazi_shensha_api", API_MODULE_PATH)
API_MODULE = module_from_spec(API_SPEC)
sys.modules["bazi_shensha_api"] = API_MODULE
assert API_SPEC and API_SPEC.loader
API_SPEC.loader.exec_module(API_MODULE)

client = TestClient(API_MODULE.app)


def sample_pillars():
    return {
        "year": {"heavenly_stem": "庚", "earthly_branch": "午"},
        "month": {"heavenly_stem": "癸", "earthly_branch": "丑"},
        "day": {"heavenly_stem": "甲", "earthly_branch": "寅"},
        "hour": {"heavenly_stem": "丁", "earthly_branch": "未"},
    }


def test_shensha_items_have_required_fields():
    result = MODULE.calculate_shensha(sample_pillars(), "male")
    assert isinstance(result, list)
    assert result
    for item in result:
        assert {"name", "type", "position", "description"}.issubset(item.keys())


def test_jia_day_with_chou_or_wei_has_tianyi_guiren():
    result = MODULE.calculate_shensha(sample_pillars(), "male")
    names = {item["name"] for item in result}
    assert "天乙贵人" in names


def test_shensha_result_is_not_empty():
    result = MODULE.calculate_shensha(sample_pillars(), "male")
    assert len(result) > 0


def test_interpret_contains_shensha():
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
    assert "shensha" in body
    assert isinstance(body["shensha"], list)
