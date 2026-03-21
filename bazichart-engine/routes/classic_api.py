"""古籍参考API路由"""
from __future__ import annotations
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

BASE_DIR = Path(__file__).resolve().parent.parent
METADATA_DIR = BASE_DIR / "data" / "metadata"

router = APIRouter()


@router.get("/classic/{day_stem}/{month_branch}")
async def get_classic(day_stem: str, month_branch: str):
    """根据日干和月支查询古籍参考"""
    result = {"day_stem": day_stem, "month_branch": month_branch}

    # 穷通宝鉴
    try:
        tiaohuo = json.loads((METADATA_DIR / "tiaohuo_table.json").read_text(encoding="utf-8"))
        # 尝试匹配
        key = f"{day_stem}_{month_branch}"
        match = tiaohuo.get(key) or tiaohuo.get(day_stem) or {}
        result["qiongtong"] = match
    except Exception:
        result["qiongtong"] = {}

    # 实战规则
    try:
        rules = json.loads((METADATA_DIR / "rule_fragments.json").read_text(encoding="utf-8"))
        matched = [r for r in rules if isinstance(r, dict) and
                   (r.get("stem") == day_stem or r.get("branch") == month_branch)]
        result["rules"] = matched[:5]
    except Exception:
        result["rules"] = []

    # 流派矛盾
    try:
        contras = json.loads((METADATA_DIR / "contradictions.json").read_text(encoding="utf-8"))
        matched = [c for c in contras if isinstance(c, dict) and
                   (c.get("stem") == day_stem or day_stem in str(c))]
        result["contradictions"] = matched[:3]
    except Exception:
        result["contradictions"] = []

    return result
