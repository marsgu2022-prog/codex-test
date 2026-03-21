"""
交叉验证引擎 v1 — Cross Validator

在 DeepSeek 解读之前，用硬逻辑对比八字和紫微结论，输出：
- 每个维度的置信度分数
- 高置信结论列表（两套系统一致）
- 矛盾点列表（两套系统冲突）
- prompt_injection 文本（供 DeepSeek 消费，不含命理术语）

输入：
  bazi_chart  — bazi_calculator.calculate_bazi() 的输出 dict
  ziwei_chart — ziwei_calculator.build_ziwei_chart() 的输出 dict

无紫微数据（无时辰）时返回空报告，不报错。
"""

from __future__ import annotations
from typing import Any

# ── 十神 → 荣格原型映射 ─────────────────────────────────────────
SHISHEN_TO_ARCHETYPE: dict[str, str] = {
    "比肩": "Hero",
    "劫财": "Rebel",
    "食神": "Creator",
    "伤官": "Magician",
    "偏财": "Explorer",
    "正财": "Caregiver",
    "七杀": "Shadow/Warrior",
    "正官": "Ruler",
    "偏印": "Sage",
    "正印": "Innocent",
}

# ── 紫微主星 → 荣格原型映射 ─────────────────────────────────────
STAR_TO_ARCHETYPE: dict[str, str] = {
    "紫微": "Ruler/Self",
    "天机": "Sage",
    "太阳": "Hero",
    "武曲": "Warrior",
    "天同": "Innocent",
    "廉贞": "Lover/Rebel",
    "天府": "Caregiver",
    "太阴": "Anima",
    "贪狼": "Explorer/Lover",
    "巨门": "Shadow",
    "天相": "Everyman",
    "天梁": "Wise Old Man",
    "七杀": "Shadow/Warrior",
    "破军": "Rebel/Magician",
}

# 事业类型分类原型集合
_STRUCTURED_ARCHETYPES = {"Ruler", "Caregiver", "Everyman", "Innocent", "Self"}
_CREATIVE_ARCHETYPES   = {"Creator", "Magician", "Explorer", "Rebel", "Lover"}

# 财运类型主星分类
_STEADY_STARS   = {"天府", "天相", "太阴", "天同"}
_VOLATILE_STARS = {"贪狼", "破军", "七杀", "廉贞"}

# 煞星（用于维度5压力判断）
_SHA_STARS = {"擎羊", "陀罗", "火星", "铃星", "地空", "地劫"}

# 维度权重
_WEIGHTS = {
    "核心人格": 0.40,
    "事业方向": 0.25,
    "财运模式": 0.15,
    "感情模式": 0.10,
    "压力模式": 0.10,
}


# ════════════════════════════════════════════════════════════════
# 辅助函数
# ════════════════════════════════════════════════════════════════

def overlap(archetype_a: str, archetype_b: str) -> bool:
    """判断两个原型字符串是否有交集（支持 'Shadow/Warrior' 复合原型）。"""
    set_a = set(archetype_a.split("/"))
    set_b = set(archetype_b.split("/"))
    return bool(set_a & set_b)


def _all_shishen(bazi: dict) -> list[str]:
    """从 bazi_chart 提取所有十神（含地支藏干），排除'日主'。"""
    tg = bazi.get("ten_gods", {})
    result: list[str] = []
    for key in ("year_stem", "month_stem", "day_stem", "hour_stem"):
        val = tg.get(key, "")
        if val and val != "日主":
            result.append(val)
    for key in ("year_branch", "month_branch", "day_branch", "hour_branch"):
        for val in tg.get(key, []):
            if val and val != "日主":
                result.append(val)
    return result


def _dominant_shishen(bazi: dict) -> str:
    """返回出现次数最多的十神（不含日主）。"""
    from collections import Counter
    gods = _all_shishen(bazi)
    if not gods:
        return "比肩"
    return Counter(gods).most_common(1)[0][0]


def _count_shishen(bazi: dict, targets: list[str]) -> int:
    """统计指定十神在全柱（含地支）中出现的总次数。"""
    return sum(1 for g in _all_shishen(bazi) if g in targets)


def _get_palace_stars(ziwei: dict, palace_name: str) -> list[str]:
    """按宫位名称取主星列表。"""
    for p in ziwei.get("palaces", {}).values():
        if p.get("name") == palace_name:
            return p.get("major_stars", [])
    return []


def _get_palace_aux(ziwei: dict, palace_name: str) -> list[str]:
    """按宫位名称取辅星列表。"""
    for p in ziwei.get("palaces", {}).values():
        if p.get("name") == palace_name:
            return p.get("aux_stars", [])
    return []


def classify_career_type(archetypes: list[str]) -> str:
    """根据原型列表分类事业类型: structured / creative / balanced。"""
    s = sum(1 for a in archetypes for x in a.split("/") if x in _STRUCTURED_ARCHETYPES)
    c = sum(1 for a in archetypes for x in a.split("/") if x in _CREATIVE_ARCHETYPES)
    if s > c:
        return "structured"
    if c > s:
        return "creative"
    return "balanced"


def classify_wealth_type(stars: list[str]) -> str:
    """根据财帛宫主星分类财运类型: steady / volatile / mixed。"""
    s = sum(1 for star in stars if star in _STEADY_STARS)
    v = sum(1 for star in stars if star in _VOLATILE_STARS)
    if s > v:
        return "steady"
    if v > s:
        return "volatile"
    return "mixed"


# ════════════════════════════════════════════════════════════════
# 五个维度的比较函数
# ════════════════════════════════════════════════════════════════

def _compare_personality(bazi: dict, ziwei: dict) -> dict:
    """维度1：核心人格（权重40%）"""
    dominant = _dominant_shishen(bazi)
    bazi_archetype = SHISHEN_TO_ARCHETYPE.get(dominant, "Hero")

    ming_stars = _get_palace_stars(ziwei, "命宫")
    ziwei_archetypes = [STAR_TO_ARCHETYPE[s] for s in ming_stars if s in STAR_TO_ARCHETYPE]

    match = any(overlap(bazi_archetype, za) for za in ziwei_archetypes) if ziwei_archetypes else False
    confidence = 0.9 if match else 0.5

    # 白话描述（不含命理术语）
    archetype_used = bazi_archetype
    desc_map = {
        "Hero":           ("你天生有一股推动事情往前走的能量", "Natural drive to move things forward"),
        "Rebel":          ("你有强烈的突破规则、寻求自由的冲动", "Strong impulse to break rules and seek freedom"),
        "Creator":        ("你的内心有丰富的创造力和表达欲", "Rich creativity and expressive drive"),
        "Magician":       ("你内心有很强的改变现实的冲动", "Strong inner drive to transform reality"),
        "Explorer":       ("你对新机会和未知领域有天然的嗅觉", "Natural instinct for new opportunities and frontiers"),
        "Caregiver":      ("你有很强的照顾和维护他人的本能", "Strong instinct to care for and maintain relationships"),
        "Shadow/Warrior": ("你有很高的压力承受力，善于在逆境中找突破口", "High stress tolerance, skilled at finding breakthroughs"),
        "Ruler":          ("你有很强的秩序感和掌控全局的需求", "Strong sense of order and need to oversee the whole picture"),
        "Sage":           ("你有很强的洞察力和跨领域思考能力", "Sharp insight and cross-domain thinking ability"),
        "Innocent":       ("你有天然的信任感和寻求安全稳定的倾向", "Natural trust and tendency to seek security"),
    }
    desc_zh, desc_en = desc_map.get(archetype_used, ("你有独特的内在驱动力", "Unique inner drive"))

    return {
        "dimension":    "核心人格",
        "weight":       _WEIGHTS["核心人格"],
        "bazi_signal":  f"主导十神: {dominant} → {bazi_archetype}",
        "ziwei_signal": f"命宫主星: {ming_stars} → {ziwei_archetypes}",
        "match":        match,
        "confidence":   confidence,
        "archetype":    archetype_used,
        "description_zh": desc_zh,
        "description_en": desc_en,
    }


def _compare_career(bazi: dict, ziwei: dict) -> dict:
    """维度2：事业方向（权重25%）"""
    guan_sha  = _count_shishen(bazi, ["正官", "七杀"])
    shi_shang = _count_shishen(bazi, ["食神", "伤官"])

    if guan_sha > shi_shang:
        bazi_career = "structured"
    elif shi_shang > guan_sha:
        bazi_career = "creative"
    else:
        bazi_career = "balanced"

    career_stars    = _get_palace_stars(ziwei, "官禄")
    career_archetypes = [STAR_TO_ARCHETYPE[s] for s in career_stars if s in STAR_TO_ARCHETYPE]
    ziwei_career    = classify_career_type(career_archetypes)

    match      = (bazi_career == ziwei_career) or ziwei_career == "balanced"
    confidence = 0.85 if match else 0.5

    career_desc = {
        "structured": ("你更适合有清晰框架和规则的职业环境", "Suited to structured environments with clear frameworks"),
        "creative":   ("你更适合需要独立判断和创新的方向", "Suited to roles requiring independent judgment and innovation"),
        "balanced":   ("你在结构和创意之间有弹性，适应力强", "Flexible between structure and creativity"),
    }
    desc_zh, desc_en = career_desc.get(bazi_career, ("事业方向有独特的个人特质", "Unique career path"))

    return {
        "dimension":    "事业方向",
        "weight":       _WEIGHTS["事业方向"],
        "bazi_signal":  f"官杀{guan_sha}:食伤{shi_shang} → {bazi_career}",
        "ziwei_signal": f"官禄宫: {career_stars} → {ziwei_career}",
        "match":        match,
        "confidence":   confidence,
        "archetype":    bazi_career,
        "description_zh": desc_zh,
        "description_en": desc_en,
    }


def _compare_wealth(bazi: dict, ziwei: dict) -> dict:
    """维度3：财运模式（权重15%）"""
    zheng_cai = _count_shishen(bazi, ["正财"])
    pian_cai  = _count_shishen(bazi, ["偏财"])

    if zheng_cai > pian_cai:
        bazi_wealth = "steady"
    elif pian_cai > zheng_cai:
        bazi_wealth = "volatile"
    else:
        bazi_wealth = "mixed"

    wealth_stars = _get_palace_stars(ziwei, "财帛")
    ziwei_wealth = classify_wealth_type(wealth_stars)

    match      = (bazi_wealth == ziwei_wealth) or ziwei_wealth == "mixed"
    confidence = 0.8 if match else 0.5

    wealth_desc = {
        "steady":   ("你的财运路径偏向稳定积累，不适合过度冒险", "Wealth accumulates steadily; avoid excessive risk-taking"),
        "volatile": ("你的财运路径起伏较大，机会型收益明显", "Volatile wealth path with significant opportunity-based gains"),
        "mixed":    ("你的财运兼具稳健与机会性，节奏感很重要", "Mixed wealth pattern; timing and rhythm are key"),
    }
    desc_zh, desc_en = wealth_desc.get(bazi_wealth, ("财运有独特的个人节奏", "Unique wealth rhythm"))

    return {
        "dimension":    "财运模式",
        "weight":       _WEIGHTS["财运模式"],
        "bazi_signal":  f"正财{zheng_cai}:偏财{pian_cai} → {bazi_wealth}",
        "ziwei_signal": f"财帛宫: {wealth_stars} → {ziwei_wealth}",
        "match":        match,
        "confidence":   confidence,
        "archetype":    bazi_wealth,
        "description_zh": desc_zh,
        "description_en": desc_en,
    }


def _compare_relationship(bazi: dict, ziwei: dict) -> dict:
    """维度4：感情模式（权重10%）
    八字：男看正财偏财，女看正官七杀；紫微：夫妻宫主星原型
    """
    sex = bazi.get("sex", "男")  # 从 bazi_chart 或外部注入

    if sex in ("男", "M", "male"):
        rel_gods  = ["正财", "偏财"]
        zheng_cnt = _count_shishen(bazi, ["正财"])
        pian_cnt  = _count_shishen(bazi, ["偏财"])
        if zheng_cnt > pian_cnt:
            bazi_rel = "stable"    # 稳定型
        elif pian_cnt > zheng_cnt:
            bazi_rel = "adventurous"  # 多变型
        else:
            bazi_rel = "mixed"
    else:
        guan_cnt = _count_shishen(bazi, ["正官"])
        sha_cnt  = _count_shishen(bazi, ["七杀"])
        if guan_cnt > sha_cnt:
            bazi_rel = "stable"
        elif sha_cnt > guan_cnt:
            bazi_rel = "adventurous"
        else:
            bazi_rel = "mixed"

    marriage_stars     = _get_palace_stars(ziwei, "夫妻")
    marriage_archetypes = [STAR_TO_ARCHETYPE[s] for s in marriage_stars if s in STAR_TO_ARCHETYPE]

    # 夫妻宫分类：稳定型 vs 动荡型
    _stable_archetypes = {"Caregiver", "Innocent", "Everyman", "Ruler", "Self"}
    _dynamic_archetypes = {"Rebel", "Explorer", "Shadow", "Warrior", "Lover", "Magician"}
    s_cnt = sum(1 for a in marriage_archetypes for x in a.split("/") if x in _stable_archetypes)
    d_cnt = sum(1 for a in marriage_archetypes for x in a.split("/") if x in _dynamic_archetypes)
    ziwei_rel = "stable" if s_cnt > d_cnt else ("adventurous" if d_cnt > s_cnt else "mixed")

    match      = (bazi_rel == ziwei_rel) or bazi_rel == "mixed" or ziwei_rel == "mixed"
    confidence = 0.8 if match else 0.5

    rel_desc = {
        "stable":      ("你对感情关系有很高的忠诚度和稳定性需求", "High loyalty and need for stability in relationships"),
        "adventurous": ("你的感情模式里有很强的独立性，需要找到节奏匹配的伴侣", "Strong independence in relationships; need rhythm-matched partner"),
        "mixed":       ("你的感情模式兼具稳定与激情，关键在于平衡", "Mixed relationship pattern balancing stability and passion"),
    }
    desc_zh, desc_en = rel_desc.get(bazi_rel, ("感情模式有独特的个人特质", "Unique relationship pattern"))

    return {
        "dimension":    "感情模式",
        "weight":       _WEIGHTS["感情模式"],
        "bazi_signal":  f"关系十神 → {bazi_rel}",
        "ziwei_signal": f"夫妻宫: {marriage_stars} → {ziwei_rel}",
        "match":        match,
        "confidence":   confidence,
        "archetype":    bazi_rel,
        "description_zh": desc_zh,
        "description_en": desc_en,
    }


def _compare_stress(bazi: dict, ziwei: dict) -> dict:
    """维度5：压力模式（权重10%）
    八字：七杀/伤官强度；紫微：命宫有无煞星
    """
    sha_cnt     = _count_shishen(bazi, ["七杀"])
    shang_cnt   = _count_shishen(bazi, ["伤官"])
    stress_total = sha_cnt + shang_cnt

    bazi_stress = "high" if stress_total >= 3 else ("medium" if stress_total >= 1 else "low")

    ming_aux  = _get_palace_aux(ziwei, "命宫")
    sha_in_ming = [s for s in ming_aux if s in _SHA_STARS]
    ziwei_stress = "high" if len(sha_in_ming) >= 2 else ("medium" if sha_in_ming else "low")

    match      = (bazi_stress == ziwei_stress)
    confidence = 0.75 if match else 0.5

    stress_desc = {
        "high":   ("你天生承压能力强，但也更容易在高压环境中消耗自己", "High natural stress tolerance but also higher self-consumption in pressure"),
        "medium": ("你有适度的压力驱动力，挑战能激发你的潜能", "Moderate stress drive; challenges bring out your potential"),
        "low":    ("你在平和的环境里发挥最好，不需要用压力驱动自己", "Best performance in calm environments; no need for pressure-driven motivation"),
    }
    desc_zh, desc_en = stress_desc.get(bazi_stress, ("压力模式有独特的个人特质", "Unique stress pattern"))

    return {
        "dimension":    "压力模式",
        "weight":       _WEIGHTS["压力模式"],
        "bazi_signal":  f"七杀{sha_cnt}+伤官{shang_cnt}=总{stress_total} → {bazi_stress}",
        "ziwei_signal": f"命宫煞星: {sha_in_ming} → {ziwei_stress}",
        "match":        match,
        "confidence":   confidence,
        "archetype":    bazi_stress,
        "description_zh": desc_zh,
        "description_en": desc_en,
    }


# ════════════════════════════════════════════════════════════════
# 主函数
# ════════════════════════════════════════════════════════════════

def cross_validate(bazi_chart: dict, ziwei_chart: dict | None) -> dict[str, Any]:
    """
    交叉验证八字和紫微结论。

    参数:
        bazi_chart:  bazi_calculator.calculate_bazi() 输出
        ziwei_chart: ziwei_calculator.build_ziwei_chart() 输出，无时辰时传 None

    返回: 交叉验证报告 dict，含 prompt_injection 供 DeepSeek 消费。
    """
    if not ziwei_chart:
        return {
            "overall_confidence":   None,
            "dimensions":           [],
            "high_confidence_traits": [],
            "contradictions":       [],
            "prompt_injection":     "",
        }

    dimensions = [
        _compare_personality(bazi_chart, ziwei_chart),
        _compare_career(bazi_chart, ziwei_chart),
        _compare_wealth(bazi_chart, ziwei_chart),
        _compare_relationship(bazi_chart, ziwei_chart),
        _compare_stress(bazi_chart, ziwei_chart),
    ]

    # 加权平均置信度
    overall = sum(d["confidence"] * d["weight"] for d in dimensions)

    # 高置信结论（两系统一致，confidence >= 0.8）
    high_confidence_traits = [
        d["description_zh"]
        for d in dimensions
        if d["match"] and d["confidence"] >= 0.8
    ]

    # 矛盾点（不一致，给 DeepSeek 措辞建议）
    _cont_templates = {
        "核心人格": "解读时表达为「你有时在不同能量状态间切换，这种内在张力是你独特的地方」",
        "事业方向": "解读时表达为「你在稳定框架和自由创新之间有内在拉扯，找到平衡点是你的成长课题」",
        "财运模式": "解读时表达为「你有稳健的一面，但内心也渴望突破，财运路径不是单线的」",
        "感情模式": "解读时表达为「你的感情需求比较复杂，稳定和新鲜感对你同样重要」",
        "压力模式": "解读时表达为「你的内在承压能力和外在表现出的状态不完全一样，内外有落差」",
    }
    contradictions = [
        {
            "dimension":  d["dimension"],
            "bazi_says":  d["bazi_signal"],
            "ziwei_says": d["ziwei_signal"],
            "suggestion": _cont_templates.get(d["dimension"], "表达时留有余地"),
        }
        for d in dimensions
        if not d["match"]
    ]

    # 生成 prompt_injection（白话，不含命理术语）
    _inject_parts: list[str] = []
    if high_confidence_traits:
        traits_str = "；".join(high_confidence_traits)
        _inject_parts.append(f"以下特质置信度很高，可以直接说得肯定：{traits_str}。")
    if contradictions:
        cont_str = "；".join(
            f"{c['dimension']}方面两种信号有出入，{c['suggestion']}"
            for c in contradictions
        )
        _inject_parts.append(f"以下维度存在矛盾，表达时留余地：{cont_str}。")
    if not _inject_parts:
        _inject_parts.append("各维度信号一致，解读时可以较为肯定地表达各维度特质。")

    prompt_injection = "\n".join(_inject_parts)

    return {
        "overall_confidence":     round(overall, 3),
        "dimensions":             dimensions,
        "high_confidence_traits": high_confidence_traits,
        "contradictions":         contradictions,
        "prompt_injection":       prompt_injection,
    }
