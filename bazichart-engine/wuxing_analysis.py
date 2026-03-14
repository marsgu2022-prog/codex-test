from __future__ import annotations

from typing import Any


STEM_WUXING = {
    "甲": "木",
    "乙": "木",
    "丙": "火",
    "丁": "火",
    "戊": "土",
    "己": "土",
    "庚": "金",
    "辛": "金",
    "壬": "水",
    "癸": "水",
}
BRANCH_HIDDEN_STEMS = {
    "子": [("癸", 0.6)],
    "丑": [("己", 0.6), ("辛", 0.3), ("癸", 0.1)],
    "寅": [("甲", 0.6), ("丙", 0.3), ("戊", 0.1)],
    "卯": [("乙", 0.6)],
    "辰": [("戊", 0.6), ("乙", 0.3), ("癸", 0.1)],
    "巳": [("丙", 0.6), ("庚", 0.3), ("戊", 0.1)],
    "午": [("丁", 0.6), ("己", 0.4)],
    "未": [("己", 0.6), ("丁", 0.3), ("乙", 0.1)],
    "申": [("庚", 0.6), ("壬", 0.3), ("戊", 0.1)],
    "酉": [("辛", 0.6)],
    "戌": [("戊", 0.6), ("辛", 0.3), ("丁", 0.1)],
    "亥": [("壬", 0.6), ("甲", 0.4)],
}
CONTROL_CYCLE = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}
GENERATE_CYCLE = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}


def _empty_scores() -> dict[str, float]:
    return {"金": 0.0, "木": 0.0, "水": 0.0, "火": 0.0, "土": 0.0}


def _round_scores(scores: dict[str, float]) -> dict[str, float]:
    return {element: round(value, 2) for element, value in scores.items()}


def _day_master_strength(ratio: float) -> str:
    if ratio >= 0.3:
        return "偏强"
    if ratio <= 0.18:
        return "偏弱"
    return "中和"


def _favorable_elements(day_master_element: str, strength: str) -> tuple[list[str], list[str]]:
    generated = GENERATE_CYCLE[day_master_element]
    controlled = CONTROL_CYCLE[day_master_element]
    if strength == "偏强":
        favorable = [controlled, generated]
        unfavorable = [day_master_element, _element_that_generates(day_master_element)]
    elif strength == "偏弱":
        favorable = [day_master_element, _element_that_generates(day_master_element)]
        unfavorable = [controlled, generated]
    else:
        favorable = [generated, controlled]
        unfavorable = [day_master_element]
    return favorable, unfavorable


def _element_that_generates(target: str) -> str:
    for element, generated in GENERATE_CYCLE.items():
        if generated == target:
            return element
    return target


def analyze_wuxing(pillars) -> dict:
    scores = _empty_scores()
    month_branch = pillars["month"]["earthly_branch"]
    day_master = pillars["day"]["heavenly_stem"]
    day_master_element = STEM_WUXING[day_master]

    for pillar_name in ("year", "month", "day", "hour"):
        stem = pillars[pillar_name]["heavenly_stem"]
        branch = pillars[pillar_name]["earthly_branch"]
        scores[STEM_WUXING[stem]] += 1.0
        hidden_stems = BRANCH_HIDDEN_STEMS[branch]
        for index, (hidden_stem, weight) in enumerate(hidden_stems):
            actual_weight = weight
            if pillar_name == "month" and branch == month_branch and index == 0:
                actual_weight += 0.5
            scores[STEM_WUXING[hidden_stem]] += actual_weight

    rounded_scores = _round_scores(scores)
    total_score = sum(rounded_scores.values())
    percentages = {
        element: round((value / total_score) * 100, 2) if total_score else 0.0
        for element, value in rounded_scores.items()
    }
    percentage_total = round(sum(percentages.values()), 2)
    if percentage_total != 100.0 and total_score:
        diff = round(100.0 - percentage_total, 2)
        max_element = max(percentages, key=percentages.get)
        percentages[max_element] = round(percentages[max_element] + diff, 2)

    day_master_ratio = rounded_scores[day_master_element] / total_score if total_score else 0.0
    strength = _day_master_strength(day_master_ratio)
    favorable, unfavorable = _favorable_elements(day_master_element, strength)
    analysis = (
        f"日主{day_master}{day_master_element}五行占比约{round(day_master_ratio * 100, 2)}%，"
        f"整体判断为{strength}，喜{''.join(favorable)}，忌{''.join(unfavorable)}。"
    )

    return {
        "wuxing_scores": rounded_scores,
        "wuxing_percentages": percentages,
        "day_master": day_master,
        "day_master_element": day_master_element,
        "day_master_strength": strength,
        "favorable_elements": favorable,
        "unfavorable_elements": unfavorable,
        "analysis": analysis,
    }
