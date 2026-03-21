from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import random
import sqlite3
import string
from typing import Dict, List, Tuple

BASE_DIR = Path(__file__).resolve().parent
INVITE_DB_PATH = BASE_DIR / "invites.db"
CODE_ALPHABET = string.ascii_uppercase + string.digits


def _get_connection() -> sqlite3.Connection:
    INVITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        INVITE_DB_PATH,
        detect_types=sqlite3.PARSE_DECLTYPES,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS invite_codes (
          code TEXT PRIMARY KEY,
          max_uses INTEGER DEFAULT 10,
          used_count INTEGER DEFAULT 0,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          expires_at TEXT,
          disabled INTEGER DEFAULT 0,
          note TEXT
        );
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS invite_usage_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          code TEXT,
          endpoint TEXT,
          client_ip TEXT,
          used_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    cursor.close()
    conn.close()


def _random_code_body(length: int = 8) -> str:
    return "".join(random.choice(CODE_ALPHABET) for _ in range(length))


def generate_code(
    prefix: str = "BZ",
    max_uses: int = 10,
    expires_days: int | None = 30,
    note: str = "",
) -> str:
    expires_at: str | None = None
    if expires_days is not None and expires_days > 0:
        expires_at = (datetime.utcnow() + timedelta(days=expires_days)).isoformat()
    attempts = 0
    while attempts < 10:
        body = _random_code_body()
        code = f"{prefix}-{body[:4]}-{body[4:]}"
        conn = None
        cursor = None
        try:
            conn = _get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO invite_codes (code, max_uses, expires_at, note)
                VALUES (?, ?, ?, ?)
                """,
                (code, max_uses, expires_at, note),
            )
            conn.commit()
            return code
        except sqlite3.IntegrityError:
            attempts += 1
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    raise RuntimeError("无法生成唯一的邀请码")


def validate_code(code: str) -> Tuple[bool, str]:
    normalized = (code or "").strip().upper()
    if not normalized:
        return False, "邀请码不能为空"
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT max_uses, used_count, disabled, expires_at FROM invite_codes WHERE code = ?",
        (normalized,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row is None:
        return False, "邀请码不存在"
    if row["disabled"]:
        return False, "邀请码已被禁用"
    expires_at = row["expires_at"]
    if expires_at:
        try:
            expires_dt = datetime.fromisoformat(expires_at)
        except ValueError:
            expires_dt = None
        if expires_dt and expires_dt < datetime.utcnow():
            return False, "邀请码已过期"
    if row["used_count"] >= row["max_uses"]:
        return False, "邀请码已用完"
    return True, "ok"


def consume_code(code: str, endpoint: str, client_ip: str) -> None:
    normalized = code.strip().upper()
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE invite_codes SET used_count = used_count + 1 WHERE code = ?",
        (normalized,),
    )
    cursor.execute(
        """
        INSERT INTO invite_usage_log (code, endpoint, client_ip)
        VALUES (?, ?, ?)
        """,
        (normalized, endpoint, client_ip),
    )
    conn.commit()
    cursor.close()
    conn.close()


def list_codes() -> List[Dict[str, str | int | None]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT code, max_uses, used_count, created_at, expires_at, disabled, note
        FROM invite_codes
        ORDER BY created_at DESC
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [
        {
            "code": row["code"],
            "max_uses": row["max_uses"],
            "used_count": row["used_count"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
            "disabled": bool(row["disabled"]),
            "note": row["note"],
        }
        for row in rows
    ]


def disable_code(code: str) -> bool:
    normalized = (code or "").strip().upper()
    if not normalized:
        return False
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE invite_codes SET disabled = 1 WHERE code = ?",
        (normalized,),
    )
    updated = cursor.rowcount > 0
    conn.commit()
    cursor.close()
    conn.close()
    return updated
