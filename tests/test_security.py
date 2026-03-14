from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from fastapi.testclient import TestClient


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "api.py"
SPEC = spec_from_file_location("bazi_security_api", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["bazi_security_api"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

client = TestClient(MODULE.app)


def test_rate_limit_blocks_requests_after_thirty_per_minute():
    MODULE.clear_rate_limit_store()
    payload = {
        "year": 1990,
        "month": 7,
        "day": 15,
        "hour": 9,
        "minute": 0,
        "gender": "女",
        "city": "上海",
    }
    headers = {"X-Forwarded-For": "203.0.113.10"}

    responses = [client.post("/api/interpret", json=payload, headers=headers) for _ in range(35)]

    assert all(response.status_code == 200 for response in responses[:30])
    assert all(response.status_code == 429 for response in responses[30:])
    assert all(response.json() == {"error": "请求过于频繁，请稍后再试"} for response in responses[30:])


def test_security_headers_are_attached_to_responses():
    MODULE.clear_rate_limit_store()

    response = client.get("/api/health", headers={"X-Forwarded-For": "203.0.113.11"})

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["content-security-policy"] == "default-src 'none'"
    assert "server" not in response.headers
