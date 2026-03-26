"""页面路由"""
from __future__ import annotations
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


@router.get("/home", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/reading", response_class=HTMLResponse)
async def reading(request: Request):
    return templates.TemplateResponse("reading.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/classic", response_class=HTMLResponse)
async def classic(request: Request):
    return templates.TemplateResponse("classic.html", {"request": request})


@router.get("/reports", response_class=HTMLResponse)
async def reports(request: Request):
    return templates.TemplateResponse("reports.html", {"request": request})


@router.get("/reports/admin", response_class=HTMLResponse)
async def reports_admin(request: Request):
    return templates.TemplateResponse("reports_admin.html", {"request": request})
