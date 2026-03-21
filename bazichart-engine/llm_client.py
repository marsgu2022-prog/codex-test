"""
DeepSeek LLM 客户端 — 两轮深度八字解读

调用流程：
  第一轮：格局 + 用神 + 日主画像 + 十神解读
  第二轮：大运流年 + 月运年运 + 趋吉建议 + 健康预警

API key 从环境变量 DEEPSEEK_API_KEY 读取。
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from threading import Lock
from typing import Any

import httpx

logger = logging.getLogger("bazichart_engine_api")

# 延迟导入 i18n_utils（在 generate_deep_interpretation 中使用）

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"
DATA_DIR = Path(__file__).resolve().parent / "data"
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
USAGE_STATE_FILE = LOG_DIR / "deepseek_usage_state.json"

CORE_KNOWLEDGE_FILES = [
    "BAZI.md",
    "BAZI_AI_REFERENCE.md",
    "ZIPING_YONGSHEN.md",
]
MAX_KNOWLEDGE_CHARS = 2200
TCM_KNOWLEDGE_FILE = "ni_haixia_tcm.md"
MAX_TCM_KNOWLEDGE_CHARS = 900
DAILY_DEEP_INTERPRET_LIMIT = int(os.environ.get("DEEPSEEK_DAILY_CALL_LIMIT", "200"))
DEEPSEEK_INPUT_COST_PER_1K = float(os.environ.get("DEEPSEEK_INPUT_COST_PER_1K", "0.00027"))
DEEPSEEK_OUTPUT_COST_PER_1K = float(os.environ.get("DEEPSEEK_OUTPUT_COST_PER_1K", "0.0011"))
USAGE_STATE_LOCK = Lock()


class DailyLimitExceededError(RuntimeError):
    """DeepSeek 每日调用额度耗尽。"""


def _current_day() -> str:
    return time.strftime("%Y-%m-%d", time.localtime())


def _load_usage_state() -> dict[str, Any]:
    LOG_DIR.mkdir(exist_ok=True)
    if USAGE_STATE_FILE.exists():
        try:
            state = json.loads(USAGE_STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}
    else:
        state = {}

    day = _current_day()
    if state.get("day") != day:
        state = {
            "day": day,
            "deep_interpret_requests": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
        }
    return state


def _save_usage_state(state: dict[str, Any]) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    USAGE_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _estimate_cost_usd(usage: dict[str, Any]) -> float:
    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    completion_tokens = usage.get("completion_tokens", 0) or 0
    return round(
        (prompt_tokens / 1000) * DEEPSEEK_INPUT_COST_PER_1K
        + (completion_tokens / 1000) * DEEPSEEK_OUTPUT_COST_PER_1K,
        6,
    )


def _reserve_daily_request(client_ip: str) -> None:
    with USAGE_STATE_LOCK:
        state = _load_usage_state()
        if state["deep_interpret_requests"] >= DAILY_DEEP_INTERPRET_LIMIT:
            raise DailyLimitExceededError("今日深度解读额度已达上限，已自动降级为基础命盘")
        state["deep_interpret_requests"] += 1
        _save_usage_state(state)
    logger.warning(
        "DeepSeek 请求占用额度: day=%s ip=%s calls=%s/%s",
        _current_day(),
        client_ip,
        state["deep_interpret_requests"],
        DAILY_DEEP_INTERPRET_LIMIT,
    )


def _record_usage(client_ip: str, stage: str, usage: dict[str, Any]) -> None:
    estimated_cost = _estimate_cost_usd(usage)
    with USAGE_STATE_LOCK:
        state = _load_usage_state()
        state["total_prompt_tokens"] += usage.get("prompt_tokens", 0) or 0
        state["total_completion_tokens"] += usage.get("completion_tokens", 0) or 0
        state["total_tokens"] += usage.get("total_tokens", 0) or 0
        state["estimated_cost_usd"] = round(state["estimated_cost_usd"] + estimated_cost, 6)
        _save_usage_state(state)
    logger.info(
        "DeepSeek 用量: ts=%s ip=%s stage=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s estimated_cost_usd=%.6f",
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        client_ip,
        stage,
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
        usage.get("total_tokens", 0),
        estimated_cost,
    )


# ── 知识库 & 名人数据加载 ──

def _extract_sections(content: str, keywords: list[str], limit: int) -> str:
    snippets: list[str] = []
    lower = content.lower()
    for keyword in keywords:
        pos = lower.find(keyword.lower())
        if pos == -1:
            continue
        start = content.rfind("\n##", 0, pos)
        if start == -1:
            start = max(0, pos - 160)
        end = content.find("\n##", pos + 1)
        if end == -1:
            end = min(len(content), pos + 900)
        snippet = content[start:end].strip()
        if snippet and snippet not in snippets:
            snippets.append(snippet)
    return "\n\n".join(snippets)[:limit].strip()


def _load_tcm_knowledge() -> str:
    """只保留五行脏腑和情志映射，避免长篇中医知识拖慢模型。"""
    fpath = KNOWLEDGE_DIR / TCM_KNOWLEDGE_FILE
    if not fpath.exists():
        return (
            "五行脏腑速记：木主肝胆与筋目，火主心小肠与血脉，土主脾胃与肌肉，"
            "金主肺大肠与皮毛，水主肾膀胱与骨髓。"
            "五志：怒伤肝，喜伤心，思伤脾，忧伤肺，恐伤肾。"
        )
    content = fpath.read_text(encoding="utf-8").strip()
    picked = _extract_sections(content, ["天干与脏腑经络对应", "五志与情志疾病"], MAX_TCM_KNOWLEDGE_CHARS)
    return picked or (
        "五行脏腑速记：木主肝胆与筋目，火主心小肠与血脉，土主脾胃与肌肉，"
        "金主肺大肠与皮毛，水主肾膀胱与骨髓。"
    )


def _load_knowledge_base() -> str:
    parts: list[str] = []
    for fname in CORE_KNOWLEDGE_FILES:
        fpath = KNOWLEDGE_DIR / fname
        if not fpath.exists():
            continue
        content = fpath.read_text(encoding="utf-8").strip()
        snippet = _extract_sections(content, ["格局", "用神", "十神", "旺衰", "月令"], 900)
        if snippet:
            parts.append(snippet)
    merged = "\n\n---\n\n".join(parts)
    if merged:
        return merged[:MAX_KNOWLEDGE_CHARS].strip()
    return (
        "规则摘要：先看月令，再定日主旺衰，再辨格局，最后取用神。"
        "财官印食宜顺用，杀伤劫刃宜制化。"
        "十神要结合柱位解读：年柱看家世，月柱看环境与事业，日柱看内在关系，时柱看志向与晚景。"
    )


_DAY_PILLAR_INDEX_CACHE: dict[str, list] | None = None

def _load_day_pillar_index() -> dict[str, list]:
    global _DAY_PILLAR_INDEX_CACHE
    if _DAY_PILLAR_INDEX_CACHE is not None:
        return _DAY_PILLAR_INDEX_CACHE
    idx_path = DATA_DIR / "day_pillar_index.json"
    if idx_path.exists():
        _DAY_PILLAR_INDEX_CACHE = json.loads(idx_path.read_text(encoding="utf-8"))
    else:
        _DAY_PILLAR_INDEX_CACHE = {}
    return _DAY_PILLAR_INDEX_CACHE


def _get_famous_by_day_pillar(day_pillar: str, limit: int = 5) -> list[dict]:
    idx = _load_day_pillar_index()
    return idx.get(day_pillar, [])[:limit]


# ── 排盘数据格式化 ──

def _build_chart_summary(chart_data: dict[str, Any]) -> str:
    lines: list[str] = []

    fp = chart_data.get("four_pillars", {})
    pillars = []
    for key in ["year", "month", "day", "hour"]:
        p = fp.get(key, {})
        gan = p.get("heavenly_stem", "?")
        zhi = p.get("earthly_branch", "?")
        pillars.append(f"{gan}{zhi}")
    lines.append(f"四柱：年柱{pillars[0]}  月柱{pillars[1]}  日柱{pillars[2]}  时柱{pillars[3]}")

    wa = chart_data.get("wuxing_analysis", {})
    dm = wa.get("day_master", "")
    dm_el = wa.get("day_master_element", "")
    dm_str = wa.get("day_master_strength", "")
    if dm:
        lines.append(f"日主：{dm}（{dm_el}），日主强弱：{dm_str}")

    cg = chart_data.get("canggan", {})
    if cg:
        cg_parts = []
        for key in ["year", "month", "day", "hour"]:
            idx = ["year", "month", "day", "hour"].index(key)
            cg_parts.append(f"{'年月日时'[idx]}支藏干：{'、'.join(cg.get(key, []))}")
        lines.append("  ".join(cg_parts))

    ss = chart_data.get("shishen_per_pillar", {})
    if ss:
        ss_line = "  ".join(
            f"{'年月日时'[i]}干十神：{ss.get(k, '?')}"
            for i, k in enumerate(["year", "month", "day", "hour"])
        )
        lines.append(ss_line)

    ny = chart_data.get("nayin", {})
    if ny:
        ny_line = "  ".join(
            f"{'年月日时'[i]}柱纳音：{ny.get(k, '?')}"
            for i, k in enumerate(["year", "month", "day", "hour"])
        )
        lines.append(ny_line)

    scores = wa.get("wuxing_scores", {})
    pcts = wa.get("wuxing_percentages", {})
    if scores:
        wx_parts = [f"{k}:{v:.1f}({pcts.get(k, 0):.0f}%)" for k, v in scores.items()]
        lines.append(f"五行力量：{' '.join(wx_parts)}")

    fav = wa.get("favorable_elements", [])
    unfav = wa.get("unfavorable_elements", [])
    if fav or unfav:
        lines.append(f"喜用五行：{'、'.join(fav)}  忌用五行：{'、'.join(unfav)}")

    shensha = chart_data.get("shensha", [])
    if shensha:
        ss_list = [f"{s['name']}({s['type']},{s.get('position', '')})" for s in shensha]
        lines.append(f"神煞：{' | '.join(ss_list)}")

    dayun = chart_data.get("dayun", [])
    if dayun:
        dy_parts = []
        for dy in dayun[:8]:
            gan = dy.get("tiangan", "")
            zhi = dy.get("dizhi", "")
            sa = dy.get("start_age", "?")
            ea = dy.get("end_age", "?")
            dy_parts.append(f"{gan}{zhi}({sa}-{ea}岁)")
        lines.append(f"大运：{' → '.join(dy_parts)}")

    liunian = chart_data.get("liunian", [])
    if liunian:
        ly_parts = [f"{ly['year']}年{ly.get('tiangan', '')}{ly.get('dizhi', '')}" for ly in liunian[:5]]
        lines.append(f"近年流年：{'  '.join(ly_parts)}")

    inp = chart_data.get("input", {})
    gender = inp.get("gender", "")
    lines.append(
        f"性别：{gender}  出生：{inp.get('birth_year', '')}年"
        f"{inp.get('birth_month', '')}月{inp.get('birth_day', '')}日"
        f"{inp.get('birth_hour', '')}时"
    )

    return "\n".join(lines)


def _format_famous_context(famous: list[dict]) -> str:
    if not famous:
        return ""
    lines = ["## 同日柱名人参考"]
    for p in famous:
        name = p.get("name_zh") or p.get("name_en", "")
        field = p.get("field_zh") or p.get("field_en", "")
        birth = p.get("birth_date", "")
        lines.append(f"- {name}（{field}，{birth}）")
    return "\n".join(lines)


# ── DeepSeek API 调用 ──

def _call_deepseek(
    api_key: str,
    messages: list[dict],
    client_ip: str = "unknown",
    stage: str = "unknown",
    temperature: float = 0.7,
    max_tokens: int = 3000,
    json_mode: bool = True,
) -> tuple[str, dict]:
    """单次 DeepSeek 调用，返回 (content_text, usage_dict)。"""
    body: dict[str, Any] = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    with httpx.Client(timeout=90.0) as client:
        resp = client.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        resp.raise_for_status()

    result = resp.json()
    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = result.get("usage", {})
    _record_usage(client_ip, stage, usage)
    return content, usage


def _parse_json_response(content: str) -> dict:
    """从 LLM 响应中提取 JSON。"""
    if not content:
        raise RuntimeError("DeepSeek 返回空内容")

    def _normalize(candidate: str) -> str:
        text = candidate.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.replace("，", ",").replace("：", ":")
        text = re.sub(r",(\s*[}\]])", r"\1", text)
        text = re.sub(r'([}\]"0-9eElnru])(\s*\n\s*)(".*?":)', r'\1,\2\3', text)
        return text

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    candidates = [_normalize(content)]
    match = re.search(r"\{[\s\S]*\}", content)
    if match:
        candidates.append(_normalize(match.group()))

    for candidate in candidates:
        try:
            return json.loads(candidate, strict=False)
        except json.JSONDecodeError:
            continue

    raise RuntimeError(f"无法解析 JSON: {content[:400]}")


# ── System Prompts ──

LANGUAGE_PURITY = """
【最高优先级——语言纯净】
- 所有输出必须是简体中文，禁止英文夹杂。
- 直接给结论和推理，不铺陈，不重复，不写空话。
- 每段控制在必要长度，能用一句说清就不要写两句。
- 建议必须可执行，避免宿命化表达。
"""

SYSTEM_ROUND1 = LANGUAGE_PURITY + """你是专业八字命理师。请根据排盘数据完成以下任务：
1. 判断日主旺衰，点明帮扶和克泄的核心来源。
2. 结合月令判断格局，说明是否成格或杂气偏格。
3. 判断用神、喜神、忌神，并说明理由。
4. 结合日主和十神分布，生成日主画像与人际/情绪倾向。

## 断命规则速记
{knowledge_base}

{famous_context}

## 输出要求
输出 JSON：
- "geju_analysis": 120-220字
- "yongshen_analysis": 120-220字
- "personality_portrait": 120-220字
- "ten_gods_analysis": 数组，最多4项；每项含 "god_name"、"pillar"、"psychological_meaning"
严格输出合法 JSON。"""


SYSTEM_ROUND2 = LANGUAGE_PURITY + """你是专业八字命理师兼养生顾问。基于第一轮结论，一次完成运势与建议。

## 已确定的分析结论
{round1_context}

## 当前时间
{current_date}

## 健康映射速记
{tcm_knowledge}

## 输出要求
输出 JSON：
- "current_dayun": 80-140字
- "current_liunian": 80-140字
- "career_advice": 50-90字
- "wealth_advice": 50-90字
- "relationship_advice": 50-90字
- "health_advice": 50-90字
- "current_month": 对象，含 "month_ganzhi"、"analysis"、"scores"、"key_reminder"
- "current_year": 对象，含 "year_ganzhi"、"analysis"、"scores"、"key_months"
- "fortune_advice": 对象，含 "directions"、"colors"、"industries"、"cautions"
- "health_warning": 对象，含 "constitution"、"risk_organs"、"emotional_tendency"、"yearly_focus"、"wellness_diet"
额外要求：
- 所有字符串尽量精炼，避免重复，总输出控制在 1200 字以内
- "key_months" 最多 2 项
- "wellness_diet" 最多 3 项，单项不超过 12 字
严格输出合法 JSON。"""


# ── 主函数 ──

def generate_deep_interpretation(chart_data: dict[str, Any], client_ip: str = "unknown") -> dict[str, Any]:
    """
    两轮推演生成深度八字解读。

    Returns:
        包含所有字段的结构化解读 dict + famous_matches + _meta
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY 环境变量未配置")
    _reserve_daily_request(client_ip)

    knowledge_base = _load_knowledge_base()
    chart_summary = _build_chart_summary(chart_data)

    # 获取同日柱名人
    fp = chart_data.get("four_pillars", {})
    day_gan = fp.get("day", {}).get("heavenly_stem", "")
    day_zhi = fp.get("day", {}).get("earthly_branch", "")
    day_pillar = day_gan + day_zhi
    famous = _get_famous_by_day_pillar(day_pillar, limit=5)
    famous_context = _format_famous_context(famous)

    start = time.perf_counter()
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _acc_usage(u: dict):
        for k in total_usage:
            total_usage[k] += u.get(k, 0)

    # ── 第一轮：格局 + 用神 + 画像 + 十神 ──
    logger.info("DeepSeek 第一轮: 格局+用神+画像+十神")
    sys1 = SYSTEM_ROUND1.format(knowledge_base=knowledge_base, famous_context=famous_context)
    r1_content, r1_usage = _call_deepseek(api_key, [
        {"role": "system", "content": sys1},
        {"role": "user", "content": f"请分析以下八字命盘：\n\n{chart_summary}"},
    ], client_ip=client_ip, stage="round1", temperature=0.3, max_tokens=1500)
    _acc_usage(r1_usage)
    r1 = _parse_json_response(r1_content)

    r1_context = "\n".join(f"{k}: {v}" for k, v in r1.items() if not k.startswith("_"))

    # ── 第二轮：运势 + 建议 + 健康 ──
    logger.info("DeepSeek 第二轮: 运势+建议+健康")
    from datetime import datetime
    now = datetime.now()
    current_date = f"{now.year}年{now.month}月{now.day}日"
    tcm_knowledge = _load_tcm_knowledge()
    sys2 = SYSTEM_ROUND2.format(
        round1_context=r1_context,
        current_date=current_date, tcm_knowledge=tcm_knowledge,
    )
    r2_content, r2_usage = _call_deepseek(api_key, [
        {"role": "system", "content": sys2},
        {"role": "user", "content": f"排盘数据：\n\n{chart_summary}"},
    ], client_ip=client_ip, stage="round2", temperature=0.3, max_tokens=1800)
    _acc_usage(r2_usage)
    r2 = _parse_json_response(r2_content)

    elapsed = time.perf_counter() - start

    # 纯中文输出统一补齐为三语结构，保留现有接口兼容性。
    from i18n_utils import convert_dict_trilingual
    r1 = convert_dict_trilingual(r1)
    r2 = convert_dict_trilingual(r2)

    # 合并结果
    result: dict[str, Any] = {}
    result.update(r1)
    result.update(r2)

    # 四维建议合并为 life_advice
    advice_parts = []
    for key, label in [
        ("career_advice", "事业"),
        ("wealth_advice", "财运"),
        ("relationship_advice", "感情"),
        ("health_advice", "健康"),
    ]:
        text = r2.get(key, "")
        if text:
            advice_parts.append(f"【{label}】{text}")
        result[key] = text

    result["life_advice"] = "\n\n".join(advice_parts)

    # 新模块：本月运势、本年运势、趋吉建议、健康预警
    for key in ["current_month", "current_year", "fortune_advice", "health_warning"]:
        result[key] = r2.get(key, {})

    # 名人匹配
    result["famous_matches"] = [
        {
            "name": p.get("name_zh") or p.get("name_en", ""),
            "field": p.get("field_zh") or p.get("field_en", ""),
            "birth_date": p.get("birth_date", ""),
        }
        for p in famous
    ]

    result["_meta"] = {
        "model": DEEPSEEK_MODEL,
        "rounds": 2,
        "elapsed_ms": round(elapsed * 1000),
        "tokens_used": total_usage,
    }

    logger.info(
        f"DeepSeek 深度解读完成: {elapsed:.1f}s, 2轮, "
        f"tokens={total_usage.get('total_tokens', 0)}"
    )
    return result
