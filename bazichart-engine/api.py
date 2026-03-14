from __future__ import annotations

from collections import OrderedDict
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
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR.parent / "logs"
LOG_FILE_PATH = LOG_DIR / "api.log"
CACHE_LIMIT = 1000
LOGGER_NAME = "bazichart_engine_api"


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
PDF_MODULE = _load_local_module("bazichart_engine_pdf_generator", BASE_DIR / "pdf_generator.py")
INTERPRETER_MODULE = _load_local_module("bazichart_engine_ai_interpreter", BASE_DIR.parent / "src" / "ai_interpreter.py")
INTERPRETATION_CACHE: OrderedDict[str, dict[str, Any]] = OrderedDict()


class InterpretRequest(BaseModel):
    birth_year: int = Field(..., ge=1900, le=2100)
    birth_month: int = Field(..., ge=1, le=12)
    birth_day: int = Field(..., ge=1, le=31)
    birth_hour: int = Field(..., ge=0, le=23)
    gender: str = Field(..., min_length=1)
    birthplace: str = Field(..., min_length=1)


def _mask_request_params(payload: dict[str, Any] | None) -> str:
    if not payload:
        return "year=unknown gender=unknown"
    year = payload.get("birth_year", "unknown")
    gender = payload.get("gender", "unknown")
    return f"year={year} gender={gender}"


def _cache_key(payload: InterpretRequest) -> str:
    raw_key = "|".join(
        [
            str(payload.birth_year),
            str(payload.birth_month),
            str(payload.birth_day),
            str(payload.birth_hour),
            payload.gender.strip(),
            payload.birthplace.strip(),
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


def build_four_pillars(payload: InterpretRequest) -> dict[str, dict[str, str]]:
    stems = "甲乙丙丁戊己庚辛壬癸"
    branches = "子丑寅卯辰巳午未申酉戌亥"

    def pillar(seed: int) -> dict[str, str]:
        return {
            "heavenly_stem": stems[seed % len(stems)],
            "earthly_branch": branches[seed % len(branches)],
        }

    return {
        "year": pillar(payload.birth_year),
        "month": pillar(payload.birth_month),
        "day": pillar(payload.birth_day),
        "hour": pillar(payload.birth_hour),
    }


def generate_interpretation(payload: InterpretRequest, four_pillars: dict[str, Any]) -> dict[str, Any]:
    day_master = four_pillars["day"]["heavenly_stem"]
    dominant_gods = ["比肩", "正印"]
    narrative = INTERPRETER_MODULE.post_interpret(
        {
            "lang": "zh",
            "day_master": day_master,
            "dominant_gods": dominant_gods,
            "ten_gods": {"比肩": 8, "正印": 7},
        }
    )

    return {
        "input": payload.model_dump(),
        "four_pillars": four_pillars,
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

    four_pillars = build_four_pillars(payload)
    interpretation_data = generate_interpretation(payload, four_pillars)
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

    response = await call_next(request)

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
        content={"error": "参数校验失败", "details": exc.errors()},
    )


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


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
