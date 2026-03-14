from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from fastapi.testclient import TestClient


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "api.py"
SPEC = spec_from_file_location("bazi_cache_api", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["bazi_cache_api"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

client = TestClient(MODULE.app)


def test_interpret_cache_reuses_same_parameters():
    MODULE.clear_interpretation_cache()
    payload = {
        "year": 1990,
        "month": 7,
        "day": 15,
        "hour": 9,
        "minute": 0,
        "gender": "女",
        "city": "上海",
    }

    first = client.post("/api/interpret", json=payload)
    second = client.post("/api/interpret", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(MODULE.INTERPRETATION_CACHE) == 1


def test_pdf_endpoint_uses_shared_interpretation_cache():
    MODULE.clear_interpretation_cache()
    payload = {
        "year": 1988,
        "month": 10,
        "day": 8,
        "hour": 6,
        "minute": 0,
        "gender": "男",
        "city": "北京",
    }

    interpret_response = client.post("/api/interpret", json=payload)
    pdf_response = client.post("/api/report/pdf", json=payload)

    assert interpret_response.status_code == 200
    assert pdf_response.status_code == 200
    assert len(MODULE.INTERPRETATION_CACHE) == 1
