from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from html import escape
import hmac
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
import logging
from pathlib import Path
import sys
import time
from typing import Any
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from lunar_python import Solar
from pydantic import BaseModel, Field, model_validator
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
from invite_system import (
    consume_code,
    disable_code,
    generate_code,
    init_db,
    list_codes,
    validate_code,
)
try:
    from i18n_utils import convert_response_traditional, filter_lang
except ModuleNotFoundError:
    def convert_response_traditional(data: Any) -> Any:
        return data

    def filter_lang(data: Any, _lang: str) -> Any:
        return data

LOG_DIR = BASE_DIR.parent / "logs"
LOG_FILE_PATH = LOG_DIR / "api.log"
CACHE_LIMIT = 1000
LOGGER_NAME = "bazichart_engine_api"
RATE_LIMIT_PER_MINUTE = 30
MAX_REQUEST_BODY_SIZE = 10 * 1024
BLOCKED_UA = ["python-requests", "scrapy", "wget", "httpclient", "java/", "go-http", "libwww", "curl/"]
ALLOWED_REFERERS = ["bazichart.ai", "localhost", "127.0.0.1", ""]
PROTECTED_API_PATHS = {"/api/interpret", "/api/deep-interpret", "/api/report/pdf"}
ADMIN_INVITE_KEY = "Mars2026Admin"
ADMIN_SESSION_COOKIE = "bazichart_admin_session"
ADMIN_SESSION_MAX_AGE = 7 * 24 * 60 * 60


def _load_local_module(module_name: str, file_path: Path):
    spec = spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块: {file_path}")
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _configure_logger() -> logging.Logger:
    LOG_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter("%(message)s")
        file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
        file_handler.setFormatter(formatter)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    return logger


LOGGER = _configure_logger()
init_db()
for _ in range(5):
    try:
        test_code = generate_code(max_uses=100, note="startup test code", expires_days=30)
        LOGGER.info("启动测试邀请码: %s", test_code)
    except RuntimeError:
        LOGGER.warning("未能生成唯一的启动测试邀请码")
DAILY_FORTUNE_MODULE = _load_local_module("bazichart_engine_daily_fortune", BASE_DIR / "daily_fortune.py")
DAYUN_MODULE = _load_local_module("bazichart_engine_dayun", BASE_DIR / "dayun.py")
DAYUN_DETAIL_MODULE = _load_local_module("bazichart_engine_dayun_detail", BASE_DIR / "dayun_detail.py")
FAMOUS_MATCH_MODULE = _load_local_module("bazichart_engine_famous_match", BASE_DIR / "famous_match.py")
HEHUN_MODULE = _load_local_module("bazichart_engine_hehun", BASE_DIR / "hehun.py")
LIUNIAN_DETAIL_MODULE = _load_local_module("bazichart_engine_liunian_detail", BASE_DIR / "liunian_detail.py")
PDF_MODULE = _load_local_module("bazichart_engine_pdf_generator", BASE_DIR / "pdf_generator.py")
SHENSHA_MODULE = _load_local_module("bazichart_engine_shensha", BASE_DIR / "shensha.py")
SOLAR_TIME_MODULE = _load_local_module("bazichart_engine_solar_time", BASE_DIR / "solar_time.py")
SOLAR_TERMS_MODULE = _load_local_module("bazichart_engine_solar_terms", BASE_DIR / "solar_terms.py")
WUXING_MODULE = _load_local_module("bazichart_engine_wuxing_analysis", BASE_DIR / "wuxing_analysis.py")
INTERPRETER_MODULE = _load_local_module("bazichart_engine_ai_interpreter", BASE_DIR.parent / "src" / "ai_interpreter.py")
INTERPRETATION_CACHE: OrderedDict[str, dict[str, Any]] = OrderedDict()
RATE_LIMIT_STORE: dict[str, tuple[int, int]] = {}
CITY_LONGITUDE_MAP = {
    "上海": 121.47,
    "shanghai": 121.47,
    "北京": 116.40,
    "beijing": 116.40,
    "乌鲁木齐": 87.62,
    "urumqi": 87.62,
    "乌市": 87.62,
    "纽约": -74.01,
    "new york": -74.01,
    "new york city": -74.01,
}
SHICHEN_TO_HOUR = {
    "子时": 23,
    "丑时": 1,
    "寅时": 3,
    "卯时": 5,
    "辰时": 7,
    "巳时": 9,
    "午时": 11,
    "未时": 13,
    "申时": 15,
    "酉时": 17,
    "戌时": 19,
    "亥时": 21,
}
TIANGAN = "甲乙丙丁戊己庚辛壬癸"
DIZHI = "子丑寅卯辰巳午未申酉戌亥"

# ── 十神相关常量（来自 dayun_detail.py） ──
_STEM_WUXING = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}
_STEM_YINYANG = {
    "甲": "阳", "乙": "阴", "丙": "阳", "丁": "阴", "戊": "阳",
    "己": "阴", "庚": "阳", "辛": "阴", "壬": "阳", "癸": "阴",
}
_GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
_CONTROLS = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}
_SHISHEN_LABELS = {
    ("同我", True): "比肩", ("同我", False): "劫财",
    ("我生", True): "食神", ("我生", False): "伤官",
    ("我克", True): "偏财", ("我克", False): "正财",
    ("克我", True): "七杀", ("克我", False): "正官",
    ("生我", True): "偏印", ("生我", False): "正印",
}

def _relation(day_element: str, target_element: str) -> str:
    if day_element == target_element:
        return "同我"
    if _GENERATES[day_element] == target_element:
        return "我生"
    if _GENERATES[target_element] == day_element:
        return "生我"
    if _CONTROLS[day_element] == target_element:
        return "我克"
    return "克我"

def _shishen(day_master: str, target_stem: str) -> str:
    relation = _relation(_STEM_WUXING[day_master], _STEM_WUXING[target_stem])
    same_polarity = _STEM_YINYANG[day_master] == _STEM_YINYANG[target_stem]
    return _SHISHEN_LABELS[(relation, same_polarity)]

# ── 60甲子纳音表 ──
_NAYIN_TABLE = {
    ("甲", "子"): "海中金", ("乙", "丑"): "海中金",
    ("丙", "寅"): "炉中火", ("丁", "卯"): "炉中火",
    ("戊", "辰"): "大林木", ("己", "巳"): "大林木",
    ("庚", "午"): "路旁土", ("辛", "未"): "路旁土",
    ("壬", "申"): "剑锋金", ("癸", "酉"): "剑锋金",
    ("甲", "戌"): "山头火", ("乙", "亥"): "山头火",
    ("丙", "子"): "涧下水", ("丁", "丑"): "涧下水",
    ("戊", "寅"): "城头土", ("己", "卯"): "城头土",
    ("庚", "辰"): "白蜡金", ("辛", "巳"): "白蜡金",
    ("壬", "午"): "杨柳木", ("癸", "未"): "杨柳木",
    ("甲", "申"): "泉中水", ("乙", "酉"): "泉中水",
    ("丙", "戌"): "屋上土", ("丁", "亥"): "屋上土",
    ("戊", "子"): "霹雳火", ("己", "丑"): "霹雳火",
    ("庚", "寅"): "松柏木", ("辛", "卯"): "松柏木",
    ("壬", "辰"): "长流水", ("癸", "巳"): "长流水",
    ("甲", "午"): "砂石金", ("乙", "未"): "砂石金",
    ("丙", "申"): "山下火", ("丁", "酉"): "山下火",
    ("戊", "戌"): "平地木", ("己", "亥"): "平地木",
    ("庚", "子"): "壁上土", ("辛", "丑"): "壁上土",
    ("壬", "寅"): "金箔金", ("癸", "卯"): "金箔金",
    ("甲", "辰"): "覆灯火", ("乙", "巳"): "覆灯火",
    ("丙", "午"): "天河水", ("丁", "未"): "天河水",
    ("戊", "申"): "大驿土", ("己", "酉"): "大驿土",
    ("庚", "戌"): "钗钏金", ("辛", "亥"): "钗钏金",
    ("壬", "子"): "桑柘木", ("癸", "丑"): "桑柘木",
    ("甲", "寅"): "大溪水", ("乙", "卯"): "大溪水",
    ("丙", "辰"): "沙中土", ("丁", "巳"): "沙中土",
    ("戊", "午"): "天上火", ("己", "未"): "天上火",
    ("庚", "申"): "石榴木", ("辛", "酉"): "石榴木",
    ("壬", "戌"): "大海水", ("癸", "亥"): "大海水",
}

def get_nayin(gan: str, zhi: str) -> str:
    return _NAYIN_TABLE.get((gan, zhi), "未知")
YEAR_BASE = 1984
MONTH_START_STEM_MAP = {
    "甲": "丙",
    "己": "丙",
    "乙": "戊",
    "庚": "戊",
    "丙": "庚",
    "辛": "庚",
    "丁": "壬",
    "壬": "壬",
    "戊": "甲",
    "癸": "甲",
}
MONTH_BRANCHES = "寅卯辰巳午未申酉戌亥子丑"


VALID_LANGS = {"zh_hans", "zh_hant", "en", "all"}


class InterpretRequest(BaseModel):
    year: Any = Field(default=None)
    month: Any = Field(default=None)
    day: Any = Field(default=None)
    hour: Any = Field(default=None)
    minute: Any = Field(default=0)
    gender: Any = Field(default=None)
    city: str | None = Field(default=None)
    timezone: str | None = Field(default=None)
    longitude: Any = Field(default=None)
    lang: str = Field(default="zh_hans")
    invite_code: str | None = Field(default=None)

    @model_validator(mode="after")
    def validate_fields(self) -> "InterpretRequest":
        self.year = _validate_int_field(self.year, "请输入出生年份", "年份范围为1900-2030", 1900, 2030)
        self.month = _validate_int_field(self.month, "请输入出生月份", "月份范围为1-12", 1, 12)
        self.day = _validate_int_field(self.day, "请输入出生日期", "日期范围为1-31", 1, 31)
        self.hour = _validate_int_field(self.hour, "请输入出生时辰", "时辰范围为0-23", 0, 23)
        self.minute = _validate_int_field(self.minute, "分钟范围为0-59", "分钟范围为0-59", 0, 59)
        self.gender = _normalize_gender(self.gender)
        self.city = (self.city or "").strip()
        self.timezone = (self.timezone or "Asia/Shanghai").strip() or "Asia/Shanghai"
        self.longitude = _normalize_longitude(self.longitude)
        _validate_date(self.year, self.month, self.day)
        if self.lang not in VALID_LANGS:
            self.lang = "zh_hans"
        self.invite_code = (self.invite_code or "").strip()
        return self


class HehunRequest(BaseModel):
    male_year: Any = Field(default=None)
    male_month: Any = Field(default=None)
    male_day: Any = Field(default=None)
    male_hour: Any = Field(default=None)
    male_gender: Any = Field(default=None)
    female_year: Any = Field(default=None)
    female_month: Any = Field(default=None)
    female_day: Any = Field(default=None)
    female_hour: Any = Field(default=None)
    female_gender: Any = Field(default=None)

    @model_validator(mode="after")
    def validate_fields(self) -> "HehunRequest":
        self.male_year = _validate_int_field(self.male_year, "请输入男方出生年份", "年份范围为1900-2030", 1900, 2030)
        self.male_month = _validate_int_field(self.male_month, "请输入男方出生月份", "月份范围为1-12", 1, 12)
        self.male_day = _validate_int_field(self.male_day, "请输入男方出生日期", "日期范围为1-31", 1, 31)
        self.male_hour = _validate_int_field(self.male_hour, "请输入男方出生时辰", "时辰范围为0-23", 0, 23)
        self.male_gender = _normalize_gender(self.male_gender)
        self.female_year = _validate_int_field(self.female_year, "请输入女方出生年份", "年份范围为1900-2030", 1900, 2030)
        self.female_month = _validate_int_field(self.female_month, "请输入女方出生月份", "月份范围为1-12", 1, 12)
        self.female_day = _validate_int_field(self.female_day, "请输入女方出生日期", "日期范围为1-31", 1, 31)
        self.female_hour = _validate_int_field(self.female_hour, "请输入女方出生时辰", "时辰范围为0-23", 0, 23)
        self.female_gender = _normalize_gender(self.female_gender)
        _validate_date(self.male_year, self.male_month, self.male_day)
        _validate_date(self.female_year, self.female_month, self.female_day)
        return self


class FamousMatchRequest(BaseModel):
    day_pillar: str = Field(default="")

    @model_validator(mode="after")
    def validate_fields(self) -> "FamousMatchRequest":
        self.day_pillar = _normalize_day_pillar(self.day_pillar)
        return self


class InviteGenerateRequest(BaseModel):
    admin_key: str
    max_uses: int = Field(default=10)
    expires_days: int | None = Field(default=30)
    note: str = Field(default="")


class InviteDisableRequest(BaseModel):
    admin_key: str
    code: str


def _extract_validation_message(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "参数校验失败"

    first = errors[0]
    error_type = first.get("type")
    field = first.get("loc", [])[-1] if first.get("loc") else None
    if error_type == "missing":
        if field == "year":
            return "请输入出生年份"
        if field == "month":
            return "请输入出生月份"
        if field == "day":
            return "请输入出生日期"
        if field == "hour":
            return "请输入出生时辰"
        if field == "gender":
            return "请选择性别"

    message = first.get("msg", "参数校验失败")
    if message.startswith("Value error, "):
        return message.split("Value error, ", 1)[1]
    return message


def _validate_int_field(value: Any, missing_message: str, invalid_message: str, minimum: int, maximum: int) -> int:
    if value is None or value == "":
        raise ValueError(missing_message)
    try:
        int_value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(invalid_message) from exc
    if int_value < minimum or int_value > maximum:
        raise ValueError(invalid_message)
    return int_value


def _normalize_gender(value: Any) -> str:
    if value is None or str(value).strip() == "":
        raise ValueError("请选择性别")
    text = str(value).strip().lower()
    if text == "男":
        return "male"
    if text == "女":
        return "female"
    if text in {"male", "female"}:
        return text
    raise ValueError("请选择性别")


def _normalize_longitude(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("经度格式无效") from exc


def _normalize_day_pillar(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) != 2 or text[0] not in TIANGAN or text[1] not in DIZHI:
        raise ValueError("日柱格式无效")
    return text


def _validate_date(year: int, month: int, day: int) -> None:
    try:
        datetime(year=year, month=month, day=day)
    except ValueError as exc:
        raise ValueError("日期无效") from exc


def _mask_request_params(payload: dict[str, Any] | None) -> str:
    if not payload:
        return "year=unknown gender=unknown"
    year = payload.get("year", "unknown")
    gender = payload.get("gender", "unknown")
    return f"year={year} gender={gender}"


def _cache_key(payload: InterpretRequest) -> str:
    raw_key = "|".join(
        [
            str(payload.year),
            str(payload.month),
            str(payload.day),
            str(payload.hour),
            str(payload.minute),
            payload.gender.strip(),
            payload.city.strip(),
            str(payload.longitude),
        ]
    )
    return sha256(raw_key.encode("utf-8")).hexdigest()


def _get_cached_interpretation(cache_key: str) -> dict[str, Any] | None:
    cached = INTERPRETATION_CACHE.get(cache_key)
    if cached is None:
        return None
    INTERPRETATION_CACHE.move_to_end(cache_key)
    return cached


def _set_cached_interpretation(cache_key: str, interpretation_data: dict[str, Any]) -> None:
    INTERPRETATION_CACHE[cache_key] = interpretation_data
    INTERPRETATION_CACHE.move_to_end(cache_key)
    while len(INTERPRETATION_CACHE) > CACHE_LIMIT:
        INTERPRETATION_CACHE.popitem(last=False)


def clear_interpretation_cache() -> None:
    INTERPRETATION_CACHE.clear()


def clear_rate_limit_store() -> None:
    RATE_LIMIT_STORE.clear()


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "").strip()
    if forwarded_for:
        return forwarded_for.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _check_rate_limit(client_ip: str, current_bucket: int) -> bool:
    previous = RATE_LIMIT_STORE.get(client_ip)
    if previous is None or previous[0] != current_bucket:
        RATE_LIMIT_STORE[client_ip] = (current_bucket, 1)
        return True

    count = previous[1] + 1
    RATE_LIMIT_STORE[client_ip] = (current_bucket, count)
    return count <= RATE_LIMIT_PER_MINUTE


def _apply_security_headers(response: Response) -> Response:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    content_type = (response.headers.get("content-type") or "").lower()
    if "text/html" in content_type:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; form-action 'self'; base-uri 'self'; frame-ancestors 'none'"
        )
    else:
        response.headers["Content-Security-Policy"] = "default-src 'none'"
    if "server" in response.headers:
        del response.headers["server"]
    return response


def _invite_required_response() -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={"error": "邀请码无效或已用完", "code": "INVITE_REQUIRED"},
    )


def _build_admin_session_value() -> str:
    expires_at = int(time.time()) + ADMIN_SESSION_MAX_AGE
    signature = sha256(f"{ADMIN_INVITE_KEY}:{expires_at}:{BASE_DIR}".encode("utf-8")).hexdigest()
    return f"{expires_at}.{signature}"


def _has_admin_session(request: Request) -> bool:
    raw_cookie = (request.cookies.get(ADMIN_SESSION_COOKIE) or "").strip()
    if not raw_cookie or "." not in raw_cookie:
        return False
    expires_part, signature = raw_cookie.split(".", 1)
    if not expires_part.isdigit():
        return False
    expires_at = int(expires_part)
    if expires_at < int(time.time()):
        return False
    expected = sha256(f"{ADMIN_INVITE_KEY}:{expires_at}:{BASE_DIR}".encode("utf-8")).hexdigest()
    return hmac.compare_digest(signature, expected)


def _set_admin_session(response: Response) -> None:
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=_build_admin_session_value(),
        max_age=ADMIN_SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


def _clear_admin_session(response: Response) -> None:
    response.delete_cookie(ADMIN_SESSION_COOKIE, path="/")


def _ensure_invite_code(payload: InterpretRequest, request: Request) -> JSONResponse | None:
    if _has_admin_session(request):
        return None
    request_code = (payload.invite_code or "").strip()
    if not request_code:
        return _invite_required_response()
    normalized = request_code.upper()
    valid, _reason = validate_code(normalized)
    if not valid:
        return _invite_required_response()
    try:
        consume_code(normalized, request.url.path, _get_client_ip(request))
    except Exception as exc:
        LOGGER.exception("邀请码使用记录失败: %s", exc)
        raise HTTPException(status_code=500, detail="邀请码使用失败") from exc
    return None


def _require_admin_access(request: Request, key: str | None = None) -> None:
    if _has_admin_session(request):
        return
    if key == ADMIN_INVITE_KEY:
        return
    raise HTTPException(status_code=403, detail="权限不足")


def _require_admin_session(request: Request) -> None:
    if not _has_admin_session(request):
        raise HTTPException(status_code=403, detail="权限不足")


def _render_homepage(is_admin: bool) -> HTMLResponse:
    auth_link = "/admin" if is_admin else "/admin/login"
    auth_label = "进入后台" if is_admin else "管理员登录"
    auth_hint = "管理员已登录，可直接进入后台管理" if is_admin else "管理员可直接登录，登录后深度解盘与 PDF 全通免邀请码"
    html = f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>BaziChart</title>
    <style>
      :root {{
        --bg: #0a0d1f;
        --panel: rgba(11, 15, 33, 0.82);
        --line: rgba(196, 149, 77, 0.28);
        --gold: #d4a43a;
        --gold-soft: rgba(212, 164, 58, 0.14);
        --text: #f5efe4;
        --muted: rgba(245, 239, 228, 0.7);
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        min-height: 100vh;
        font-family: "PingFang SC", "Noto Serif SC", serif;
        color: var(--text);
        background:
          radial-gradient(circle at top, rgba(153, 112, 42, 0.18), transparent 32%),
          linear-gradient(180deg, #090c1b 0%, #060814 100%);
      }}
      .shell {{ min-height: 100vh; }}
      .topbar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 18px 32px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      }}
      .brand {{
        color: var(--text);
        text-decoration: none;
        font-size: 24px;
        letter-spacing: 0.08em;
      }}
      .topbar-right {{
        display: flex;
        align-items: center;
        gap: 14px;
      }}
      .hint {{
        color: var(--muted);
        font-size: 13px;
      }}
      .login-btn {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 120px;
        padding: 10px 18px;
        border: 1px solid var(--line);
        border-radius: 999px;
        color: var(--gold);
        text-decoration: none;
        background: var(--gold-soft);
      }}
      .hero {{
        width: min(960px, calc(100vw - 48px));
        margin: 0 auto;
        padding: 72px 0 120px;
        text-align: center;
      }}
      .disc {{
        width: min(360px, 72vw);
        aspect-ratio: 1;
        margin: 0 auto 28px;
        border-radius: 50%;
        border: 1px solid rgba(212, 164, 58, 0.25);
        background:
          radial-gradient(circle at center, rgba(241, 206, 145, 0.95) 0 7%, rgba(94, 64, 26, 0.96) 8% 13%, transparent 14%),
          radial-gradient(circle at center, transparent 0 23%, rgba(191, 145, 68, 0.18) 24% 27%, transparent 28% 37%, rgba(191, 145, 68, 0.12) 38% 42%, transparent 43%),
          radial-gradient(circle at center, rgba(139, 95, 42, 0.92) 0 62%, rgba(77, 53, 23, 0.96) 63% 74%, rgba(18, 20, 40, 0.95) 75%);
        box-shadow: 0 24px 80px rgba(0, 0, 0, 0.45), inset 0 0 40px rgba(255, 210, 136, 0.12);
      }}
      .eyebrow {{
        display: inline-block;
        padding: 8px 16px;
        border: 1px solid var(--line);
        border-radius: 999px;
        color: var(--gold);
        background: rgba(212, 164, 58, 0.08);
      }}
      h1 {{
        margin: 28px 0 16px;
        font-size: clamp(52px, 8vw, 88px);
        line-height: 1.05;
        font-weight: 500;
      }}
      .gold {{ color: var(--gold); }}
      p {{
        margin: 0 auto;
        max-width: 720px;
        color: var(--muted);
        font-size: 18px;
        line-height: 1.8;
      }}
      .cta {{
        display: inline-flex;
        margin-top: 28px;
        padding: 14px 34px;
        border-radius: 14px;
        border: 1px solid var(--line);
        background: transparent;
        color: var(--gold);
        text-decoration: none;
      }}
      @media (max-width: 700px) {{
        .topbar {{
          padding: 16px 18px;
          align-items: flex-start;
          flex-direction: column;
        }}
        .topbar-right {{
          width: 100%;
          justify-content: space-between;
        }}
      }}
    </style>
  </head>
  <body>
    <div class="shell">
      <header class="topbar">
        <a class="brand" href="/">BaziChart</a>
        <div class="topbar-right">
          <span class="hint">{escape(auth_hint)}</span>
          <a class="login-btn" href="{auth_link}">{auth_label}</a>
        </div>
      </header>
      <main class="hero">
        <div class="disc" aria-hidden="true"></div>
        <div class="eyebrow">古老智慧 · 现代智能</div>
        <h1>解读你的<br /><span class="gold">性格密码</span></h1>
        <p>AI 八字分析、荣格心理学与东方智慧结合。管理员登录后可直接使用深度解盘与 PDF 报告，无需邀请码。</p>
        <a class="cta" href="/admin/login">开始登入</a>
      </main>
    </div>
  </body>
</html>"""
    return HTMLResponse(content=html)


def _render_admin_login(error_message: str = "") -> HTMLResponse:
    error_block = ""
    if error_message:
        error_block = f'<div class="error">{escape(error_message)}</div>'
    html = f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>管理员登录</title>
    <style>
      :root {{
        --bg: #090d1d;
        --panel: rgba(15, 19, 40, 0.94);
        --line: rgba(196, 149, 77, 0.28);
        --gold: #d4a43a;
        --text: #f6efe2;
        --muted: rgba(246, 239, 226, 0.68);
        --danger: #ff8585;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 24px;
        font-family: "PingFang SC", "Noto Sans SC", sans-serif;
        color: var(--text);
        background: linear-gradient(180deg, #090c1b 0%, #060814 100%);
      }}
      .card {{
        width: min(460px, 100%);
        padding: 28px;
        border: 1px solid var(--line);
        border-radius: 24px;
        background: var(--panel);
        box-shadow: 0 24px 80px rgba(0, 0, 0, 0.42);
      }}
      h1 {{ margin: 0 0 12px; font-size: 30px; }}
      p {{ margin: 0 0 24px; color: var(--muted); line-height: 1.7; }}
      label {{ display: block; margin-bottom: 10px; color: var(--muted); font-size: 14px; }}
      input {{
        width: 100%;
        padding: 14px 16px;
        border-radius: 14px;
        border: 1px solid var(--line);
        background: rgba(255, 255, 255, 0.03);
        color: var(--text);
      }}
      button {{
        width: 100%;
        margin-top: 18px;
        padding: 14px 16px;
        border-radius: 14px;
        border: 1px solid var(--line);
        background: rgba(212, 164, 58, 0.12);
        color: var(--gold);
        cursor: pointer;
      }}
      .error {{
        margin-bottom: 16px;
        padding: 12px 14px;
        border-radius: 12px;
        color: var(--danger);
        background: rgba(255, 133, 133, 0.08);
        border: 1px solid rgba(255, 133, 133, 0.2);
      }}
      .back {{
        display: inline-block;
        margin-top: 14px;
        color: var(--muted);
        text-decoration: none;
      }}
    </style>
  </head>
  <body>
    <form class="card" method="post" action="/admin/login">
      <h1>管理员登录</h1>
      <p>当前登录仅面向管理员。登录成功后，深度解盘与 PDF 报告接口自动免邀请码。</p>
      {error_block}
      <label for="admin_key">管理员口令</label>
      <input id="admin_key" name="admin_key" type="password" autocomplete="current-password" required />
      <button type="submit">登入后台</button>
      <a class="back" href="/">返回主页</a>
    </form>
  </body>
</html>"""
    return HTMLResponse(content=html)


def _render_admin_console(codes: list[dict[str, Any]]) -> HTMLResponse:
    rows = []
    for item in codes[:20]:
        status = "已禁用" if item["disabled"] else "可用"
        rows.append(
            "<tr>"
            f"<td>{escape(str(item['code']))}</td>"
            f"<td>{item['used_count']}/{item['max_uses']}</td>"
            f"<td>{escape(status)}</td>"
            f"<td>{escape(str(item.get('note') or '-'))}</td>"
            "</tr>"
        )
    rows_html = "".join(rows) or '<tr><td colspan="4">暂无邀请码</td></tr>'
    html = f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>管理员后台</title>
    <style>
      :root {{
        --bg: #09101f;
        --panel: rgba(13, 20, 41, 0.94);
        --line: rgba(196, 149, 77, 0.26);
        --gold: #d4a43a;
        --text: #f4ede0;
        --muted: rgba(244, 237, 224, 0.7);
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        min-height: 100vh;
        padding: 28px;
        font-family: "PingFang SC", "Noto Sans SC", sans-serif;
        color: var(--text);
        background: linear-gradient(180deg, #090c1b 0%, #060814 100%);
      }}
      .shell {{ width: min(1080px, 100%); margin: 0 auto; }}
      .top {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 20px;
      }}
      .title h1 {{ margin: 0 0 6px; font-size: 32px; }}
      .title p {{ margin: 0; color: var(--muted); }}
      .actions {{
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
      }}
      .btn {{
        padding: 10px 16px;
        border-radius: 12px;
        border: 1px solid var(--line);
        color: var(--gold);
        text-decoration: none;
        background: rgba(212, 164, 58, 0.08);
      }}
      .panel {{
        border: 1px solid var(--line);
        border-radius: 24px;
        background: var(--panel);
        padding: 24px;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
      }}
      th, td {{
        padding: 14px 10px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        text-align: left;
      }}
      th {{ color: var(--muted); font-weight: 500; }}
      .notice {{
        margin-bottom: 18px;
        padding: 14px 16px;
        border-radius: 16px;
        background: rgba(212, 164, 58, 0.08);
        color: var(--muted);
      }}
    </style>
  </head>
  <body>
    <div class="shell">
      <div class="top">
        <div class="title">
          <h1>管理员后台</h1>
          <p>当前会话已登录。管理员可直接调用深度解盘与 PDF 报告，无需邀请码。</p>
        </div>
        <div class="actions">
          <a class="btn" href="/">返回主页</a>
          <a class="btn" href="/admin/logout">退出登录</a>
        </div>
      </div>
      <div class="panel">
        <div class="notice">这里先提供最小可用后台，用于确认管理员登录与邀请码管理状态。</div>
        <table>
          <thead>
            <tr>
              <th>邀请码</th>
              <th>使用次数</th>
              <th>状态</th>
              <th>备注</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
    </div>
  </body>
</html>"""
    return HTMLResponse(content=html)


def _raise_internal_error(status_code: int, public_message: str, log_message: str, exc: Exception) -> None:
    LOGGER.exception("%s: %s", log_message, exc)
    raise HTTPException(status_code=status_code, detail=public_message) from exc


def _raise_internal_error(status_code: int, public_message: str, log_message: str, exc: Exception) -> None:
    LOGGER.exception("%s: %s", log_message, exc)
    raise HTTPException(status_code=status_code, detail=public_message) from exc


def _js_style_hash(raw: str) -> int:
    value = 0
    for char in raw:
        value = ((value << 5) - value) + ord(char)
        value &= 0xFFFFFFFF
    if value & 0x80000000:
        value = -((~value + 1) & 0xFFFFFFFF)
    return abs(value)


def _to_base36(value: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if value == 0:
        return "0"
    result = []
    current = value
    while current:
        current, remainder = divmod(current, 36)
        result.append(digits[remainder])
    return "".join(reversed(result))


def verify_request_token(token: str) -> bool:
    if not token:
        return False
    try:
        ts_raw, signature = token.split(".", 1)
        ts = int(ts_raw)
    except (ValueError, AttributeError):
        return False

    current_ts = int(time.time() // 30)
    if abs(current_ts - ts) > 4:
        return False

    expected = _to_base36(_js_style_hash(f"bazichart_{ts}_salt"))
    return signature == expected


def _resolve_longitude(payload: InterpretRequest) -> float | None:
    if payload.longitude is not None:
        return payload.longitude
    if not payload.city:
        return None
    return CITY_LONGITUDE_MAP.get(payload.city) or CITY_LONGITUDE_MAP.get(payload.city.lower())


def _build_solar_time_info(payload: InterpretRequest) -> dict[str, Any] | None:
    longitude = _resolve_longitude(payload)
    if longitude is None:
        return None
    return SOLAR_TIME_MODULE.calculate_true_solar_time(
        payload.year,
        payload.month,
        payload.day,
        payload.hour,
        payload.minute,
        longitude,
    )


def _resolve_bazi_datetime(payload: InterpretRequest, solar_time_info: dict[str, Any] | None = None) -> datetime:
    if solar_time_info and solar_time_info.get("corrected_datetime"):
        return datetime.fromisoformat(solar_time_info["corrected_datetime"])
    return datetime(payload.year, payload.month, payload.day, payload.hour, payload.minute)


def _ganzhi_for_year(year: int) -> str:
    offset = year - YEAR_BASE
    return f"{TIANGAN[offset % 10]}{DIZHI[offset % 12]}"


def _month_ganzhi(year_stem: str, month_order: int) -> str:
    start_stem = MONTH_START_STEM_MAP[year_stem]
    stem_index = (TIANGAN.index(start_stem) + month_order - 1) % 10
    branch = MONTH_BRANCHES[month_order - 1]
    return f"{TIANGAN[stem_index]}{branch}"


def _pillar_dict(ganzhi: str) -> dict[str, str]:
    return {"heavenly_stem": ganzhi[0], "earthly_branch": ganzhi[1]}


def build_four_pillars(payload: InterpretRequest, solar_time_info: dict[str, Any] | None = None) -> dict[str, dict[str, str]]:
    bazi_dt = _resolve_bazi_datetime(payload, solar_time_info=solar_time_info)
    solar = Solar.fromYmdHms(bazi_dt.year, bazi_dt.month, bazi_dt.day, bazi_dt.hour, bazi_dt.minute, bazi_dt.second)
    eight_char = solar.getLunar().getEightChar()
    bazi_year = SOLAR_TERMS_MODULE.resolve_bazi_year(bazi_dt)
    year_ganzhi = _ganzhi_for_year(bazi_year)
    month_order = SOLAR_TERMS_MODULE.resolve_bazi_month_order(bazi_dt)
    month_ganzhi = _month_ganzhi(year_ganzhi[0], month_order)
    return {
        "year": _pillar_dict(year_ganzhi),
        "month": _pillar_dict(month_ganzhi),
        "day": _pillar_dict(eight_char.getDay()),
        "hour": _pillar_dict(eight_char.getTime()),
    }


def _build_canggan(four_pillars: dict[str, Any]) -> dict[str, list[str]]:
    """提取每柱地支的藏干列表（只取天干名，不带权重）。"""
    branch_hidden = WUXING_MODULE.BRANCH_HIDDEN_STEMS
    result: dict[str, list[str]] = {}
    for pillar_name in ("year", "month", "day", "hour"):
        branch = four_pillars[pillar_name]["earthly_branch"]
        result[pillar_name] = [stem for stem, _ in branch_hidden[branch]]
    return result


def _build_shishen_per_pillar(four_pillars: dict[str, Any]) -> dict[str, str]:
    """计算每柱天干相对于日主的十神关系。"""
    day_master = four_pillars["day"]["heavenly_stem"]
    result: dict[str, str] = {}
    for pillar_name in ("year", "month", "day", "hour"):
        if pillar_name == "day":
            result[pillar_name] = "日主"
        else:
            stem = four_pillars[pillar_name]["heavenly_stem"]
            result[pillar_name] = _shishen(day_master, stem)
    return result


def _build_nayin(four_pillars: dict[str, Any]) -> dict[str, str]:
    """计算每柱的60甲子纳音。"""
    result: dict[str, str] = {}
    for pillar_name in ("year", "month", "day", "hour"):
        gan = four_pillars[pillar_name]["heavenly_stem"]
        zhi = four_pillars[pillar_name]["earthly_branch"]
        result[pillar_name] = get_nayin(gan, zhi)
    return result


def generate_interpretation(payload: InterpretRequest, four_pillars: dict[str, Any]) -> dict[str, Any]:
    day_master = four_pillars["day"]["heavenly_stem"]
    day_pillar = f"{four_pillars['day']['heavenly_stem']}{four_pillars['day']['earthly_branch']}"
    dominant_gods = ["比肩", "正印"]
    current_year = datetime.now().year
    solar_time_info = _build_solar_time_info(payload)
    dayun = DAYUN_MODULE.calculate_dayun(
        payload.year,
        payload.month,
        payload.day,
        payload.hour,
        payload.gender,
        minute=payload.minute,
        solar_time_info=solar_time_info,
    )
    for item in dayun:
        item["detail"] = DAYUN_DETAIL_MODULE.generate_dayun_detail(
            four_pillars,
            f"{item['tiangan']}{item['dizhi']}",
            payload.gender,
        )
    liunian = DAYUN_MODULE.calculate_liunian(payload.year, current_year - 5, 10)
    current_dayun_ganzhi = f"{dayun[0]['tiangan']}{dayun[0]['dizhi']}" if dayun else "甲子"
    for item in liunian:
        item["detail"] = LIUNIAN_DETAIL_MODULE.generate_liunian_detail(
            four_pillars,
            current_dayun_ganzhi,
            f"{item['tiangan']}{item['dizhi']}",
            payload.gender,
        )
    narrative = INTERPRETER_MODULE.post_interpret(
        {
            "lang": "zh",
            "day_master": day_master,
            "dominant_gods": dominant_gods,
            "ten_gods": {"比肩": 8, "正印": 7},
        }
    )

    return {
        "input": {
            "birth_year": payload.year,
            "birth_month": payload.month,
            "birth_day": payload.day,
            "birth_hour": payload.hour,
            "birth_minute": payload.minute,
            "gender": payload.gender,
            "birthplace": payload.city,
            "timezone": payload.timezone,
            "longitude": payload.longitude,
        },
        "four_pillars": four_pillars,
        "canggan": _build_canggan(four_pillars),
        "shishen_per_pillar": _build_shishen_per_pillar(four_pillars),
        "nayin": _build_nayin(four_pillars),
        "shensha": SHENSHA_MODULE.calculate_shensha(four_pillars, payload.gender),
        "wuxing_analysis": WUXING_MODULE.analyze_wuxing(four_pillars),
        "famous_matches": FAMOUS_MATCH_MODULE.get_famous_matches(day_pillar),
        "dayun": dayun,
        "liunian": liunian,
        "ten_gods_analysis": {
            "比肩": {
                "interpretation": "比肩体现自主驱动力、边界感与对平等关系的重视。"
            },
            "正印": {
                "interpretation": "正印体现吸收能力、安全感来源与对支持系统的需求。"
            },
        },
        "psychological_analysis": {
            "荣格原型": "更偏向英雄与照顾者并存的心理模式。",
            "MBTI倾向": "可能更偏向 INFJ / ENFJ 一类的共情与组织倾向。",
            "解读摘要": narrative.get("narrative", ""),
        },
    }


def get_or_create_interpretation(payload: InterpretRequest) -> tuple[dict[str, Any], str]:
    cache_key = _cache_key(payload)
    cached = _get_cached_interpretation(cache_key)
    if cached is not None:
        return cached, "HIT"

    solar_time_info = _build_solar_time_info(payload)
    four_pillars = build_four_pillars(payload, solar_time_info=solar_time_info)
    interpretation_data = generate_interpretation(payload, four_pillars)
    if solar_time_info is not None:
        interpretation_data["solar_time_info"] = solar_time_info
    _set_cached_interpretation(cache_key, interpretation_data)
    return interpretation_data, "MISS"


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bazichart.ai",
        "https://www.bazichart.ai",
        "http://localhost:3003",
        "http://localhost:5173",
        "http://localhost:5174",
    ],
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-Token"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.perf_counter()
    if request.method == "OPTIONS" and request.url.path.startswith("/api/"):
        response = await call_next(request)
        return _apply_security_headers(response)

    body = await request.body()
    client_ip = _get_client_ip(request)
    payload: dict[str, Any] | None = None
    if body:
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = None

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    request = Request(request.scope, receive)
    request.state.log_params = _mask_request_params(payload)
    request.state.cache_status = "MISS"
    response: Response

    if len(body) > MAX_REQUEST_BODY_SIZE:
        response = JSONResponse(status_code=413, content={"error": "请求体过大"})
    elif not _check_rate_limit(client_ip, int(time.time() // 60)):
        response = JSONResponse(status_code=429, content={"error": "请求过于频繁，请稍后再试"})
    elif request.url.path.startswith("/api/"):
        ua = (request.headers.get("user-agent") or "").lower()
        is_local_probe = client_ip in {"127.0.0.1", "::1", "localhost", "testclient"} or request.url.path == "/api/health"
        if not is_local_probe and any(blocked in ua for blocked in BLOCKED_UA):
            response = JSONResponse(status_code=403, content={"error": "Access denied"})
        elif _has_admin_session(request):
            response = await call_next(request)
        elif not is_local_probe and request.url.path in PROTECTED_API_PATHS:
            referer = (request.headers.get("referer") or "").lower()
            token = request.headers.get("x-request-token", "")
            if referer and not any(allowed in referer for allowed in ALLOWED_REFERERS):
                response = JSONResponse(status_code=403, content={"error": "Invalid referer"})
            elif not verify_request_token(token):
                response = JSONResponse(status_code=403, content={"error": "Invalid request token"})
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)
    else:
        response = await call_next(request)

    response = _apply_security_headers(response)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    LOGGER.info(
        "[%s] %s %s | %s | %s | %s | %sms",
        timestamp,
        request.method,
        request.url.path,
        request.state.log_params,
        response.status_code,
        f"[CACHE {getattr(request.state, 'cache_status', 'MISS')}]",
        elapsed_ms,
    )
    return response


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    request.state.cache_status = "MISS"
    return JSONResponse(
        status_code=400,
        content={"error": _extract_validation_message(exc)},
    )


## ── 名人数据 ──

_FAMOUS_PEOPLE: list[dict] = []
_DAY_PILLAR_INDEX: dict[str, list] = {}

def _load_famous_data():
    global _FAMOUS_PEOPLE, _DAY_PILLAR_INDEX
    data_dir = BASE_DIR / "data"
    fp_path = data_dir / "famous_people.json"
    idx_path = data_dir / "day_pillar_index.json"
    if fp_path.exists() and not _FAMOUS_PEOPLE:
        _FAMOUS_PEOPLE = json.loads(fp_path.read_text(encoding="utf-8"))
    if idx_path.exists() and not _DAY_PILLAR_INDEX:
        _DAY_PILLAR_INDEX = json.loads(idx_path.read_text(encoding="utf-8"))

_load_famous_data()


@app.get("/")
def homepage(request: Request):
    return _render_homepage(is_admin=_has_admin_session(request))


@app.get("/admin/login")
def admin_login_page(request: Request):
    if _has_admin_session(request):
        return RedirectResponse(url="/admin", status_code=303)
    return _render_admin_login()


@app.post("/admin/login")
async def admin_login_submit(request: Request):
    body = (await request.body()).decode("utf-8")
    form_data = parse_qs(body)
    admin_key = (form_data.get("admin_key", [""])[0] or "").strip()
    if admin_key != ADMIN_INVITE_KEY:
        return _render_admin_login("管理员口令错误")
    response = RedirectResponse(url="/admin", status_code=303)
    _set_admin_session(response)
    return response


@app.get("/admin")
def admin_console(request: Request):
    _require_admin_session(request)
    return _render_admin_console(list_codes())


@app.get("/admin/logout")
def admin_logout(request: Request):
    _require_admin_session(request)
    response = RedirectResponse(url="/admin/login", status_code=303)
    _clear_admin_session(response)
    return response


@app.get("/api/famous-by-day-pillar")
def famous_by_day_pillar(day_pillar: str, limit: int = 20):
    """按日柱查询同日柱名人"""
    if not day_pillar or len(day_pillar) != 2:
        raise HTTPException(status_code=400, detail="请提供有效的日柱（如甲子）")
    safe_limit = max(1, min(limit, 20))
    matches = _DAY_PILLAR_INDEX.get(day_pillar, [])
    return {"day_pillar": day_pillar, "count": min(len(matches), safe_limit), "people": matches[:safe_limit]}


def _detect_region(person: dict) -> str:
    """根据名人数据自动推断地区"""
    if person.get("region"):
        return person["region"]
    name_zh = person.get("name_zh", "")
    name_en = person.get("name_en", "")
    has_cjk = any('\u4e00' <= c <= '\u9fff' for c in name_zh) if name_zh else False
    # 真正华人的特征：2-4字中文名，无中间点·，且有拼音英文名
    if has_cjk and '·' not in name_zh and len(name_zh) <= 4:
        # 排除日韩越南人：英文名含典型非华人姓
        en_lower = (name_en or "").lower()
        if any(k in en_lower for k in ['sato', 'tanaka', 'yamam', 'suzuki', 'nguyen', 'park ', 'kim ', 'lee hoi']):
            return "global"
        return "cn"
    return "global"


def _get_recommended(region: str, limit: int = 20) -> list:
    """按地区智能推荐名人"""
    local = []
    global_famous = []
    others = []
    for p in _FAMOUS_PEOPLE:
        r = _detect_region(p)
        if r == region:
            local.append(p)
        elif r == "global":
            global_famous.append(p)
        else:
            others.append(p)

    # 本地区60% + 全球30% + 其他10%
    local_limit = int(limit * 0.6)
    global_limit = int(limit * 0.3)
    other_limit = limit - local_limit - global_limit

    result = local[:local_limit] + global_famous[:global_limit] + others[:other_limit]
    return result[:limit]


@app.get("/api/famous/search")
def famous_search(q: str = "", region: str = "", lang: str = "zh", limit: int = 20):
    """按姓名模糊搜索名人。空查询按地区智能推荐。"""
    limit = max(1, min(limit, 20))
    if not q or len(q.strip()) < 1:
        if region:
            recommended = _get_recommended(region, limit)
        else:
            # 根据lang推断region
            inferred_region = "cn" if lang in ("zh", "zh-CN", "zh-TW") else "global"
            recommended = _get_recommended(inferred_region, limit)
        return {"query": "", "count": len(recommended), "people": recommended}
    q = q.strip().lower()
    results = []
    for p in _FAMOUS_PEOPLE:
        name_zh = (p.get("name_zh") or "").lower()
        name_en = (p.get("name_en") or "").lower()
        if q in name_zh or q in name_en:
            results.append(p)
            if len(results) >= limit:
                break
    return {"query": q, "count": len(results), "people": results}


@app.post("/api/famous-match")
def famous_match(payload: FamousMatchRequest):
    try:
        people = FAMOUS_MATCH_MODULE.get_famous_matches(payload.day_pillar)
        return {
            "day_pillar": payload.day_pillar,
            "count": len(people),
            "people": people,
        }
    except HTTPException:
        raise
    except Exception as exc:
        _raise_internal_error(500, "名人匹配失败，请稍后再试", "名人匹配失败", exc)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/daily-fortune")
def get_daily_fortune(
    date: str,
    lang: str = "zh",
    year: int | None = None,
    month: int | None = None,
    day: int | None = None,
    hour: int | None = None,
    gender: str | None = None,
    minute: int = 0,
    city: str | None = None,
    timezone: str | None = None,
    longitude: float | None = None,
):
    try:
        user_bazi = None
        provided = [year, month, day, hour, gender]
        if any(value is not None for value in provided):
            if not all(value is not None for value in provided):
                raise HTTPException(status_code=400, detail="个性化运势参数不完整")
            payload = InterpretRequest(
                year=year,
                month=month,
                day=day,
                hour=hour,
                minute=minute,
                gender=gender,
                city=city,
                timezone=timezone,
                longitude=longitude,
            )
            solar_time_info = _build_solar_time_info(payload)
            four_pillars = build_four_pillars(payload, solar_time_info=solar_time_info)
            user_bazi = {"four_pillars": four_pillars}

        return DAILY_FORTUNE_MODULE.generate_daily_fortune(date, user_bazi=user_bazi, lang=lang)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _raise_internal_error(500, "每日运势生成失败，请稍后再试", "每日运势生成失败", exc)


@app.post("/api/hehun")
def analyze_hehun(payload: HehunRequest):
    try:
        male_payload = InterpretRequest(
            year=payload.male_year,
            month=payload.male_month,
            day=payload.male_day,
            hour=payload.male_hour,
            minute=0,
            gender=payload.male_gender,
            city="",
            timezone="Asia/Shanghai",
            longitude=None,
        )
        female_payload = InterpretRequest(
            year=payload.female_year,
            month=payload.female_month,
            day=payload.female_day,
            hour=payload.female_hour,
            minute=0,
            gender=payload.female_gender,
            city="",
            timezone="Asia/Shanghai",
            longitude=None,
        )
        male_pillars = build_four_pillars(male_payload)
        female_pillars = build_four_pillars(female_payload)
        male_analysis = WUXING_MODULE.analyze_wuxing(male_pillars)
        female_analysis = WUXING_MODULE.analyze_wuxing(female_pillars)
        return HEHUN_MODULE.analyze_hehun(
            male_pillars,
            female_pillars,
            male_analysis=male_analysis,
            female_analysis=female_analysis,
        )
    except HTTPException:
        raise
    except Exception as exc:
        _raise_internal_error(500, "合婚分析失败，请稍后再试", "合婚分析失败", exc)


def _apply_lang(data: dict[str, Any], lang: str) -> dict[str, Any]:
    """根据 lang 参数转换响应语言"""
    if lang == "zh_hans":
        return data
    if lang == "zh_hant":
        return convert_response_traditional(data)
    # lang == "en" 或 "all"：基础排盘无英文，直接返回
    return data


@app.post("/api/interpret")
def interpret(payload: InterpretRequest, request: Request):
    try:
        interpretation_data, cache_status = get_or_create_interpretation(payload)
        request.state.cache_status = cache_status
        return _apply_lang(interpretation_data, payload.lang)
    except HTTPException:
        raise
    except Exception as exc:
        _raise_internal_error(500, "解读生成失败，请稍后再试", "解读生成失败", exc)


@app.post("/api/deep-interpret")
def deep_interpret(payload: InterpretRequest, request: Request):
    """深度 AI 解读端点 — 调用 DeepSeek + 韩立知识库生成结构化深度命理解读。"""
    rejection = _ensure_invite_code(payload, request)
    if rejection:
        return rejection
    try:
        interpretation_data, cache_status = get_or_create_interpretation(payload)
        request.state.cache_status = cache_status
    except HTTPException:
        raise
    except Exception as exc:
        _raise_internal_error(500, "排盘计算失败，请稍后再试", "排盘计算失败", exc)

    try:
        from llm_client import generate_deep_interpretation
        deep_result = generate_deep_interpretation(interpretation_data)
        # 附上同日柱名人
        fp = interpretation_data.get("four_pillars", {})
        day_gan = fp.get("day", {}).get("heavenly_stem", "")
        day_zhi = fp.get("day", {}).get("earthly_branch", "")
        day_pillar = day_gan + day_zhi
        same_day_famous = _DAY_PILLAR_INDEX.get(day_pillar, [])
        response = {
            "chart_data": _apply_lang(interpretation_data, payload.lang),
            "deep_interpretation": filter_lang(deep_result, payload.lang) if payload.lang != "zh_hans" else deep_result,
            "same_day_pillar_famous": {
                "day_pillar": day_pillar,
                "count": len(same_day_famous),
                "people": same_day_famous[:20],
            },
        }
        return response
    except ValueError as exc:
        _raise_internal_error(503, "AI解读服务暂不可用", "AI解读服务异常", exc)
    except RuntimeError as exc:
        _raise_internal_error(502, "AI解读失败，请稍后再试", "AI解读失败", exc)
    except Exception as exc:
        _raise_internal_error(500, "深度解读生成失败，请稍后再试", "深度解读生成失败", exc)


@app.post("/api/report/pdf")
def create_pdf_report(payload: InterpretRequest, request: Request):
    rejection = _ensure_invite_code(payload, request)
    if rejection:
        return rejection
    try:
        interpretation_data, cache_status = get_or_create_interpretation(payload)
        request.state.cache_status = cache_status

        # 调用 DeepSeek 深度解读
        deep_result = None
        same_day_famous = []
        try:
            from llm_client import generate_deep_interpretation
            deep_result = generate_deep_interpretation(interpretation_data)
            fp = interpretation_data.get("four_pillars", {})
            day_gan = fp.get("day", {}).get("heavenly_stem", "")
            day_zhi = fp.get("day", {}).get("earthly_branch", "")
            day_pillar = day_gan + day_zhi
            same_day_famous = _DAY_PILLAR_INDEX.get(day_pillar, [])[:20]
        except Exception as deep_err:
            LOGGER.warning(f"PDF深度解读失败（降级为基础报告）: {deep_err}")

        try:
            pdf_bytes = PDF_MODULE.generate_bazi_report(
                interpretation_data,
                lang=payload.lang,
                deep_interpretation=deep_result,
                same_day_famous=same_day_famous,
            )
        except TypeError:
            pdf_bytes = PDF_MODULE.generate_bazi_report(interpretation_data)
    except HTTPException:
        raise
    except Exception as exc:
        _raise_internal_error(500, "PDF 生成失败，请稍后再试", "PDF 生成失败", exc)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="bazi_report.pdf"'},
    )


@app.post("/api/admin/invite/generate")
def admin_generate_invite(payload: InviteGenerateRequest, request: Request):
    _require_admin_access(request, payload.admin_key)
    code = generate_code(
        max_uses=payload.max_uses,
        expires_days=payload.expires_days,
        note=payload.note,
    )
    return {"code": code}


@app.get("/api/admin/invite/list")
def admin_list_invites(request: Request, admin_key: str = ""):
    _require_admin_access(request, admin_key)
    return {"codes": list_codes()}


@app.post("/api/admin/invite/disable")
def admin_disable_invite(payload: InviteDisableRequest, request: Request):
    _require_admin_access(request, payload.admin_key)
    if not disable_code(payload.code):
        raise HTTPException(status_code=404, detail="邀请码不存在")
    return {"disabled": True}


@app.post("/api/report/hehun-pdf")
def create_hehun_pdf_report(payload: HehunRequest):
    try:
        male_payload = InterpretRequest(
            year=payload.male_year,
            month=payload.male_month,
            day=payload.male_day,
            hour=payload.male_hour,
            minute=0,
            gender=payload.male_gender,
            city="",
            timezone="Asia/Shanghai",
            longitude=None,
        )
        female_payload = InterpretRequest(
            year=payload.female_year,
            month=payload.female_month,
            day=payload.female_day,
            hour=payload.female_hour,
            minute=0,
            gender=payload.female_gender,
            city="",
            timezone="Asia/Shanghai",
            longitude=None,
        )
        male_pillars = build_four_pillars(male_payload)
        female_pillars = build_four_pillars(female_payload)
        male_analysis = WUXING_MODULE.analyze_wuxing(male_pillars)
        female_analysis = WUXING_MODULE.analyze_wuxing(female_pillars)
        hehun_result = HEHUN_MODULE.analyze_hehun(
            male_pillars,
            female_pillars,
            male_analysis=male_analysis,
            female_analysis=female_analysis,
        )
        pdf_bytes = PDF_MODULE.generate_hehun_report(
            {"four_pillars": male_pillars, "input": {"gender": male_payload.gender}},
            {"four_pillars": female_pillars, "input": {"gender": female_payload.gender}},
            hehun_result,
        )
    except HTTPException:
        raise
    except Exception as exc:
        _raise_internal_error(500, "合婚 PDF 生成失败，请稍后再试", "合婚 PDF 生成失败", exc)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="hehun_report.pdf"'},
    )

# === BaziChart.ai v2 前端 ===
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

try:
    from routes.pages import router as pages_router
    from routes.reading_api import router as reading_router
    from routes.auth_api import router as auth_router
    from routes.archive_api import router as archive_router
    from routes.classic_api import router as classic_router

    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    app.include_router(pages_router)
    app.include_router(reading_router, prefix="/api/v2")
    app.include_router(auth_router, prefix="/api/v2/auth")
    app.include_router(archive_router, prefix="/api/v2")
    app.include_router(classic_router, prefix="/api/v2")

except Exception as _v2_err:
    import logging
    logging.getLogger("bazichart_engine_api").warning(f"v2前端加载失败: {_v2_err}")
# === v2 结束 ===
