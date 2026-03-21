"""用户认证模块"""
from __future__ import annotations
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import bcrypt
import jwt

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "users.db"

_SECRET_KEY: Optional[str] = None


def _get_secret() -> str:
    global _SECRET_KEY
    if _SECRET_KEY is None:
        key = os.environ.get("JWT_SECRET")
        if not key:
            raise RuntimeError("JWT_SECRET 环境变量未设置，请在 .env 文件中配置")
        _SECRET_KEY = key
    return _SECRET_KEY


def init_users_db():
    """初始化用户数据库"""
    conn = sqlite3.connect(str(DB_FILE))
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nickname TEXT,
        free_readings_remaining INTEGER DEFAULT 2,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS archives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        name TEXT NOT NULL,
        gender TEXT,
        birth_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS readings (
        id TEXT PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        archive_id INTEGER REFERENCES archives(id),
        input_data TEXT NOT NULL,
        bazi_result TEXT,
        reading_text TEXT,
        reading_type TEXT DEFAULT 'free',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """验证 bcrypt 密码"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_token(user_id: int, email: str) -> str:
    """创建 PyJWT token，7天过期"""
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(tz=timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, _get_secret(), algorithm="HS256")


def verify_token(token: str) -> Optional[dict]:
    """验证 token，返回 payload 或 None"""
    try:
        return jwt.decode(token, _get_secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
