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
    try:
        from auth import init_users_db, hash_password, create_token
    except ImportError as e:
        raise HTTPException(status_code=503, detail="SERVICE_UNAVAILABLE")
    init_users_db()
    try:
        conn = sqlite3.connect(str(DB_FILE))
        conn.row_factory = sqlite3.Row
        existing = conn.execute("SELECT id FROM users WHERE email=?", (payload.email,)).fetchone()
        if existing:
            conn.close()
            raise HTTPException(status_code=400, detail="EMAIL_ALREADY_REGISTERED")
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
    except Exception:
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR")


@router.post("/login")
async def login(payload: LoginRequest):
    import sys
    if str(BASE_DIR / "src") not in sys.path:
        sys.path.insert(0, str(BASE_DIR / "src"))
    try:
        from auth import verify_password, create_token
    except ImportError:
        raise HTTPException(status_code=503, detail="SERVICE_UNAVAILABLE")
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE email=?", (payload.email,)).fetchone()
    conn.close()
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="INVALID_CREDENTIALS")
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
    try:
        from auth import verify_token, get_user_by_id
    except ImportError:
        raise HTTPException(status_code=503, detail="SERVICE_UNAVAILABLE")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="UNAUTHORIZED")
    token = authorization[7:]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="TOKEN_INVALID_OR_EXPIRED")
    user = get_user_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")
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
