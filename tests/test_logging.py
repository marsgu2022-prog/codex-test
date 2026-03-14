from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from fastapi.testclient import TestClient


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "api.py"
SPEC = spec_from_file_location("bazi_logging_api", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["bazi_logging_api"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

client = TestClient(MODULE.app)


def test_request_logging_writes_log_file():
    MODULE.LOG_FILE_PATH.parent.mkdir(exist_ok=True)
    MODULE.LOG_FILE_PATH.write_text("", encoding="utf-8")

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
    assert MODULE.LOG_FILE_PATH.exists()
    content = MODULE.LOG_FILE_PATH.read_text(encoding="utf-8")
    assert "POST /api/interpret" in content
    assert "year=1990 gender=女" in content
    assert "[CACHE " in content
