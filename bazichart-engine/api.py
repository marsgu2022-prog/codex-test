from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent


def _load_local_module(module_name: str, file_path: Path):
    spec = spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块: {file_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PDF_MODULE = _load_local_module("bazichart_engine_pdf_generator", BASE_DIR / "pdf_generator.py")
INTERPRETER_MODULE = _load_local_module("bazichart_engine_ai_interpreter", BASE_DIR.parent / "src" / "ai_interpreter.py")


class InterpretRequest(BaseModel):
    birth_year: int = Field(..., ge=1900, le=2100)
    birth_month: int = Field(..., ge=1, le=12)
    birth_day: int = Field(..., ge=1, le=31)
    birth_hour: int = Field(..., ge=0, le=23)
    gender: str = Field(..., min_length=1)
    birthplace: str = Field(..., min_length=1)


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
            "MBTI倾向": "可能更接近 INFJ / ENFJ 一类的共情与组织倾向。",
            "解读摘要": narrative.get("narrative", ""),
        },
    }


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3003"],
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "参数校验失败", "details": exc.errors()},
    )


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/report/pdf")
def create_pdf_report(payload: InterpretRequest):
    try:
        four_pillars = build_four_pillars(payload)
        interpretation_data = generate_interpretation(payload, four_pillars)
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
