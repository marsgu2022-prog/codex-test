"""认证API路由"""
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "users.db"

router = APIRouter()


class RegisterRequest(BaseModel):
    email: str
    password: str
    nickname: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register")
async def register(payload: RegisterRequest):
    import sys
    if str(BASE_DIR / "src") not in sys.path:
        sys.path.insert(0, str(BASE_DIR / "src"))
    from auth import init_users_db, hash_password, create_token
    init_users_db()
    try:
        conn = sqlite3.connect(str(DB_FILE))
        conn.row_factory = sqlite3.Row
        # 检查邮箱是否已注册
        existing = conn.execute("SELECT id FROM users WHERE email=?", (payload.email,)).fetchone()
        if existing:
            conn.close()
            raise HTTPException(status_code=400, detail="邮箱已注册")
        pw_hash = hash_password(payload.password)
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, nickname) VALUES (?,?,?)",
            (payload.email, pw_hash, payload.nickname or payload.email.split("@")[0])
        )
        user_id = cur.lastrowid
        conn.commit()
        conn.close()
        token = create_token(user_id, payload.email)
        return {"token": token, "free_readings": 2, "user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def login(payload: LoginRequest):
    import sys
    if str(BASE_DIR / "src") not in sys.path:
        sys.path.insert(0, str(BASE_DIR / "src"))
    from auth import verify_password, create_token
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE email=?", (payload.email,)).fetchone()
    conn.close()
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    token = create_token(user["id"], user["email"])
    return {
        "token": token,
        "remaining_readings": user["free_readings_remaining"],
        "nickname": user["nickname"],
    }


@router.get("/profile")
async def profile(authorization: Optional[str] = Header(None)):
    import sys
    if str(BASE_DIR / "src") not in sys.path:
        sys.path.insert(0, str(BASE_DIR / "src"))
    from auth import verify_token, get_user_by_id
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization[7:]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token无效或已过期")
    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    conn = sqlite3.connect(str(DB_FILE))
    archives_count = conn.execute(
        "SELECT COUNT(*) FROM archives WHERE user_id=?", (user["id"],)
    ).fetchone()[0]
    conn.close()
    return {
        "email": user["email"],
        "nickname": user["nickname"],
        "remaining_readings": user["free_readings_remaining"],
        "archives_count": archives_count,
    }
