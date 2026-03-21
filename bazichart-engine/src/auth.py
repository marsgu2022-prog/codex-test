"""用户认证模块"""
from __future__ import annotations
import sqlite3
import hashlib
import hmac
import os
import time
import json
import base64
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "users.db"
SECRET_KEY = os.environ.get("JWT_SECRET", "bazichart-secret-2026")


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
    salt = os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}:{h.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, h = password_hash.split(":", 1)
        expected = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return hmac.compare_digest(h, expected.hex())
    except Exception:
        return False


def create_token(user_id: int, email: str) -> str:
    """创建JWT-like token"""
    payload = {"sub": user_id, "email": email, "exp": int(time.time()) + 7 * 24 * 3600}
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{sig}"


def verify_token(token: str) -> Optional[dict]:
    """验证token，返回payload或None"""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        encoded, sig = parts
        expected_sig = hmac.new(SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(encoded).decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
