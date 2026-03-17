from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from fastapi.testclient import TestClient


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "api.py"
SPEC = spec_from_file_location("bazi_admin_api", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["bazi_admin_api"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

client = TestClient(MODULE.app)


def test_homepage_shows_admin_login_entry():
    response = client.get("/")

    assert response.status_code == 200
    assert "管理员登录" in response.text
    assert 'href="/admin/login"' in response.text


def test_admin_login_sets_cookie_and_opens_console():
    response = client.post(
        "/admin/login",
        data={"admin_key": MODULE.ADMIN_INVITE_KEY},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin"
    assert MODULE.ADMIN_SESSION_COOKIE in response.headers["set-cookie"]

    console = client.get("/admin")
    assert console.status_code == 200
    assert "管理员后台" in console.text


def test_admin_session_bypasses_invite_requirement_for_pdf():
    login_response = client.post(
        "/admin/login",
        data={"admin_key": MODULE.ADMIN_INVITE_KEY},
        follow_redirects=False,
    )
    cookie = login_response.cookies.get(MODULE.ADMIN_SESSION_COOKIE)

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
        headers={"X-Request-Token": "test.admin"},
        cookies={MODULE.ADMIN_SESSION_COOKIE: cookie},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
