from __future__ import annotations

from typing import Any


TIANGAN = "甲乙丙丁戊己庚辛壬癸"
DIZHI = "子丑寅卯辰巳午未申酉戌亥"
TIANYI_GUIREN = {
    "甲": {"丑", "未"},
    "戊": {"丑", "未"},
    "庚": {"丑", "未"},
    "乙": {"子", "申"},
    "己": {"子", "申"},
    "丙": {"亥", "酉"},
    "丁": {"亥", "酉"},
    "壬": {"卯", "巳"},
    "癸": {"卯", "巳"},
    "辛": {"寅", "午"},
}
WENCHANG = {
    "甲": {"巳"},
    "乙": {"午"},
    "丙": {"申"},
    "戊": {"申"},
    "丁": {"酉"},
    "己": {"酉"},
    "庚": {"亥"},
    "辛": {"子"},
    "壬": {"寅"},
    "癸": {"卯"},
}
TIANDE_BY_MONTH_BRANCH = {
    "寅": {"丁"},
    "卯": {"申"},
    "辰": {"壬"},
    "巳": {"辛"},
    "午": {"亥"},
    "未": {"甲"},
    "申": {"癸"},
    "酉": {"寅"},
    "戌": {"丙"},
    "亥": {"乙"},
    "子": {"巳"},
    "丑": {"庚"},
}
YUEDE_BY_MONTH_BRANCH = {
    "寅": {"丙"},
    "午": {"丙"},
    "戌": {"丙"},
    "申": {"壬"},
    "子": {"壬"},
    "辰": {"壬"},
    "亥": {"甲"},
    "卯": {"甲"},
    "未": {"甲"},
    "巳": {"庚"},
    "酉": {"庚"},
    "丑": {"庚"},
}
TAIJI_GUIREN = {
    "甲": {"子", "午"},
    "乙": {"子", "午"},
    "丙": {"卯", "酉"},
    "丁": {"卯", "酉"},
    "戊": {"辰", "戌", "丑", "未"},
    "己": {"辰", "戌", "丑", "未"},
    "庚": {"寅", "亥"},
    "辛": {"寅", "亥"},
    "壬": {"巳", "申"},
    "癸": {"巳", "申"},
}
JINYU = {
    "甲": {"辰"},
    "乙": {"巳"},
    "丙": {"未"},
    "戊": {"未"},
    "丁": {"申"},
    "己": {"申"},
    "庚": {"戌"},
    "辛": {"亥"},
    "壬": {"丑"},
    "癸": {"寅"},
}
TIANCHU = {
    "甲": {"巳"},
    "乙": {"午"},
    "丙": {"巳"},
    "丁": {"午"},
    "戊": {"申"},
    "己": {"酉"},
    "庚": {"亥"},
    "辛": {"子"},
    "壬": {"寅"},
    "癸": {"卯"},
}
BRANCH_GROUP_MAP = {
    "申子辰": {
        "驿马": {"寅"},
        "华盖": {"辰"},
        "将星": {"子"},
        "桃花（咸池）": {"酉"},
        "劫煞": {"巳"},
        "亡神": {"亥"},
        "白虎": {"午"},
    },
    "寅午戌": {
        "驿马": {"申"},
        "华盖": {"戌"},
        "将星": {"午"},
        "桃花（咸池）": {"卯"},
        "劫煞": {"亥"},
        "亡神": {"巳"},
        "白虎": {"子"},
    },
    "亥卯未": {
        "驿马": {"巳"},
        "华盖": {"未"},
        "将星": {"卯"},
        "桃花（咸池）": {"子"},
        "劫煞": {"申"},
        "亡神": {"寅"},
        "白虎": {"酉"},
    },
    "巳酉丑": {
        "驿马": {"亥"},
        "华盖": {"丑"},
        "将星": {"酉"},
        "桃花（咸池）": {"午"},
        "劫煞": {"寅"},
        "亡神": {"申"},
        "白虎": {"卯"},
    },
}
GUCHEN_GUASU = {
    "亥子丑": {"孤辰": {"寅"}, "寡宿": {"戌"}},
    "寅卯辰": {"孤辰": {"巳"}, "寡宿": {"丑"}},
    "巳午未": {"孤辰": {"申"}, "寡宿": {"辰"}},
    "申酉戌": {"孤辰": {"亥"}, "寡宿": {"未"}},
}
YANGREN = {
    "甲": {"卯"},
    "乙": {"寅"},
    "丙": {"午"},
    "丁": {"巳"},
    "戊": {"午"},
    "己": {"巳"},
    "庚": {"酉"},
    "辛": {"申"},
    "壬": {"子"},
    "癸": {"亥"},
}
KONGWANG_BY_XUN = [
    {"戌", "亥"},
    {"申", "酉"},
    {"午", "未"},
    {"辰", "巳"},
    {"寅", "卯"},
    {"子", "丑"},
]
DESCRIPTIONS = {
    "天乙贵人": "遇难呈祥，逢凶化吉，一生多得贵人相助。",
    "文昌贵人": "主聪明好学，文笔佳，思维清晰。",
    "天德贵人": "主心地仁厚，常得天助，化解灾厄。",
    "月德贵人": "主有福泽，行事多得助力，遇事易转圜。",
    "驿马": "主奔波变动、迁移旅行，动中求发展。",
    "华盖": "主艺术灵感、宗教玄思，也带孤高气质。",
    "太极贵人": "主悟性高，喜玄学哲思，逢凶多可化解。",
    "金舆": "主福气、名望与物质享受，易得体面之助。",
    "天厨贵人": "主口福、福禄和生活品味，常与饮食之福有关。",
    "将星": "主领导力、执行力与掌控欲，利于掌权任事。",
    "桃花（咸池）": "主人缘、魅力与情感机会，也易惹情事波动。",
    "孤辰寡宿": "主内心孤独、情感疏离，宜注意关系经营。",
    "劫煞": "主突发阻碍、竞争消耗，处事需防意外损失。",
    "亡神": "主心神不宁、计划反复，易有疏漏与虚耗。",
    "羊刃": "主个性刚烈果断，若失衡则易冲动伤人伤己。",
    "空亡": "主事情易落空、反复或延后，象征虚耗不实。",
    "天罗地网": "主牵绊束缚、压力困局，行事宜谨慎避险。",
    "白虎": "主是非伤灾、血光刑伤之象，宜防冲突损伤。",
    "丧门": "主忧伤孝服之气，易遇家庭或情绪层面压力。",
    "吊客": "主悲伤吊唁之象，宜留意亲友健康与情绪波动。",
}
TYPES = {
    "天乙贵人": "吉",
    "文昌贵人": "吉",
    "天德贵人": "吉",
    "月德贵人": "吉",
    "驿马": "中性",
    "华盖": "中性",
    "太极贵人": "吉",
    "金舆": "吉",
    "天厨贵人": "吉",
    "将星": "吉",
    "桃花（咸池）": "中性",
    "孤辰寡宿": "凶",
    "劫煞": "凶",
    "亡神": "凶",
    "羊刃": "凶",
    "空亡": "凶",
    "天罗地网": "凶",
    "白虎": "凶",
    "丧门": "凶",
    "吊客": "凶",
}


def _pillar_positions(pillars: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    stem_positions = {}
    branch_positions = {}
    labels = {"year": "年", "month": "月", "day": "日", "hour": "时"}
    for key, label in labels.items():
        pillar = pillars.get(key, {})
        stem = pillar.get("heavenly_stem")
        branch = pillar.get("earthly_branch")
        if stem:
            stem_positions[f"{label}干"] = stem
        if branch:
            branch_positions[f"{label}支"] = branch
    return stem_positions, branch_positions


def _match_positions(position_map: dict[str, str], targets: set[str]) -> list[str]:
    return [position for position, value in position_map.items() if value in targets]


def _branch_group(branch: str) -> str:
    for group in BRANCH_GROUP_MAP:
        if branch in group:
            return group
    return ""


def _day_pillar_empty_branches(day_stem: str, day_branch: str) -> set[str]:
    cycle = [(TIANGAN[index % 10], DIZHI[index % 12]) for index in range(60)]
    try:
        index = cycle.index((day_stem, day_branch))
    except ValueError:
        return set()
    return KONGWANG_BY_XUN[index // 10]


def _append_result(results: list[dict[str, str]], name: str, positions: list[str]) -> None:
    if not positions:
        return
    results.append(
        {
            "name": name,
            "type": TYPES[name],
            "position": "、".join(positions),
            "description": DESCRIPTIONS[name],
        }
    )


def calculate_shensha(pillars, gender) -> list:
    stem_positions, branch_positions = _pillar_positions(pillars)
    year_branch = pillars["year"]["earthly_branch"]
    month_branch = pillars["month"]["earthly_branch"]
    day_stem = pillars["day"]["heavenly_stem"]
    day_branch = pillars["day"]["earthly_branch"]
    results: list[dict[str, str]] = []

    _append_result(results, "天乙贵人", _match_positions(branch_positions, TIANYI_GUIREN.get(day_stem, set())))
    _append_result(results, "文昌贵人", _match_positions(branch_positions, WENCHANG.get(day_stem, set())))
    _append_result(
        results,
        "天德贵人",
        _match_positions(stem_positions, TIANDE_BY_MONTH_BRANCH.get(month_branch, set()))
        + _match_positions(branch_positions, TIANDE_BY_MONTH_BRANCH.get(month_branch, set())),
    )
    _append_result(results, "月德贵人", _match_positions(stem_positions, YUEDE_BY_MONTH_BRANCH.get(month_branch, set())))

    for source_branch in (year_branch, day_branch):
        group = _branch_group(source_branch)
        if not group:
            continue
        for name in ("驿马", "华盖", "将星", "桃花（咸池）", "劫煞", "亡神", "白虎"):
            positions = _match_positions(branch_positions, BRANCH_GROUP_MAP[group][name])
            if positions and not any(item["name"] == name for item in results):
                _append_result(results, name, positions)

    _append_result(results, "太极贵人", _match_positions(branch_positions, TAIJI_GUIREN.get(day_stem, set())))
    _append_result(results, "金舆", _match_positions(branch_positions, JINYU.get(day_stem, set())))
    _append_result(results, "天厨贵人", _match_positions(branch_positions, TIANCHU.get(day_stem, set())))

    year_group = _branch_group(year_branch)
    if year_group and year_group in GUCHEN_GUASU:
        lonely_positions = _match_positions(branch_positions, GUCHEN_GUASU[year_group]["孤辰"])
        widow_positions = _match_positions(branch_positions, GUCHEN_GUASU[year_group]["寡宿"])
        _append_result(results, "孤辰寡宿", lonely_positions + widow_positions)

    _append_result(results, "羊刃", _match_positions(branch_positions, YANGREN.get(day_stem, set())))
    _append_result(results, "空亡", _match_positions(branch_positions, _day_pillar_empty_branches(day_stem, day_branch)))

    if str(gender).lower() in {"male", "男"}:
        _append_result(results, "天罗地网", _match_positions(branch_positions, {"戌", "亥"}))
    else:
        _append_result(results, "天罗地网", _match_positions(branch_positions, {"辰", "巳"}))

    year_index = DIZHI.index(year_branch)
    sangmen_branch = DIZHI[(year_index + 2) % 12]
    diaoke_branch = DIZHI[(year_index - 2) % 12]
    _append_result(results, "丧门", _match_positions(branch_positions, {sangmen_branch}))
    _append_result(results, "吊客", _match_positions(branch_positions, {diaoke_branch}))

    return results
