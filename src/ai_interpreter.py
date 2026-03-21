"""
AI 解读层 — 双轨并行

轨道A（原有，保持不变）：post_interpret / get_interpret_archetypes
  静态荣格原型映射，无 LLM 调用，用于 /api/interpret 的叙事片段。

轨道B（新增）：generate_qianlong_reading
  千隆v1.2全管线：知识库热加载 + 千隆prompt + 紫微注入 + 皇极时代背景
  → DeepSeek 自然语言解读
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── 路径常量 ──────────────────────────────────────────────────────
_SRC_DIR     = Path(__file__).resolve().parent
_ENGINE_DIR  = _SRC_DIR.parent / "bazichart-engine"
_SCRIPTS_DIR = _ENGINE_DIR / "scripts"
_PROMPTS_DIR = _ENGINE_DIR / "prompts"
_DEFAULT_KNOWLEDGE_DIR = _ENGINE_DIR / "knowledge"

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL   = "deepseek-chat"
MAX_KNOWLEDGE_CHARS = 8000

# 知识库文件加载优先级
KNOWLEDGE_PRIORITY = [
    "BAZI.md",
    "JUNG_MAPPING.md",
    "READING_TECHNIQUES.md",
    "ZIWEI.md",
]


# ── 动态导入辅助 ─────────────────────────────────────────────────

def _import_script(name: str) -> Any | None:
    """从 scripts/ 目录动态导入模块，失败返回 None。"""
    path = _SCRIPTS_DIR / f"{name}.py"
    if not path.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location(f"bazichart_{name}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as exc:
        logger.warning("导入 %s 失败: %s", name, exc)
        return None


# 懒加载模块缓存
_ziwei_mod    = None
_huangji_mod  = None
_ziwei_tried  = False
_huangji_tried = False


def _get_ziwei():
    global _ziwei_mod, _ziwei_tried
    if not _ziwei_tried:
        _ziwei_mod   = _import_script("ziwei_calculator")
        _ziwei_tried = True
    return _ziwei_mod


def _get_huangji():
    global _huangji_mod, _huangji_tried
    if not _huangji_tried:
        _huangji_mod   = _import_script("huangji_calculator")
        _huangji_tried = True
    return _huangji_mod


# ════════════════════════════════════════════════════════════════
# 任务1：知识库热加载
# ════════════════════════════════════════════════════════════════

def load_knowledge_base(knowledge_dir: str | Path | None = None) -> str:
    """
    扫描 knowledge/ 目录下所有 .md 文件，返回拼接文本。
    每个文件用 '=== 文件名 ===' 分隔。
    总长度超过 MAX_KNOWLEDGE_CHARS 时，按 KNOWLEDGE_PRIORITY 截断。
    """
    kdir = Path(knowledge_dir) if knowledge_dir else _DEFAULT_KNOWLEDGE_DIR
    if not kdir.exists():
        logger.debug("知识库目录不存在: %s", kdir)
        return ""

    md_files = list(kdir.glob("*.md"))
    if not md_files:
        return ""

    # 按优先级排序：优先文件在前，其余按文件名字母序
    priority_map = {name: i for i, name in enumerate(KNOWLEDGE_PRIORITY)}
    md_files.sort(key=lambda p: (priority_map.get(p.name, len(KNOWLEDGE_PRIORITY)), p.name))

    parts: list[str] = []
    total = 0
    for fpath in md_files:
        try:
            content = fpath.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not content:
            continue
        section = f"=== {fpath.name} ===\n{content}"
        if total + len(section) > MAX_KNOWLEDGE_CHARS:
            remaining = MAX_KNOWLEDGE_CHARS - total
            if remaining > 200:
                section = section[:remaining].rstrip() + "\n[（已截断）]"
                parts.append(section)
            break
        parts.append(section)
        total += len(section)

    return "\n\n".join(parts)


# ════════════════════════════════════════════════════════════════
# 任务3：紫微结论注入
# ════════════════════════════════════════════════════════════════

def format_ziwei_for_prompt(chart: dict) -> str:
    """
    从紫微排盘结果提取关键宫位信息，格式化为 prompt 文本。
    只提取：命宫主星+四化、身宫、五行局、事业/财帛/夫妻宫主星。
    不暴露"紫微斗数"术语，由 DeepSeek 消化后用白话融入解读。
    """
    if not chart:
        return ""

    try:
        palaces    = chart.get("palaces", {})
        ming_gong  = chart.get("ming_gong", {})
        shen_gong  = chart.get("shen_gong", {})
        ju_info    = chart.get("wu_xing_ju", {})
        sihua      = chart.get("sihua", {})

        def _stars_in(palace_name: str) -> str:
            for p in palaces.values():
                if p.get("name") == palace_name:
                    stars = p.get("major_stars", [])
                    return "、".join(stars) if stars else "无主星"
            return "未知"

        def _sihua_in(palace_name: str) -> str:
            """从宫位自身的 sihua 字段读取四化，格式 {star: type_str}"""
            hits = []
            for p in palaces.values():
                if p.get("name") == palace_name:
                    for star, stype in p.get("sihua", {}).items():
                        hits.append(f"{star}{stype}")
            return "、".join(hits) if hits else ""

        ming_branch    = ming_gong.get("branch", "")
        ming_stars     = _stars_in("命宫")
        ming_sihua_txt = _sihua_in("命宫")
        shen_branch    = shen_gong.get("branch", "")
        shen_palace    = ""
        for p in palaces.values():
            if p.get("branch") == shen_branch:
                shen_palace = p.get("name", "")
                break

        ju_name = ju_info.get("ju_name", "")

        career_stars   = _stars_in("官禄")
        wealth_stars   = _stars_in("财帛")
        marriage_stars = _stars_in("夫妻")

        lines = []
        ming_txt = f"命宫在{ming_branch}宫，主星{ming_stars}"
        if ming_sihua_txt:
            ming_txt += f"（{ming_sihua_txt}）"
        lines.append(ming_txt)

        if shen_branch:
            lines.append(f"身宫在{shen_branch}宫，与{shen_palace}同宫")

        if ju_name:
            lines.append(f"五行局为{ju_name}")

        if career_stars:
            lines.append(f"事业宫主星为{career_stars}")
        if wealth_stars:
            lines.append(f"财帛宫主星为{wealth_stars}")
        if marriage_stars:
            lines.append(f"夫妻宫主星为{marriage_stars}")

        return "命盘补充信息：" + "，".join(lines) + "。"

    except Exception as exc:
        logger.warning("format_ziwei_for_prompt 失败: %s", exc)
        return ""


# ════════════════════════════════════════════════════════════════
# 任务4：皇极时代背景
# ════════════════════════════════════════════════════════════════

def get_era_context(birth_year: int) -> str:
    """
    获取出生年份的皇极经世时代背景描述。
    使用 huangji_calculator.get_era_description()；
    若不可用则用 calculate_huangji() 手动拼接。
    """
    mod = _get_huangji()
    if mod is None:
        return ""

    try:
        if hasattr(mod, "get_era_description"):
            return mod.get_era_description(birth_year)

        if hasattr(mod, "calculate_huangji"):
            r    = mod.calculate_huangji(birth_year)
            pos  = r["position"]
            hui  = r["hui_theme"]
            ctx  = r["context"]
            return (
                f"时代背景：出生于{pos['hui_name']}{hui['gua_name']}卦当令期"
                f"（{hui['yang_count']}阳{hui['yin_count']}阴，{hui['theme']}）。"
                f"{hui['description']}。"
                f"（当前所处历史阶段约{ctx['shi_start_year']}—{ctx['shi_end_year']}年，"
                f"{hui['trend']}）"
            )
    except Exception as exc:
        logger.warning("get_era_context 失败 year=%s: %s", birth_year, exc)

    return ""


# ════════════════════════════════════════════════════════════════
# 任务2：千隆v1.2 prompt 加载
# ════════════════════════════════════════════════════════════════

_QIANLONG_PROMPT_CACHE: dict | None = None


def _load_qianlong_prompt() -> dict:
    """
    读取 prompts/qianlong_reading_prompt.json，返回 dict。
    失败时返回空 dict（调用方有 fallback）。
    """
    global _QIANLONG_PROMPT_CACHE
    if _QIANLONG_PROMPT_CACHE is not None:
        return _QIANLONG_PROMPT_CACHE

    fpath = _PROMPTS_DIR / "qianlong_reading_prompt.json"
    try:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        _QIANLONG_PROMPT_CACHE = data
        return data
    except Exception as exc:
        logger.warning("读取千隆prompt失败: %s", exc)
        return {}


_FALLBACK_SYSTEM = (
    "你是一位资深命理顾问，风格温暖有洞察力，像老朋友聊天。"
    "根据八字命盘做800-1500字的自然语言解读，"
    "先描述性格特征（40%），再点出过去困境（15%），"
    "视角转换（5%），给出方向感（25%），最后给落地建议（15%）。"
    "全程白话，不出现命理术语。"
    "最后加：以上分析基于命理学理论，仅供参考，人生的精彩永远取决于你自己的选择。"
)


def _build_system_prompt(knowledge_ctx: str) -> str:
    """
    拼接完整 system prompt：知识库 + 千隆v1.2 system_prompt。
    加入紫微信息使用规则（不暴露紫微术语）。
    """
    qianlong = _load_qianlong_prompt()
    base_prompt = qianlong.get("system_prompt") or _FALLBACK_SYSTEM

    # 在重要原则末尾注入紫微使用规则
    ziwei_rule = (
        "\n如果收到命盘补充信息，将其作为分析依据但不要在解读中提及相关术语，"
        "用白话自然融入解读即可。例如主星天机化权 → 用「你内在有一股很强的策略性思维」表达。"
    )
    base_prompt = base_prompt.rstrip() + ziwei_rule

    if knowledge_ctx:
        return f"【知识库参考】\n{knowledge_ctx}\n\n---\n\n{base_prompt}"
    return base_prompt


def _build_user_prompt(chart_data: dict, ziwei_ctx: str, era_ctx: str,
                       user_question: str, user_background: str) -> str:
    """
    用排盘数据填充千隆 user_prompt_template，
    并在末尾追加紫微补充和时代背景。
    """
    qianlong = _load_qianlong_prompt()
    template = qianlong.get("user_prompt_template", "")

    # 提取排盘字段
    inp = chart_data.get("input", {})
    fp  = chart_data.get("four_pillars", {})
    wa  = chart_data.get("wuxing_analysis", {})
    ss  = chart_data.get("shishen_per_pillar", {})

    def _pillar(key: str) -> str:
        p = fp.get(key, {})
        return p.get("heavenly_stem", "?") + p.get("earthly_branch", "?")

    gender            = inp.get("gender", "")
    year_pillar       = _pillar("year")
    month_pillar      = _pillar("month")
    day_pillar        = _pillar("day")
    hour_pillar       = _pillar("hour")
    day_master        = wa.get("day_master", "")
    day_master_str    = wa.get("day_master_strength", "")

    # 五行分布（优先用计数，fallback用分数）
    scores = wa.get("wuxing_scores", {}) or {}
    pcts   = wa.get("wuxing_percentages", {}) or {}
    def _wx(k_zh: str, k_en: str) -> str:
        v = scores.get(k_zh) if k_zh in scores else scores.get(k_en)
        if v is None:
            return "?"
        p = pcts.get(k_zh) if k_zh in pcts else (pcts.get(k_en) or 0)
        return f"{v:.0f}({p:.0f}%)"

    wood  = _wx("木", "wood")
    fire  = _wx("火", "fire")
    earth = _wx("土", "earth")
    metal = _wx("金", "metal")
    water = _wx("水", "water")

    # 十神摘要
    ten_gods_parts = []
    for col in ["year", "month", "day", "hour"]:
        god = ss.get(col, "")
        if god:
            ten_gods_parts.append(f"{'年月日时'[['year','month','day','hour'].index(col)]}干{god}")
    ten_gods_summary = "  ".join(ten_gods_parts) if ten_gods_parts else "（无十神数据）"

    if template:
        try:
            user_txt = template.format(
                gender=gender,
                year_pillar=year_pillar,
                month_pillar=month_pillar,
                day_pillar=day_pillar,
                hour_pillar=hour_pillar,
                day_master=day_master,
                day_master_strength=day_master_str,
                wood=wood,
                fire=fire,
                earth=earth,
                metal=metal,
                water=water,
                ten_gods_summary=ten_gods_summary,
                user_question=user_question or "（未提供）",
                user_background=user_background or "（未提供）",
            )
        except KeyError:
            # 模板有未知占位符时降级
            user_txt = (
                f"请为以下命主做一份个人解读：\n\n"
                f"性别：{gender}\n"
                f"四柱：{year_pillar} {month_pillar} {day_pillar} {hour_pillar}\n"
                f"日主：{day_master}，日主强弱：{day_master_str}\n"
                f"五行分布：木{wood} 火{fire} 土{earth} 金{metal} 水{water}\n"
                f"十神分布：{ten_gods_summary}"
            )
    else:
        user_txt = (
            f"请为以下命主做一份个人解读：\n\n"
            f"性别：{gender}\n"
            f"四柱：{year_pillar} {month_pillar} {day_pillar} {hour_pillar}\n"
            f"日主：{day_master}，日主强弱：{day_master_str}\n"
            f"五行分布：木{wood} 火{fire} 土{earth} 金{metal} 水{water}\n"
            f"十神分布：{ten_gods_summary}"
        )

    # 追加紫微补充
    if ziwei_ctx:
        user_txt += (
            "\n\n补充参考（仅供解读时参考，不要在解读中提及相关术语）：\n"
            + ziwei_ctx
        )

    # 追加时代背景
    if era_ctx:
        user_txt += (
            "\n\n时代背景参考（自然融入解读，不要提及体系名称）：\n"
            + era_ctx
        )

    return user_txt


# ── DeepSeek 调用（不依赖 llm_client.py）──────────────────────

def _call_deepseek(api_key: str, system: str, user: str,
                   max_tokens: int = 2000, temperature: float = 0.75) -> str:
    """使用 urllib.request 调用 DeepSeek，返回文本内容。"""
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        # 千隆解读输出自然语言，不要 json_object 模式
    }
    req = urllib.request.Request(
        DEEPSEEK_API_URL,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"]


# ════════════════════════════════════════════════════════════════
# 主函数：千隆全管线
# ════════════════════════════════════════════════════════════════

def generate_qianlong_reading(
    chart_data: dict[str, Any],
    user_question: str = "",
    user_background: str = "",
    client_ip: str = "unknown",
    knowledge_dir: str | Path | None = None,
) -> dict[str, Any]:
    """
    千隆v1.2全管线：
      1. bazi数据已在 chart_data 中
      2. ziwei_calculator 排盘（有时辰时）
      3. huangji_calculator 时代背景
      4. load_knowledge_base 热加载
      5. 读取千隆v1.2 prompt
      6. 拼接 system + user → DeepSeek → 自然语言解读

    返回 dict:
      {
        "reading":      str,    # 解读正文
        "ziwei_used":   bool,
        "era_used":     bool,
        "knowledge_len": int,
        "_meta": {...}
      }
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return {
            "reading": "（DEEPSEEK_API_KEY 未配置，无法生成解读）",
            "error": "no_api_key",
        }

    start = time.perf_counter()
    inp = chart_data.get("input", {})
    birth_year  = inp.get("birth_year")
    birth_month = inp.get("birth_month")
    birth_day   = inp.get("birth_day")
    birth_hour  = inp.get("birth_hour")   # 可能为 None
    gender      = inp.get("gender", "男")

    # ── Step 2: 紫微排盘 ──
    ziwei_ctx  = ""
    ziwei_used = False
    if birth_hour is not None and birth_year and birth_month and birth_day:
        ziwei_mod = _get_ziwei()
        if ziwei_mod and hasattr(ziwei_mod, "build_ziwei_chart"):
            try:
                hour_float = float(birth_hour)
                sex = "男" if str(gender).upper() in {"男", "M", "MALE"} else "女"
                ziwei_chart = ziwei_mod.build_ziwei_chart(
                    int(birth_year), int(birth_month), int(birth_day),
                    hour_float, sex,
                )
                ziwei_ctx  = format_ziwei_for_prompt(ziwei_chart)
                ziwei_used = bool(ziwei_ctx)
            except Exception as exc:
                logger.warning("紫微排盘失败: %s", exc)

    # ── Step 3: 皇极时代背景 ──
    era_ctx  = ""
    era_used = False
    if birth_year:
        try:
            era_ctx  = get_era_context(int(birth_year))
            era_used = bool(era_ctx)
        except Exception as exc:
            logger.warning("皇极时代背景失败: %s", exc)

    # ── Step 4: 知识库热加载 ──
    knowledge_ctx = load_knowledge_base(knowledge_dir)

    # ── Step 5+6: 拼接 prompt → DeepSeek ──
    system_prompt = _build_system_prompt(knowledge_ctx)
    user_prompt   = _build_user_prompt(
        chart_data, ziwei_ctx, era_ctx, user_question, user_background
    )

    try:
        reading_text = _call_deepseek(api_key, system_prompt, user_prompt,
                                      max_tokens=2200, temperature=0.75)
    except Exception as exc:
        logger.error("DeepSeek 调用失败: %s", exc)
        return {
            "reading": f"（解读生成失败：{exc}）",
            "error":   str(exc),
        }

    elapsed = time.perf_counter() - start
    logger.info(
        "generate_qianlong_reading 完成: %.1fs ziwei=%s era=%s kb=%d chars",
        elapsed, ziwei_used, era_used, len(knowledge_ctx),
    )

    return {
        "reading":       reading_text,
        "ziwei_used":    ziwei_used,
        "era_used":      era_used,
        "knowledge_len": len(knowledge_ctx),
        "_meta": {
            "model":      DEEPSEEK_MODEL,
            "elapsed_ms": round(elapsed * 1000),
            "ziwei_ctx_len":    len(ziwei_ctx),
            "era_ctx_len":      len(era_ctx),
            "system_prompt_len": len(system_prompt),
            "user_prompt_len":   len(user_prompt),
        },
    }


# ════════════════════════════════════════════════════════════════
# 轨道A（原有代码，完整保留，api.py 兼容性）
# ════════════════════════════════════════════════════════════════

STYLE_GUIDE = """
STYLE RULES:
- Tone: Warm but not flattering. Like a high-level coach, not a fortune teller.
- Use pattern language, not fate language: 'tendency', 'often', 'may', 'can', 'in some contexts'
- Structure every insight as: Function (what it protects) -> Cost (when it's excessive) -> Practice (one actionable move)
- NEVER use: 'destined to', 'you will inevitably', 'doomed', 'cursed', 'fated to suffer'
- NEVER predict: health/lifespan, divorce, betrayal, loneliness as certainties
- For negative traits: reframe using cognitive reappraisal - acknowledge the function, name the cost, offer a practice
- Relationship language: use attachment theory (secure/anxious/avoidant/fearful-avoidant), not 'compatible/incompatible'
- This is an interpretive framework, not scientific measurement. Always position as self-reflection tool.
""".strip()


TEN_GOD_ARCHETYPES = {
    "比肩": {
        "en": "The Mirror",
        "archetype": "Self-consistency, agency, equality, boundaries, resilience",
        "jung_primary": "Warrior/Hero",
        "jung_secondary": "Orphan/Everyman",
        "attachment": "dismissing-avoidant",
        "shadow": "Projects vulnerability onto others; suppresses dependency needs until delayed emotional eruption",
        "growth": "Liberate 'I need help' from shame, turning it into a speakable need",
        "narrative_template": "Your chart highlights a strong drive toward self-direction and peer-level equality. When you have agency, you're calm and effective; when control feels unclear, frustration rises fast. Growth comes from negotiating roles and boundaries early - before resentment turns into sudden shutdown.",
    },
    "劫财": {
        "en": "The Rival",
        "archetype": "Competition, alliance, risk appetite, rapid action, group dynamics",
        "jung_primary": "Rebel/Outlaw",
        "jung_secondary": "Warrior/Hero",
        "attachment": "fearful-avoidant",
        "shadow": "Core fear: 'I don't deserve to be chosen steadily, so I must grab.' May oscillate between craving alliance and fearing entrapment",
        "growth": "Upgrade 'grabbing' into 'negotiating': name desires clearly, write down agreements, establish boundaries explicitly",
        "narrative_template": "The Rival energy in your chart indicates a dynamic tension between alliance and competition. You thrive in high-stakes environments where quick resource allocation matters. The mature expression is breakthrough entrepreneurship; the shadow is zero-sum impulsivity. Your growth edge: turning 'I must grab' into 'I can negotiate.'",
    },
    "食神": {
        "en": "The Artist",
        "archetype": "Nourishment, positive affect, creativity, rhythm, tolerance",
        "jung_primary": "Jester/Fool",
        "jung_secondary": "Creator",
        "attachment": "secure (when developmental environment supports)",
        "shadow": "Uses comfort to numb discomfort; suppresses conflict, ambition, and anger beneath a pleasant surface",
        "growth": "Stop treating contradiction as the enemy of comfort - treat it as nutrition that needs digesting",
        "narrative_template": "The Artist archetype flows through your chart as a natural creative and restorative impulse. You process life by making it livable and pleasurable. At your best, you're a steady source of recovery and aesthetic expression. Under stress, you may use 'keeping things nice' to avoid depth. Growth means letting conflict in - not as a threat, but as material.",
    },
    "伤官": {
        "en": "The Rebel",
        "archetype": "Expression drive, innovation, critical thinking, anti-authority, differentiation",
        "jung_primary": "Rebel/Outlaw",
        "jung_secondary": "Creator/Sage",
        "attachment": "dismissing-avoidant or fearful-avoidant",
        "shadow": "'I fear being denied, so I deny you first.' May use critique as armor against vulnerability",
        "growth": "Allow yourself to be influenced, seen, and discussed - without equating it with being destroyed",
        "narrative_template": "The Rebel energy points to an innovative mind that questions convention. This force drives breakthrough thinking but may create tension with authority when unexamined. Your real challenge isn't being 'too sharp' - it's staying connected while being sharp. Try splitting critique into two sentences: one for facts, one for what you need.",
    },
    "偏财": {
        "en": "The Adventurer",
        "archetype": "Opportunity sense, resource integration, outward expansion, flexible exchange, results orientation",
        "jung_primary": "Explorer",
        "jung_secondary": "Magician",
        "attachment": "avoidant tendency",
        "shadow": "Instrumentalizes relationships; substitutes value exchange for emotional investment",
        "growth": "Practice saying 'I need you' - not just 'here's what I can offer you'",
        "narrative_template": "The Adventurer pattern suggests comfort with risk and an instinct for spotting opportunity. You excel at making resources flow and connecting disparate worlds. The stabilizer is trust: when you shift from 'trading' to 'investing in relationships,' your results compound instead of cycling.",
    },
    "正财": {
        "en": "The Builder",
        "archetype": "Delayed gratification, reliability, risk management, responsibility, steady state",
        "jung_primary": "Ruler",
        "jung_secondary": "Caregiver",
        "attachment": "secure (may downgrade emotional expression to 'keeping life running')",
        "shadow": "'I'm only lovable when I'm useful.' May tie self-worth entirely to productivity and provision",
        "growth": "Release self-worth from performance - practice non-transactional intimacy and acceptance",
        "narrative_template": "The Builder archetype indicates a psychological need for tangible results and steady accumulation. You create stability and reliability wherever you go. The shadow emerges when security becomes rigidity, or when 'providing' replaces 'connecting.' Growth means letting yourself be valued for who you are, not just what you deliver.",
    },
    "七杀": {
        "en": "The Transformer",
        "archetype": "Threat assessment, decisiveness, action aggression, boundary defense, pressure capacity",
        "jung_primary": "Warrior/Hero",
        "jung_secondary": "Ruler",
        "attachment": "fearful-avoidant",
        "shadow": "'Vulnerability = danger.' Under pressure, may substitute control for safety in intimate relationships",
        "growth": "Allow yourself to lower armor in reliable relationships - upgrade 'protection' from control to collaboration",
        "narrative_template": "The Transformer is perhaps the most intense archetype in your chart. It carries a deep capacity for pressure, decisiveness, and boundary defense. At its best, it forges resilience and strategic power. The shadow appears when intensity becomes control, or when every relationship feels like a battlefield. Growth means finding people safe enough to disarm with.",
    },
    "正官": {
        "en": "The Guardian",
        "archetype": "Responsibility, norms, moral sense, delayed gratification, predictability",
        "jung_primary": "Ruler",
        "jung_secondary": "Sage",
        "attachment": "preoccupied or secure",
        "shadow": "'I don't deserve to exist unless I'm perfect.' May internalize rules as self-punishment rather than self-support",
        "growth": "Transform rules from self-punishment into self-support - practice the same humanizing treatment toward yourself",
        "narrative_template": "The Guardian shapes your relationship with rules, structure, and social responsibility. You naturally gravitate toward order and duty-based leadership. The shadow shows up when standards turn inward and become self-punishment. Reframe: structure exists to support your freedom, not to shame you.",
    },
    "偏印": {
        "en": "The Mystic",
        "archetype": "Insight, detachment, symbolic thinking, cross-domain learning, defensive intelligence",
        "jung_primary": "Magician",
        "jung_secondary": "Sage",
        "attachment": "avoidant tendency",
        "shadow": "Substitutes understanding for feeling; translates intimacy needs into analysis and fear into suspicion",
        "growth": "Allow yourself to not-know; allow yourself to need people - without first converting it into a theory",
        "narrative_template": "The Mystic archetype suggests an unconventional inner life - drawn to hidden knowledge, unorthodox ideas, and intuitive leaps. You process the world through depth and meaning. Under stress, you may retreat into your mind. Integration means translation - letting others access your inner model in simple, human language.",
    },
    "正印": {
        "en": "The Nurturer",
        "archetype": "Safety, learning absorption, inner nurturing, meaning-belonging, stability",
        "jung_primary": "Caregiver",
        "jung_secondary": "Sage",
        "attachment": "preoccupied or secure",
        "shadow": "'I must be taken care of to feel safe.' May slide into passivity and dependency",
        "growth": "Hold 'asking for help' and 'taking responsibility' simultaneously - maturity is self-nourishment, not eternal external feeding",
        "narrative_template": "The Nurturer presence in your chart points to a deep well of wisdom and protective instinct. You learn through absorption and reflection, often becoming the quiet anchor others depend on. Growth means becoming your own safe base - not waiting for the world to provide one.",
    },
}


DAY_MASTER_PROFILES = {
    "甲": {
        "en": "The Pioneer",
        "narrative_zh": "你更像「启动者」：看到方向就会想先把路开出来。你对成长、推进与开疆拓土的敏感度很高。在高质量状态下，你能把愿景变成可执行的第一步；在压力状态下，你可能会把「推进」当作安全感来源，变得急、硬、对阻力不耐烦。你的练习不在于更用力，而在于学会让「推进」与「倾听/校准」并存。",
        "narrative_en": "You're a natural starter - when you see a direction, you want to clear the path first. At your best, you turn vision into actionable first steps. Under stress, you may push too hard and lose patience with resistance. Your growth edge: letting momentum coexist with listening and recalibration.",
    },
    "乙": {
        "en": "The Diplomat",
        "narrative_zh": "你更像「生长型适配者」：擅长顺势、渗透、缠绕式成长。你不一定用最强硬的方式达成目标，但很会在复杂系统里找到缝隙。高质量的乙是柔韧、审美在线、关系敏感；压力下可能变成过度迁就或犹疑不决。你的成长方向是：保留温柔，但把边界说清楚。",
        "narrative_en": "You're an adaptive grower - skilled at finding gaps in complex systems and working through them with flexibility rather than force. At your best, you're resilient, aesthetically attuned, and relationally sensitive. Under stress, you may over-accommodate. Growth means keeping your gentleness while making boundaries clear.",
    },
    "丙": {
        "en": "The Luminary",
        "narrative_zh": "你更像「照亮者」：自带外向表达与感染力，想法一旦点燃就会自然外化。高质量的丙是坦率、热情、带动连接；低质量时可能因为过度在意热度而失去耐心。你的练习是：让热情变成可持续燃料, 会收火、会复盘。",
        "narrative_en": "You're a natural illuminator - expressive, warm, and energizing. Ideas ignite and radiate outward. Under stress, enthusiasm may become impatience or impulsive commitment. Growth means turning passion into sustainable fuel: knowing when to dial down and reflect.",
    },
    "丁": {
        "en": "The Alchemist",
        "narrative_zh": "你更像「内在火种」：不一定外放，但有稳定的审美与意义感。你对细微情绪与氛围更敏感，擅长用含蓄的方式影响他人。压力下可能变成把情绪憋在心里、用冷处理保护自己。你的成长方向是：把感受翻译为对方能听懂的话。",
        "narrative_en": "You're an inner flame - not necessarily loud, but carrying stable aesthetic sense and meaning. You're sensitive to subtle emotions. Under stress, you may internalize and withdraw. Growth means translating feelings into language others can receive.",
    },
    "戊": {
        "en": "The Mountain",
        "narrative_zh": "你更像「承重结构」：习惯先把系统稳住，再谈扩张。高质量的戊是可靠、抗压、能扛事；压力下可能变成过度控制或固执。你的练习是：在稳态里给变化留空间，允许小范围试错。",
        "narrative_en": "You're a load-bearing structure - stabilize first, expand later. At your best, you're reliable, pressure-resistant, and dependable. Under stress, stability may harden into control. Growth means leaving room for change within your steady framework.",
    },
    "己": {
        "en": "The Garden",
        "narrative_zh": "你更像「滋养型土壤」：擅长维护关系与日常运转，让人感觉被照顾。压力下可能把「照顾」变成讨好或牺牲。你的成长方向是：照顾别人之前先照顾边界；当你说「不」，关系反而更真实。",
        "narrative_en": "You're nurturing soil - skilled at maintaining relationships and daily operations. Under stress, caring may become people-pleasing or self-sacrifice. Growth means setting boundaries before giving: when you say 'no,' relationships become more authentic.",
    },
    "庚": {
        "en": "The Warrior",
        "narrative_zh": "你更像「切割者与执行者」：擅长快速下判断、立标准。高质量的庚是果断、公正、行动到位；压力下可能变得锋利、情感表达粗糙。你的练习是：保留标准，但把「刀」变成「手术刀」 - 对事精准、对人保留余地。",
        "narrative_en": "You're a cutter and executor - quick to judge, set standards, and act. At your best, decisive and fair. Under stress, sharpness may become bluntness. Growth means keeping your standards while turning the blade into a scalpel: precise on issues, generous with people.",
    },
    "辛": {
        "en": "The Jeweler",
        "narrative_zh": "你更像「精炼者」：追求质感、秩序与边界美学。压力下可能陷入完美主义与挑剔。你的成长方向是：允许「足够好」先落地，再用精炼能力迭代升级。",
        "narrative_en": "You're a refiner - pursuing texture, order, and aesthetic precision. Under stress, refinement may become perfectionism and criticism. Growth means letting 'good enough' land first, then using your refining ability to iterate upward.",
    },
    "壬": {
        "en": "The Ocean",
        "narrative_zh": "你更像「江河式思维」：信息量大、联想强、适应快。压力下可能因信息过载而焦虑，或因不喜欢被限制而难以承诺。你的练习是：把流动性变成选择 - 给自己设几个真正重要的锚点。",
        "narrative_en": "You're a river mind - high-volume, associative, adaptive. Under stress, information overload may cause anxiety, or resistance to commitment. Growth means converting flow into choice: set a few anchors that truly matter.",
    },
    "癸": {
        "en": "The Rain",
        "narrative_zh": "你更像「深水感受者」：敏感、内省、对隐性情绪与风险信号很快捕捉。压力下可能走向退缩或自我消耗。你的成长方向是：把敏感从「负担」升级为「工具」 - 用清晰表达与边界来保护你的深度。",
        "narrative_en": "You're a deep-water sensor - sensitive, introspective, quick to pick up hidden emotional signals. Under stress, you may withdraw or self-deplete. Growth means upgrading sensitivity from burden to instrument: protect your depth with clear expression and boundaries.",
    },
}


class AIInterpreter:
    def _build_prompt(self, chart_data: dict[str, Any], lang: str = "both") -> str:
        day_master   = chart_data.get("day_master", "未知")
        dominant_gods = ", ".join(self._extract_dominant_gods(chart_data))
        return (
            "You are an interpretive psychology-oriented BaZi assistant.\n"
            "Frame everything as reflective tendencies, not certainties.\n\n"
            f"{STYLE_GUIDE}\n\n"
            f"OUTPUT LANGUAGE: {lang}\n"
            f"DAY MASTER: {day_master}\n"
            f"DOMINANT TEN GODS: {dominant_gods or 'None provided'}\n"
            f"CHART PAYLOAD: {chart_data}\n"
        )

    def _extract_dominant_gods(self, chart_data: dict[str, Any]) -> list[str]:
        gods = chart_data.get("dominant_gods")
        if isinstance(gods, list):
            return [god for god in gods if god in TEN_GOD_ARCHETYPES]

        ten_gods = chart_data.get("ten_gods")
        if isinstance(ten_gods, dict):
            ranked = sorted(
                ((name, score) for name, score in ten_gods.items() if name in TEN_GOD_ARCHETYPES),
                key=lambda item: item[1],
                reverse=True,
            )
            return [name for name, _score in ranked[:3]]
        return []

    def _build_day_master_section(self, day_master: str, lang: str) -> dict[str, str]:
        profile = DAY_MASTER_PROFILES.get(day_master)
        if not profile:
            return {"title": day_master, "narrative": ""}

        if lang == "zh":
            return {"title": day_master, "narrative": profile["narrative_zh"]}
        return {"title": profile["en"], "narrative": profile["narrative_en"]}

    def _build_god_section(self, god: str, lang: str) -> dict[str, str]:
        data = TEN_GOD_ARCHETYPES[god]
        if lang == "zh":
            narrative = (
                f"{god}更像一种自我保护模式：它通常在保护你对「{data['archetype']}」的需要。"
                f"当这股力量过强时，代价常表现为：{data['shadow']}。"
                f"更成熟的练习是：{data['growth']}。"
            )
            return {"name": god, "narrative": narrative}

        return {
            "name": f"{god} / {data['en']}",
            "narrative": data["narrative_template"],
        }

    def _compose_text(self, day_master: dict[str, str], gods: list[dict[str, str]], lang: str) -> str:
        if lang == "zh":
            lines = [f"日主画像：{day_master['narrative']}", "主导十神："]
        else:
            lines = [f"Day Master: {day_master['narrative']}", "Dominant Ten Gods:"]

        for item in gods:
            lines.append(f"- {item['name']}: {item['narrative']}")
        return "\n".join(lines)

    def _generate_mock_interpretation(self, chart_data: dict[str, Any], lang: str = "en") -> dict[str, Any]:
        day_master_value = chart_data.get("day_master", "甲")
        dominant_gods    = self._extract_dominant_gods(chart_data) or ["比肩", "正印"]

        if lang == "both":
            zh_day_master = self._build_day_master_section(day_master_value, "zh")
            en_day_master = self._build_day_master_section(day_master_value, "en")
            zh_gods = [self._build_god_section(god, "zh") for god in dominant_gods]
            en_gods = [self._build_god_section(god, "en") for god in dominant_gods]
            return {
                "lang": "both",
                "day_master":   {"zh": zh_day_master, "en": en_day_master},
                "dominant_gods": {"zh": zh_gods, "en": en_gods},
                "narrative": {
                    "zh": self._compose_text(zh_day_master, zh_gods, "zh"),
                    "en": self._compose_text(en_day_master, en_gods, "en"),
                },
            }

        resolved_lang = "zh" if lang == "zh" else "en"
        day_master = self._build_day_master_section(day_master_value, resolved_lang)
        gods = [self._build_god_section(god, resolved_lang) for god in dominant_gods]
        return {
            "lang":         resolved_lang,
            "day_master":   day_master,
            "dominant_gods": gods,
            "narrative":    self._compose_text(day_master, gods, resolved_lang),
        }


def post_interpret(payload: dict[str, Any]) -> dict[str, Any]:
    interpreter = AIInterpreter()
    lang = payload.get("lang", "both")
    if lang not in {"en", "zh", "both"}:
        lang = "both"
    return interpreter._generate_mock_interpretation(payload, lang=lang)


def get_interpret_archetypes() -> dict[str, dict[str, str]]:
    return TEN_GOD_ARCHETYPES
