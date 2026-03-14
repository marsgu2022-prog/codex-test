from __future__ import annotations

from typing import Any


TIANGAN_HE = {
    frozenset({"甲", "己"}): "甲己合化土",
    frozenset({"乙", "庚"}): "乙庚合化金",
    frozenset({"丙", "辛"}): "丙辛合化水",
    frozenset({"丁", "壬"}): "丁壬合化木",
    frozenset({"戊", "癸"}): "戊癸合化火",
}
LIUHE = {
    frozenset({"子", "丑"}): "子丑六合",
    frozenset({"寅", "亥"}): "寅亥六合",
    frozenset({"卯", "戌"}): "卯戌六合",
    frozenset({"辰", "酉"}): "辰酉六合",
    frozenset({"巳", "申"}): "巳申六合",
    frozenset({"午", "未"}): "午未六合",
}
CHONG = {
    frozenset({"子", "午"}): "子午相冲",
    frozenset({"丑", "未"}): "丑未相冲",
    frozenset({"寅", "申"}): "寅申相冲",
    frozenset({"卯", "酉"}): "卯酉相冲",
    frozenset({"辰", "戌"}): "辰戌相冲",
    frozenset({"巳", "亥"}): "巳亥相冲",
}
HAI = {
    frozenset({"子", "未"}): "子未相害",
    frozenset({"丑", "午"}): "丑午相害",
    frozenset({"寅", "巳"}): "寅巳相害",
    frozenset({"卯", "辰"}): "卯辰相害",
    frozenset({"申", "亥"}): "申亥相害",
    frozenset({"酉", "戌"}): "酉戌相害",
}
XING = {
    frozenset({"寅", "巳"}): "寅巳相刑",
    frozenset({"巳", "申"}): "巳申相刑",
    frozenset({"寅", "申"}): "寅申相刑",
    frozenset({"丑", "戌"}): "丑戌相刑",
    frozenset({"戌", "未"}): "戌未相刑",
    frozenset({"丑", "未"}): "丑未相刑",
    frozenset({"子"}): "子卯相刑",
    frozenset({"辰"}): "辰辰自刑",
    frozenset({"午"}): "午午自刑",
    frozenset({"酉"}): "酉酉自刑",
    frozenset({"亥"}): "亥亥自刑",
}
SANHE_GROUPS = [
    {"申", "子", "辰"},
    {"亥", "卯", "未"},
    {"寅", "午", "戌"},
    {"巳", "酉", "丑"},
]
LEVELS = [
    (85, "上等婚配"),
    (70, "中上婚配"),
    (55, "中等婚配"),
    (40, "中下婚配"),
    (0, "下等婚配"),
]


def _day_gan_he(male_day_stem: str, female_day_stem: str) -> tuple[bool, str, int]:
    key = frozenset({male_day_stem, female_day_stem})
    detail = TIANGAN_HE.get(key)
    if detail:
        return True, f"{detail}，情投意合，彼此容易互相吸引。", 25
    return False, "日干未成五合，更多依赖后天相处磨合。", 10


def _year_zhi_relation(male_branch: str, female_branch: str) -> tuple[str, str, int]:
    key = frozenset({male_branch, female_branch})
    if key in LIUHE:
        return "六合", f"{LIUHE[key]}，天生缘分较深，容易相互扶持。", 22
    if any({male_branch, female_branch}.issubset(group) for group in SANHE_GROUPS):
        return "三合", "双方年支可入三合局，价值取向较容易形成同频。", 18
    if key in CHONG:
        return "相冲", f"{CHONG[key]}，彼此个性与节奏差异较大。", 6
    if key in XING:
        return "相刑", f"{XING[key]}，相处中容易出现内耗与误解。", 8
    if key in HAI:
        return "相害", f"{HAI[key]}，情感里易有暗耗与隐性摩擦。", 10
    return "平", "年支关系平稳，无明显强合强冲。", 14


def _yongshen_match(male_analysis: dict[str, Any], female_analysis: dict[str, Any]) -> tuple[int, str]:
    male_fav = male_analysis.get("favorable_elements", [])
    female_fav = female_analysis.get("favorable_elements", [])
    male_scores = male_analysis.get("wuxing_scores", {})
    female_scores = female_analysis.get("wuxing_scores", {})

    male_need = male_fav[0] if male_fav else None
    female_need = female_fav[0] if female_fav else None
    male_supported = female_scores.get(male_need, 0) if male_need else 0
    female_supported = male_scores.get(female_need, 0) if female_need else 0
    score = int(min(100, 40 + male_supported * 12 + female_supported * 12))
    detail = (
        f"男方喜{male_need or '未知'}，女方对应五行得分较高；"
        f"女方喜{female_need or '未知'}，男方亦能形成一定补益。"
    )
    return score, detail


def _wuxing_complement(male_analysis: dict[str, Any], female_analysis: dict[str, Any]) -> tuple[int, str]:
    male_scores = male_analysis.get("wuxing_scores", {})
    female_scores = female_analysis.get("wuxing_scores", {})
    low_threshold = 1.2
    high_threshold = 2.0
    complement_pairs = 0
    details = []
    for element in ("金", "木", "水", "火", "土"):
        male_value = male_scores.get(element, 0)
        female_value = female_scores.get(element, 0)
        if male_value < low_threshold and female_value >= high_threshold:
            complement_pairs += 1
            details.append(f"男方{element}偏弱而女方{element}较旺")
        elif female_value < low_threshold and male_value >= high_threshold:
            complement_pairs += 1
            details.append(f"女方{element}偏弱而男方{element}较旺")
    score = min(100, 45 + complement_pairs * 15)
    detail = "；".join(details) if details else "双方五行分布较均衡，互补性中等。"
    return score, detail


def _level(score: int) -> str:
    for threshold, label in LEVELS:
        if score >= threshold:
            return label
    return "下等婚配"


def analyze_hehun(male_pillars, female_pillars, male_analysis=None, female_analysis=None) -> dict:
    male_day_stem = male_pillars["day"]["heavenly_stem"]
    female_day_stem = female_pillars["day"]["heavenly_stem"]
    day_gan_matched, day_gan_detail, day_gan_score = _day_gan_he(male_day_stem, female_day_stem)

    relation, year_zhi_detail, year_zhi_score = _year_zhi_relation(
        male_pillars["year"]["earthly_branch"],
        female_pillars["year"]["earthly_branch"],
    )

    male_analysis = male_analysis or {}
    female_analysis = female_analysis or {}
    yongshen_score, yongshen_detail = _yongshen_match(male_analysis, female_analysis)
    complement_score, complement_detail = _wuxing_complement(male_analysis, female_analysis)

    score = int(round(day_gan_score * 0.3 + year_zhi_score * 1.0 + yongshen_score * 0.25 + complement_score * 0.25))
    score = max(0, min(100, score))
    level = _level(score)
    summary = (
        f"此婚配属{level}，"
        f"{day_gan_detail}"
        f"{year_zhi_detail}"
        f"用神匹配度为{yongshen_score}分，五行互补度为{complement_score}分。"
    )

    return {
        "score": score,
        "level": level,
        "day_gan_he": {"matched": day_gan_matched, "detail": day_gan_detail},
        "year_zhi": {"relation": relation, "detail": year_zhi_detail},
        "yongshen_match": {"score": yongshen_score, "detail": yongshen_detail},
        "wuxing_complement": {"score": complement_score, "detail": complement_detail},
        "summary": summary,
    }
