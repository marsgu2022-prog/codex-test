"""产业报告中心 API"""
from __future__ import annotations

import json
import secrets
import sqlite3
import time
from hashlib import sha256
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from routes.archive_api import _get_user
from routes.report_utils import deserialize_tags, parse_tags, sanitize_filename, serialize_tags

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "users.db"
UPLOAD_ROOT = BASE_DIR / "data" / "user-reports"
ADMIN_INVITE_KEY = "Mars2026Admin"
ADMIN_SESSION_COOKIE = "bazichart_admin_session"
ADMIN_SESSION_MAX_AGE = 7 * 24 * 60 * 60

MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_FILES_PER_USER = 100
ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".ppt", ".docx", ".doc", ".xlsx"}

router = APIRouter()

INITIAL_REPORTS = [
    {
        "title": "2024上海商业地产市场年度总结及展望",
        "source_org": "仲量联行",
        "source_url": "https://www.joneslanglasalle.com.cn/zh/trends-and-insights/research",
        "publish_date": "2025-01-15",
        "industry_tags": ["商业地产", "写字楼", "零售"],
        "region_tags": ["上海"],
        "report_type": "年度报告",
        "summary": "回顾2024年上海写字楼、零售、物流及投资市场表现，展望2025年市场走势。",
    },
    {
        "title": "上海产业园区市场发展与展望白皮书",
        "source_org": "仲量联行",
        "source_url": "https://www.joneslanglasalle.com.cn/zh/trends-and-insights/research",
        "publish_date": "2024-06-01",
        "industry_tags": ["产业园区", "产业地产"],
        "region_tags": ["上海"],
        "report_type": "白皮书",
        "summary": "深入分析上海产业园区供需格局、租金趋势及未来发展方向。",
    },
    {
        "title": "中国长租公寓市场白皮书",
        "source_org": "仲量联行",
        "source_url": "https://www.joneslanglasalle.com.cn/zh/trends-and-insights/research",
        "publish_date": "2024-09-01",
        "industry_tags": ["长租公寓", "居住"],
        "region_tags": ["全国"],
        "report_type": "白皮书",
        "summary": "分析中国长租公寓市场现状、运营模式及投资机会。",
    },
    {
        "title": "2026年中国商业地产市场展望",
        "source_org": "世邦魏理仕",
        "source_url": "https://www.cbre.com.cn/zh-cn/insights/books/2026-china-real-estate-market-outlook",
        "publish_date": "2026-01-10",
        "industry_tags": ["商业地产", "写字楼", "物流仓储"],
        "region_tags": ["全国"],
        "report_type": "年度展望",
        "summary": "对2026年中国商业地产租赁和投资趋势作出研判，分析十五五规划期内行业拐点。",
    },
    {
        "title": "上海集成电路产业发展及地产趋势专题报告",
        "source_org": "世邦魏理仕",
        "source_url": "https://www.cbre.com.cn/zh-cn/insights",
        "publish_date": "2024-08-01",
        "industry_tags": ["集成电路", "半导体", "产业地产"],
        "region_tags": ["上海"],
        "report_type": "专题研究",
        "summary": "聚焦上海集成电路产业发展现状及对产业地产的需求影响。",
    },
    {
        "title": "2025年大中华区房地产市场展望",
        "source_org": "戴德梁行",
        "source_url": "https://www.cushmanwakefield.com/zh-cn/china/insights",
        "publish_date": "2025-01-20",
        "industry_tags": ["商业地产", "写字楼", "零售", "物流"],
        "region_tags": ["大中华区"],
        "report_type": "年度展望",
        "summary": "展望大中华区各类商业地产市场走势及投资机遇。",
    },
    {
        "title": "大湾区工业上楼及未来园区核心竞争力",
        "source_org": "戴德梁行",
        "source_url": "https://www.cushmanwakefield.com/zh-cn/china/insights",
        "publish_date": "2024-05-01",
        "industry_tags": ["产业园区", "工业地产", "制造业"],
        "region_tags": ["大湾区"],
        "report_type": "专题研究",
        "summary": "探讨大湾区工业上楼模式及未来产业园区的核心竞争要素。",
    },
    {
        "title": "生命科学产业视角下的房地产市场展望",
        "source_org": "戴德梁行",
        "source_url": "https://www.cushmanwakefield.com/zh-cn/china/insights",
        "publish_date": "2024-10-01",
        "industry_tags": ["生物医药", "生命科学", "产业地产"],
        "region_tags": ["全国"],
        "report_type": "专题研究",
        "summary": "分析生命科学产业发展对研发空间和产业地产的需求趋势。",
    },
    {
        "title": "2024影响力：全球房地产的未来",
        "source_org": "第一太平戴维斯",
        "source_url": "https://www.savills.com.cn/research/research.aspx",
        "publish_date": "2024-07-01",
        "industry_tags": ["商业地产", "投资"],
        "region_tags": ["全球"],
        "report_type": "年度报告",
        "summary": "全球房地产市场趋势分析及未来展望。",
    },
    {
        "title": "中国工业地产报告",
        "source_org": "第一太平戴维斯",
        "source_url": "https://www.savills.com.cn/research/research.aspx",
        "publish_date": "2024-11-01",
        "industry_tags": ["工业地产", "物流仓储", "制造业"],
        "region_tags": ["全国"],
        "report_type": "专题研究",
        "summary": "中国工业地产市场供需分析、租金走势及投资机会。",
    },
    {
        "title": "中国房地产投资调研报告",
        "source_org": "高力国际",
        "source_url": "https://www.colliers.com/zh-cn/research",
        "publish_date": "2024-07-01",
        "industry_tags": ["投资", "商业地产"],
        "region_tags": ["全国"],
        "report_type": "调研报告",
        "summary": "调研中国市场投资者情绪、偏好资产类型及投资策略变化。",
    },
    {
        "title": "2025年商业地产行业展望",
        "source_org": "德勤",
        "source_url": "https://www.deloitte.com/cn/zh/Industries/financial-services/research.html",
        "publish_date": "2025-02-01",
        "industry_tags": ["商业地产", "投资"],
        "region_tags": ["全球"],
        "report_type": "年度展望",
        "summary": "全球商业地产业主和投资者预计2025年将成为复苏转折点。",
    },
    {
        "title": "中国商业地产活力40城",
        "source_org": "德勤",
        "source_url": "https://www.deloitte.com/cn/zh/Industries/financial-services/research.html",
        "publish_date": "2024-03-01",
        "industry_tags": ["商业地产", "城市研究"],
        "region_tags": ["全国"],
        "report_type": "专题研究",
        "summary": "评估中国40个城市的商业地产活力指数及发展潜力。",
    },
]


class IndustryReportPayload(BaseModel):
    title: str
    source_org: str
    source_url: str
    publish_date: Optional[str] = None
    industry_tags: list[str] = []
    region_tags: list[str] = []
    report_type: Optional[str] = None
    summary: Optional[str] = None
    cover_image_url: Optional[str] = None
    is_featured: bool = False


class ReviewPayload(BaseModel):
    reason: Optional[str] = None


class UserReportUpdatePayload(BaseModel):
    title: str
    source_org: Optional[str] = None
    industry_tags: list[str] = []
    region_tags: list[str] = []
    notes: Optional[str] = None
    is_favorite: bool = False


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def _build_admin_session_value() -> str:
    expires_at = int(time.time()) + ADMIN_SESSION_MAX_AGE
    signature = sha256(f"{ADMIN_INVITE_KEY}:{expires_at}:{BASE_DIR}".encode("utf-8")).hexdigest()
    return f"{expires_at}:{signature}"


def _has_admin_session(request: Request) -> bool:
    raw_cookie = (request.cookies.get(ADMIN_SESSION_COOKIE) or "").strip()
    if not raw_cookie or ":" not in raw_cookie:
        return False
    expires_at_str, signature = raw_cookie.split(":", 1)
    if not expires_at_str.isdigit():
        return False
    expires_at = int(expires_at_str)
    if expires_at < int(time.time()):
        return False
    expected = sha256(f"{ADMIN_INVITE_KEY}:{expires_at}:{BASE_DIR}".encode("utf-8")).hexdigest()
    return secrets.compare_digest(signature, expected)


def _require_admin(request: Request, admin_key: str | None = None) -> None:
    if _has_admin_session(request):
        return
    if admin_key == ADMIN_INVITE_KEY:
        return
    raise HTTPException(status_code=403, detail="ADMIN_REQUIRED")


def _normalize_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def _ensure_schema() -> None:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    conn = _get_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS industry_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source_org TEXT NOT NULL,
            source_url TEXT NOT NULL,
            publish_date TEXT,
            industry_tags TEXT DEFAULT '[]',
            region_tags TEXT DEFAULT '[]',
            report_type TEXT,
            summary TEXT,
            cover_image_url TEXT,
            is_featured INTEGER DEFAULT 0,
            click_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_name TEXT,
            file_size INTEGER,
            file_type TEXT,
            source_org TEXT,
            industry_tags TEXT DEFAULT '[]',
            region_tags TEXT DEFAULT '[]',
            notes TEXT,
            is_favorite INTEGER DEFAULT 0,
            is_shared INTEGER DEFAULT 0,
            shared_at TIMESTAMP,
            share_status TEXT DEFAULT 'private',
            share_review_note TEXT,
            download_count INTEGER DEFAULT 0,
            like_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS report_bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            report_id INTEGER,
            user_report_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_report_bookmarks_nav
            ON report_bookmarks(user_id, report_id) WHERE report_id IS NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_report_bookmarks_user
            ON report_bookmarks(user_id, user_report_id) WHERE user_report_id IS NOT NULL;
        CREATE TABLE IF NOT EXISTS report_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            user_report_id INTEGER NOT NULL REFERENCES user_reports(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, user_report_id)
        );
        CREATE INDEX IF NOT EXISTS idx_reports_source ON industry_reports(source_org);
        CREATE INDEX IF NOT EXISTS idx_reports_date ON industry_reports(publish_date DESC);
        CREATE INDEX IF NOT EXISTS idx_user_reports_user ON user_reports(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_reports_shared ON user_reports(share_status);
        """
    )
    count = cur.execute("SELECT COUNT(*) FROM industry_reports").fetchone()[0]
    if count == 0:
        cur.executemany(
            """
            INSERT INTO industry_reports
            (title, source_org, source_url, publish_date, industry_tags, region_tags, report_type, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["title"],
                    item["source_org"],
                    item["source_url"],
                    item.get("publish_date"),
                    serialize_tags(item.get("industry_tags", [])),
                    serialize_tags(item.get("region_tags", [])),
                    item.get("report_type"),
                    item.get("summary"),
                )
                for item in INITIAL_REPORTS
            ],
        )
    conn.commit()
    conn.close()


def _row_to_industry_report(row: sqlite3.Row, bookmarked: bool = False) -> dict[str, Any]:
    data = dict(row)
    data["industry_tags"] = deserialize_tags(data.get("industry_tags"))
    data["region_tags"] = deserialize_tags(data.get("region_tags"))
    data["is_featured"] = bool(data.get("is_featured"))
    data["bookmarked"] = bookmarked
    return data


def _row_to_user_report(row: sqlite3.Row, bookmarked: bool = False) -> dict[str, Any]:
    data = dict(row)
    data["industry_tags"] = deserialize_tags(data.get("industry_tags"))
    data["region_tags"] = deserialize_tags(data.get("region_tags"))
    data["is_favorite"] = bool(data.get("is_favorite"))
    data["is_shared"] = bool(data.get("is_shared"))
    data["bookmarked"] = bookmarked
    return data


def _apply_report_filters(base_sql: str, params: list[Any], *, source_org: str = "", industry: str = "", region: str = "", report_type: str = "", search: str = "") -> tuple[str, list[Any]]:
    sql = base_sql
    if source_org:
        sql += " AND source_org = ?"
        params.append(source_org)
    if report_type:
        sql += " AND report_type = ?"
        params.append(report_type)
    if industry:
        sql += " AND industry_tags LIKE ?"
        params.append(f'%"{industry}"%')
    if region:
        sql += " AND region_tags LIKE ?"
        params.append(f'%"{region}"%')
    if search:
        sql += " AND (title LIKE ? OR summary LIKE ? OR source_org LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    return sql, params


@router.get("/industry-reports")
async def list_industry_reports(
    page: int = 1,
    limit: int = 20,
    source_org: str = "",
    industry: str = "",
    region: str = "",
    report_type: str = "",
    search: str = "",
    sort: str = "publish_date",
    authorization: Optional[str] = Header(None),
):
    _ensure_schema()
    user = None
    if authorization:
        try:
            user = _get_user(authorization)
        except HTTPException:
            user = None
    limit = max(1, min(limit, 50))
    offset = (max(page, 1) - 1) * limit
    conn = _get_conn()
    sql, params = _apply_report_filters(
        "SELECT * FROM industry_reports WHERE 1=1",
        [],
        source_org=source_org,
        industry=industry,
        region=region,
        report_type=report_type,
        search=search,
    )
    count_row = conn.execute(f"SELECT COUNT(*) FROM ({sql}) AS filtered_reports", params).fetchone()
    order_sql = "click_count DESC, publish_date DESC" if sort == "click_count" else "publish_date DESC, id DESC"
    rows = conn.execute(f"{sql} ORDER BY is_featured DESC, {order_sql} LIMIT ? OFFSET ?", [*params, limit, offset]).fetchall()
    bookmarked_ids = set()
    if user:
        bookmarked_ids = {
            row["report_id"]
            for row in conn.execute("SELECT report_id FROM report_bookmarks WHERE user_id=? AND report_id IS NOT NULL", (user["id"],)).fetchall()
        }
    conn.close()
    return {
        "items": [_row_to_industry_report(row, row["id"] in bookmarked_ids) for row in rows],
        "page": page,
        "limit": limit,
        "total": count_row[0] if count_row else 0,
    }


@router.get("/industry-reports/{report_id}")
async def get_industry_report(report_id: int):
    _ensure_schema()
    conn = _get_conn()
    conn.execute("UPDATE industry_reports SET click_count = click_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id=?", (report_id,))
    conn.commit()
    row = conn.execute("SELECT * FROM industry_reports WHERE id=?", (report_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="REPORT_NOT_FOUND")
    return _row_to_industry_report(row)


@router.post("/industry-reports/{report_id}/bookmark")
async def toggle_industry_report_bookmark(report_id: int, authorization: Optional[str] = Header(None)):
    _ensure_schema()
    user = _get_user(authorization)
    conn = _get_conn()
    existing = conn.execute(
        "SELECT id FROM report_bookmarks WHERE user_id=? AND report_id=?",
        (user["id"], report_id),
    ).fetchone()
    if existing:
        conn.execute("DELETE FROM report_bookmarks WHERE id=?", (existing["id"],))
        bookmarked = False
    else:
        conn.execute("INSERT INTO report_bookmarks (user_id, report_id) VALUES (?, ?)", (user["id"], report_id))
        bookmarked = True
    conn.commit()
    conn.close()
    return {"bookmarked": bookmarked}


@router.get("/industry-reports/bookmarks")
async def list_industry_report_bookmarks(authorization: Optional[str] = Header(None)):
    _ensure_schema()
    user = _get_user(authorization)
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT ir.* FROM report_bookmarks rb
        JOIN industry_reports ir ON ir.id = rb.report_id
        WHERE rb.user_id=?
        ORDER BY rb.created_at DESC
        """,
        (user["id"],),
    ).fetchall()
    conn.close()
    return [_row_to_industry_report(row, True) for row in rows]


@router.post("/admin/industry-reports")
async def create_industry_report(payload: IndustryReportPayload, request: Request, x_admin_key: str = Header(default="")):
    _ensure_schema()
    _require_admin(request, x_admin_key)
    conn = _get_conn()
    cur = conn.execute(
        """
        INSERT INTO industry_reports
        (title, source_org, source_url, publish_date, industry_tags, region_tags, report_type, summary, cover_image_url, is_featured, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            payload.title,
            payload.source_org,
            payload.source_url,
            payload.publish_date,
            serialize_tags(payload.industry_tags),
            serialize_tags(payload.region_tags),
            payload.report_type,
            payload.summary,
            payload.cover_image_url,
            int(payload.is_featured),
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM industry_reports WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    return _row_to_industry_report(row)


@router.put("/admin/industry-reports/{report_id}")
async def update_industry_report(report_id: int, payload: IndustryReportPayload, request: Request, x_admin_key: str = Header(default="")):
    _ensure_schema()
    _require_admin(request, x_admin_key)
    conn = _get_conn()
    conn.execute(
        """
        UPDATE industry_reports
        SET title=?, source_org=?, source_url=?, publish_date=?, industry_tags=?, region_tags=?,
            report_type=?, summary=?, cover_image_url=?, is_featured=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=?
        """,
        (
            payload.title,
            payload.source_org,
            payload.source_url,
            payload.publish_date,
            serialize_tags(payload.industry_tags),
            serialize_tags(payload.region_tags),
            payload.report_type,
            payload.summary,
            payload.cover_image_url,
            int(payload.is_featured),
            report_id,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM industry_reports WHERE id=?", (report_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="REPORT_NOT_FOUND")
    return _row_to_industry_report(row)


@router.delete("/admin/industry-reports/{report_id}")
async def delete_industry_report(report_id: int, request: Request, x_admin_key: str = Header(default="")):
    _ensure_schema()
    _require_admin(request, x_admin_key)
    conn = _get_conn()
    conn.execute("DELETE FROM industry_reports WHERE id=?", (report_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/user-reports")
async def list_user_reports(
    search: str = "",
    industry: str = "",
    authorization: Optional[str] = Header(None),
):
    _ensure_schema()
    user = _get_user(authorization)
    conn = _get_conn()
    sql = "SELECT * FROM user_reports WHERE user_id=?"
    params: list[Any] = [user["id"]]
    if industry:
        sql += " AND industry_tags LIKE ?"
        params.append(f'%"{industry}"%')
    if search:
        sql += " AND (title LIKE ? OR notes LIKE ? OR source_org LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    rows = conn.execute(f"{sql} ORDER BY created_at DESC", params).fetchall()
    conn.close()
    return [_row_to_user_report(row) for row in rows]


@router.post("/user-reports/upload")
async def upload_user_report(
    authorization: Optional[str] = Header(None),
    file: UploadFile = File(...),
    title: str = Form(...),
    source_org: str = Form(default=""),
    industry_tags: str = Form(default=""),
    region_tags: str = Form(default=""),
    notes: str = Form(default=""),
    share_to_community: bool = Form(default=False),
):
    _ensure_schema()
    user = _get_user(authorization)
    ext = _normalize_extension(file.filename or "")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="FILE_TYPE_NOT_ALLOWED")
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="FILE_TOO_LARGE")
    conn = _get_conn()
    count = conn.execute("SELECT COUNT(*) FROM user_reports WHERE user_id=?", (user["id"],)).fetchone()[0]
    if count >= MAX_FILES_PER_USER:
        conn.close()
        raise HTTPException(status_code=400, detail="USER_REPORT_LIMIT_REACHED")
    user_dir = UPLOAD_ROOT / str(user["id"])
    user_dir.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_filename(file.filename or title)
    stored_name = f"{int(time.time())}-{safe_name}"
    target = user_dir / stored_name
    target.write_bytes(content)
    share_status = "pending" if share_to_community else "private"
    is_shared = 1 if share_to_community else 0
    cur = conn.execute(
        """
        INSERT INTO user_reports
        (user_id, title, file_path, file_name, file_size, file_type, source_org, industry_tags, region_tags, notes, is_shared, shared_at, share_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CASE WHEN ?=1 THEN CURRENT_TIMESTAMP ELSE NULL END, ?)
        """,
        (
            user["id"],
            title,
            str(target),
            file.filename or stored_name,
            len(content),
            ext.lstrip("."),
            source_org,
            serialize_tags(parse_tags(industry_tags)),
            serialize_tags(parse_tags(region_tags)),
            notes,
            is_shared,
            is_shared,
            share_status,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM user_reports WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    return _row_to_user_report(row)


@router.get("/user-reports/{report_id}/download")
async def download_user_report(report_id: int, authorization: Optional[str] = Header(None)):
    _ensure_schema()
    user = _get_user(authorization)
    conn = _get_conn()
    row = conn.execute("SELECT * FROM user_reports WHERE id=? AND user_id=?", (report_id, user["id"])).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="REPORT_NOT_FOUND")
    path = Path(row["file_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="FILE_NOT_FOUND")
    return FileResponse(path, filename=row["file_name"] or path.name)


@router.put("/user-reports/{report_id}")
async def update_user_report(report_id: int, payload: UserReportUpdatePayload, authorization: Optional[str] = Header(None)):
    _ensure_schema()
    user = _get_user(authorization)
    conn = _get_conn()
    conn.execute(
        """
        UPDATE user_reports
        SET title=?, source_org=?, industry_tags=?, region_tags=?, notes=?, is_favorite=?
        WHERE id=? AND user_id=?
        """,
        (
            payload.title,
            payload.source_org,
            serialize_tags(payload.industry_tags),
            serialize_tags(payload.region_tags),
            payload.notes,
            int(payload.is_favorite),
            report_id,
            user["id"],
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM user_reports WHERE id=? AND user_id=?", (report_id, user["id"])).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="REPORT_NOT_FOUND")
    return _row_to_user_report(row)


@router.delete("/user-reports/{report_id}")
async def delete_user_report(report_id: int, authorization: Optional[str] = Header(None)):
    _ensure_schema()
    user = _get_user(authorization)
    conn = _get_conn()
    row = conn.execute("SELECT * FROM user_reports WHERE id=? AND user_id=?", (report_id, user["id"])).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="REPORT_NOT_FOUND")
    conn.execute("DELETE FROM report_likes WHERE user_report_id=?", (report_id,))
    conn.execute("DELETE FROM report_bookmarks WHERE user_report_id=?", (report_id,))
    conn.execute("DELETE FROM user_reports WHERE id=? AND user_id=?", (report_id, user["id"]))
    conn.commit()
    conn.close()
    path = Path(row["file_path"])
    if path.exists():
        path.unlink()
    return {"ok": True}


@router.post("/user-reports/{report_id}/share")
async def share_user_report(report_id: int, authorization: Optional[str] = Header(None)):
    _ensure_schema()
    user = _get_user(authorization)
    conn = _get_conn()
    conn.execute(
        """
        UPDATE user_reports
        SET is_shared=1, share_status='pending', shared_at=CURRENT_TIMESTAMP, share_review_note=NULL
        WHERE id=? AND user_id=?
        """,
        (report_id, user["id"]),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM user_reports WHERE id=? AND user_id=?", (report_id, user["id"])).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="REPORT_NOT_FOUND")
    return _row_to_user_report(row)


@router.post("/user-reports/{report_id}/unshare")
async def unshare_user_report(report_id: int, authorization: Optional[str] = Header(None)):
    _ensure_schema()
    user = _get_user(authorization)
    conn = _get_conn()
    conn.execute(
        """
        UPDATE user_reports
        SET is_shared=0, share_status='private', shared_at=NULL
        WHERE id=? AND user_id=?
        """,
        (report_id, user["id"]),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM user_reports WHERE id=? AND user_id=?", (report_id, user["id"])).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="REPORT_NOT_FOUND")
    return _row_to_user_report(row)


@router.get("/shared-reports")
async def list_shared_reports(
    page: int = 1,
    limit: int = 20,
    industry: str = "",
    sort: str = "shared_at",
    search: str = "",
    authorization: Optional[str] = Header(None),
):
    _ensure_schema()
    user = None
    if authorization:
        try:
            user = _get_user(authorization)
        except HTTPException:
            user = None
    limit = max(1, min(limit, 50))
    offset = (max(page, 1) - 1) * limit
    conn = _get_conn()
    sql = """
    SELECT ur.*, u.nickname AS shared_by_nickname
    FROM user_reports ur
    JOIN users u ON u.id = ur.user_id
    WHERE ur.share_status='approved'
    """
    params: list[Any] = []
    if industry:
        sql += " AND ur.industry_tags LIKE ?"
        params.append(f'%"{industry}"%')
    if search:
        sql += " AND (ur.title LIKE ? OR ur.notes LIKE ? OR ur.source_org LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    count_row = conn.execute(f"SELECT COUNT(*) FROM ({sql}) AS filtered_shared_reports", params).fetchone()
    order_sql = {
        "download_count": "ur.download_count DESC, ur.shared_at DESC",
        "like_count": "ur.like_count DESC, ur.shared_at DESC",
    }.get(sort, "ur.shared_at DESC")
    rows = conn.execute(f"{sql} ORDER BY {order_sql} LIMIT ? OFFSET ?", [*params, limit, offset]).fetchall()
    bookmarked_ids = set()
    if user:
        bookmarked_ids = {
            row["user_report_id"]
            for row in conn.execute("SELECT user_report_id FROM report_bookmarks WHERE user_id=? AND user_report_id IS NOT NULL", (user["id"],)).fetchall()
        }
    conn.close()
    items = []
    for row in rows:
        item = _row_to_user_report(row, row["id"] in bookmarked_ids)
        item["shared_by_nickname"] = row["shared_by_nickname"]
        items.append(item)
    return {"items": items, "page": page, "limit": limit, "total": count_row[0] if count_row else 0}


@router.get("/shared-reports/{report_id}/download")
async def download_shared_report(report_id: int):
    _ensure_schema()
    conn = _get_conn()
    row = conn.execute("SELECT * FROM user_reports WHERE id=? AND share_status='approved'", (report_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="REPORT_NOT_FOUND")
    conn.execute("UPDATE user_reports SET download_count = download_count + 1 WHERE id=?", (report_id,))
    conn.commit()
    conn.close()
    path = Path(row["file_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="FILE_NOT_FOUND")
    return FileResponse(path, filename=row["file_name"] or path.name)


@router.post("/shared-reports/{report_id}/like")
async def toggle_shared_report_like(report_id: int, authorization: Optional[str] = Header(None)):
    _ensure_schema()
    user = _get_user(authorization)
    conn = _get_conn()
    row = conn.execute("SELECT * FROM user_reports WHERE id=? AND share_status='approved'", (report_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="REPORT_NOT_FOUND")
    existing = conn.execute(
        "SELECT id FROM report_likes WHERE user_id=? AND user_report_id=?",
        (user["id"], report_id),
    ).fetchone()
    if existing:
        conn.execute("DELETE FROM report_likes WHERE id=?", (existing["id"],))
        conn.execute("UPDATE user_reports SET like_count = CASE WHEN like_count > 0 THEN like_count - 1 ELSE 0 END WHERE id=?", (report_id,))
        liked = False
    else:
        conn.execute("INSERT INTO report_likes (user_id, user_report_id) VALUES (?, ?)", (user["id"], report_id))
        conn.execute("UPDATE user_reports SET like_count = like_count + 1 WHERE id=?", (report_id,))
        liked = True
    conn.commit()
    like_count = conn.execute("SELECT like_count FROM user_reports WHERE id=?", (report_id,)).fetchone()["like_count"]
    conn.close()
    return {"liked": liked, "like_count": like_count}


@router.post("/shared-reports/{report_id}/bookmark")
async def toggle_shared_report_bookmark(report_id: int, authorization: Optional[str] = Header(None)):
    _ensure_schema()
    user = _get_user(authorization)
    conn = _get_conn()
    existing = conn.execute(
        "SELECT id FROM report_bookmarks WHERE user_id=? AND user_report_id=?",
        (user["id"], report_id),
    ).fetchone()
    if existing:
        conn.execute("DELETE FROM report_bookmarks WHERE id=?", (existing["id"],))
        bookmarked = False
    else:
        conn.execute("INSERT INTO report_bookmarks (user_id, user_report_id) VALUES (?, ?)", (user["id"], report_id))
        bookmarked = True
    conn.commit()
    conn.close()
    return {"bookmarked": bookmarked}


@router.get("/admin/shared-reports/pending")
async def list_pending_shared_reports(request: Request, x_admin_key: str = Header(default="")):
    _ensure_schema()
    _require_admin(request, x_admin_key)
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT ur.*, u.nickname AS uploader_nickname, u.email AS uploader_email
        FROM user_reports ur
        JOIN users u ON u.id = ur.user_id
        WHERE ur.share_status='pending'
        ORDER BY ur.shared_at DESC, ur.created_at DESC
        """
    ).fetchall()
    conn.close()
    items = []
    for row in rows:
        item = _row_to_user_report(row)
        item["uploader_nickname"] = row["uploader_nickname"]
        item["uploader_email"] = row["uploader_email"]
        items.append(item)
    return items


@router.post("/admin/shared-reports/{report_id}/approve")
async def approve_shared_report(report_id: int, request: Request, x_admin_key: str = Header(default="")):
    _ensure_schema()
    _require_admin(request, x_admin_key)
    conn = _get_conn()
    conn.execute(
        "UPDATE user_reports SET is_shared=1, share_status='approved', share_review_note=NULL, shared_at=COALESCE(shared_at, CURRENT_TIMESTAMP) WHERE id=?",
        (report_id,),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM user_reports WHERE id=?", (report_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="REPORT_NOT_FOUND")
    return _row_to_user_report(row)


@router.post("/admin/shared-reports/{report_id}/reject")
async def reject_shared_report(report_id: int, payload: ReviewPayload, request: Request, x_admin_key: str = Header(default="")):
    _ensure_schema()
    _require_admin(request, x_admin_key)
    conn = _get_conn()
    conn.execute(
        """
        UPDATE user_reports
        SET is_shared=0, share_status='rejected', share_review_note=?
        WHERE id=?
        """,
        (payload.reason or "未通过审核", report_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM user_reports WHERE id=?", (report_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="REPORT_NOT_FOUND")
    return _row_to_user_report(row)


@router.delete("/admin/shared-reports/{report_id}")
async def admin_remove_shared_report(report_id: int, request: Request, x_admin_key: str = Header(default="")):
    _ensure_schema()
    _require_admin(request, x_admin_key)
    conn = _get_conn()
    conn.execute("UPDATE user_reports SET is_shared=0, share_status='private', share_review_note='管理员下架' WHERE id=?", (report_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/admin/shared-reports/{report_id}/download")
async def admin_download_shared_report(report_id: int, request: Request, x_admin_key: str = Header(default="")):
    _ensure_schema()
    _require_admin(request, x_admin_key)
    conn = _get_conn()
    row = conn.execute("SELECT * FROM user_reports WHERE id=?", (report_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="REPORT_NOT_FOUND")
    path = Path(row["file_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="FILE_NOT_FOUND")
    return FileResponse(path, filename=row["file_name"] or path.name)
