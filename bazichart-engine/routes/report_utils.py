"""产业报告中心通用工具"""
from __future__ import annotations

import json
import re
import time
from typing import Any


def parse_tags(raw: str | list[str] | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [item.strip() for item in raw if item and item.strip()]
    text = raw.strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
    return [item.strip() for item in re.split(r"[，,\n]+", text) if item.strip()]


def serialize_tags(tags: list[str]) -> str:
    return json.dumps(tags, ensure_ascii=False)


def deserialize_tags(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except (TypeError, json.JSONDecodeError):
        return []
    return []


def sanitize_filename(filename: str) -> str:
    clean = re.sub(r"[^\w.\-\u4e00-\u9fff]+", "-", filename).strip(".-")
    return clean[:120] or f"report-{int(time.time())}"
