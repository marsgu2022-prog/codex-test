"""档案API路由"""
from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "users.db"

router = APIRouter()


def _get_user(authorization: Optional[str]):
    import sys
    if str(BASE_DIR / "src") not in sys.path:
        sys.path.insert(0, str(BASE_DIR / "src"))
    from auth import verify_token, get_user_by_id
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    payload = verify_token(authorization[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Token无效")
    user = get_user_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


class ArchiveCreate(BaseModel):
    name: str
    gender: str
    birth_data: dict


@router.get("/archives")
async def list_archives(authorization: Optional[str] = Header(None)):
    user = _get_user(authorization)
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM archives WHERE user_id=? ORDER BY created_at DESC",
        (user["id"],)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/archives")
async def create_archive(payload: ArchiveCreate, authorization: Optional[str] = Header(None)):
    user = _get_user(authorization)
    conn = sqlite3.connect(str(DB_FILE))
    cur = conn.execute(
        "INSERT INTO archives (user_id, name, gender, birth_data) VALUES (?,?,?,?)",
        (user["id"], payload.name, payload.gender, json.dumps(payload.birth_data))
    )
    archive_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"id": archive_id, "name": payload.name}


@router.delete("/archives/{archive_id}")
async def delete_archive(archive_id: int, authorization: Optional[str] = Header(None)):
    user = _get_user(authorization)
    conn = sqlite3.connect(str(DB_FILE))
    conn.execute(
        "DELETE FROM archives WHERE id=? AND user_id=?",
        (archive_id, user["id"])
    )
    conn.commit()
    conn.close()
    return {"ok": True}
