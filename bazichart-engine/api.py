from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
import logging
from pathlib import Path
import sys
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from lunar_python import Solar
from pydantic import BaseModel, Field, model_validator


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR.parent / "logs"
LOG_FILE_PATH = LOG_DIR / "api.log"
CACHE_LIMIT = 1000
LOGGER_NAME = "bazichart_engine_api"
RATE_LIMIT_PER_MINUTE = 30
MAX_REQUEST_BODY_SIZE = 10 * 1024


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
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    if "server" in response.headers:
        del response.headers["server"]
    return response


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


def generate_interpretation(payload: InterpretRequest, four_pillars: dict[str, Any]) -> dict[str, Any]:
    day_master = four_pillars["day"]["heavenly_stem"]
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
    day_pillar = f"{four_pillars['day']['heavenly_stem']}{four_pillars['day']['earthly_branch']}"

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
        "famous_matches": FAMOUS_MATCH_MODULE.get_famous_matches(day_pillar),
        "shensha": SHENSHA_MODULE.calculate_shensha(four_pillars, payload.gender),
        "wuxing_analysis": WUXING_MODULE.analyze_wuxing(four_pillars),
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
    allow_origins=["http://localhost:3003"],
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.perf_counter()
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
        raise HTTPException(status_code=500, detail=f"每日运势生成失败: {exc}") from exc


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
        raise HTTPException(status_code=500, detail=f"合婚分析失败: {exc}") from exc


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
        raise HTTPException(status_code=500, detail=f"名人匹配失败: {exc}") from exc


@app.post("/api/interpret")
def interpret(payload: InterpretRequest, request: Request):
    try:
        interpretation_data, cache_status = get_or_create_interpretation(payload)
        request.state.cache_status = cache_status
        return interpretation_data
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"解读生成失败: {exc}") from exc


@app.post("/api/report/pdf")
def create_pdf_report(payload: InterpretRequest, request: Request):
    try:
        interpretation_data, cache_status = get_or_create_interpretation(payload)
        request.state.cache_status = cache_status
        pdf_bytes = PDF_MODULE.generate_bazi_report(interpretation_data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF 生成失败: {exc}") from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="bazi_report.pdf"'},
    )


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
        raise HTTPException(status_code=500, detail=f"合婚 PDF 生成失败: {exc}") from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="hehun_report.pdf"'},
    )
