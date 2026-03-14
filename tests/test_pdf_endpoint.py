from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from fastapi.testclient import TestClient


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "api.py"
SPEC = spec_from_file_location("bazi_pdf_api", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["bazi_pdf_api"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

client = TestClient(MODULE.app)


def test_health_endpoint():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_pdf_endpoint_returns_pdf():
    response = client.post(
        "/api/report/pdf",
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
    assert response.headers["content-type"] == "application/pdf"
    assert 'attachment; filename="bazi_report.pdf"' == response.headers["content-disposition"]
    assert len(response.content) > 0


def test_interpret_endpoint_returns_json():
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
    assert "four_pillars" in body
    assert "ten_gods_analysis" in body
    assert body["input"]["gender"] == "female"


def test_pdf_endpoint_missing_required_field_returns_400():
    response = client.post(
        "/api/report/pdf",
        json={
            "month": 7,
            "day": 15,
            "hour": 9,
            "gender": "女",
        },
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"error": "请输入出生年份"}


def test_cors_preflight_allows_frontend_origin():
    response = client.options(
        "/api/report/pdf",
        headers={
            "Origin": "http://localhost:3003",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3003"
