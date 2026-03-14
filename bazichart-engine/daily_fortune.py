from __future__ import annotations

from datetime import date as date_type, datetime
from hashlib import sha256
from random import Random
from typing import Any


TIANGAN = "甲乙丙丁戊己庚辛壬癸"
DIZHI = "子丑寅卯辰巳午未申酉戌亥"
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
GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
CONTROLS = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}
LUCKY_COLORS = {"木": "青绿色", "火": "红色", "土": "黄色", "金": "白色", "水": "黑蓝色"}
LUCKY_DIRECTIONS = {"木": "正东", "火": "正南", "土": "中宫", "金": "正西", "水": "正北"}
LUCKY_NUMBERS = {"木": 3, "火": 9, "土": 5, "金": 7, "水": 1}
FORTUNE_LEVELS = {
    "生我": "上吉",
    "我克": "中吉",
    "克我": "小凶",
    "我生": "平",
    "同我": "中吉",
    "general_strong": "小吉",
    "general_soft": "平",
}
GENERAL_MESSAGES = {
    "木": [
        "木气升发之日，适合启动新计划，循序渐进更容易见效。",
        "今日木意渐旺，利于沟通协作和拓展新方向。",
        "木性能量偏强，适合学习成长，也宜多亲近自然。",
    ],
    "火": [
        "火旺之日，宜大胆行动，把握机遇，主动表达更容易被看见。",
        "今日火势明朗，适合推进卡住的事务，但要避免急躁。",
        "火能量上扬，利执行与展示，重要决定宜趁势落实。",
    ],
    "土": [
        "土气稳重之日，适合整理秩序、夯实基础，凡事求稳更佳。",
        "今日土势厚实，利于收尾总结，也适合处理现实问题。",
        "土能量偏强，适合沉淀资源、修正细节，不宜操之过急。",
    ],
    "金": [
        "金气肃清之日，适合做判断、立边界，简化事务更有效率。",
        "今日金性能量明显，利于定标准、做取舍，但表达宜留余地。",
        "金势清明，适合处理合同、规则与关键决策。",
    ],
    "水": [
        "水气流动之日，适合思考、调研与调整节奏，顺势而为更顺畅。",
        "今日水势活跃，利于复盘、沟通和策略布局。",
        "水能量渐强，适合观察局势、整合信息，再决定下一步。",
    ],
}
PERSONAL_MESSAGES = {
    "生我": [
        "当日{day_ganzhi}之气来生扶日主{day_master}，适合争取资源与外部支持。",
        "今日能量偏向助力，日主{day_master}更容易得到回应，宜主动推进关键事务。",
        "当日五行生身，利学习提升、人脉合作与重要沟通。",
    ],
    "我克": [
        "日主{day_master}可驾驭当日之气，财务与执行层面更易见成果。",
        "今天属于可掌控的一天，适合谈结果、抓重点、推动落地。",
        "我克者为财，今日更适合资源调配和务实行动。",
    ],
    "克我": [
        "当日之气对日主{day_master}形成压力，宜稳住节奏，先难后易。",
        "今天容易感到被催逼，关键在于保留体力，不宜硬碰硬。",
        "克身之日适合收敛锋芒，先处理确定性高的事项。",
    ],
    "我生": [
        "日主{day_master}向外泄秀，适合输出创意与表达，但也要注意精力分配。",
        "今天更像付出型的一天，利分享、呈现与帮助他人。",
        "我生之日宜做内容、复盘与沟通，不宜把日程排得过满。",
    ],
    "同我": [
        "同气相求，日主{day_master}今日更容易获得共鸣与同伴支持。",
        "比和之日适合团队协作、资源互通，也要防止固执己见。",
        "今日与自身频率相近，适合强化已有节奏和长期计划。",
    ],
}
BLESSINGS = [
    "愿你今日所行皆坦途。",
    "愿你今天心定事成，步步有回应。",
    "愿你在今日的节奏里，稳稳接住好运。",
    "愿你今日所想有光，所行有成。",
]
WALLPAPER_LINES = {
    "木": ["让成长发生", "把今天种进未来"],
    "火": ["把握今日火之能量", "勇敢迈出关键一步"],
    "土": ["先稳住节奏", "好运会在扎实里显现"],
    "金": ["做清晰的决定", "把重点留给真正重要的事"],
    "水": ["顺势而行", "今天适合看清方向再出发"],
}


def _ganzhi_for_day(target_date: date_type) -> tuple[str, str]:
    base_date = date_type(1984, 2, 2)
    delta_days = (target_date - base_date).days
    return TIANGAN[delta_days % 10], DIZHI[delta_days % 12]


def _element_relation(day_master_element: str, day_element: str) -> str:
    if day_master_element == day_element:
        return "同我"
    if GENERATES[day_element] == day_master_element:
        return "生我"
    if GENERATES[day_master_element] == day_element:
        return "我生"
    if CONTROLS[day_master_element] == day_element:
        return "我克"
    return "克我"


def _pick(options: list[str], seed_text: str) -> str:
    rng = Random(int(sha256(seed_text.encode("utf-8")).hexdigest(), 16))
    return options[rng.randrange(len(options))]


def _branch_bonus(branch: str) -> int:
    if branch in {"寅", "卯", "辰", "巳", "午"}:
        return 1
    if branch in {"申", "酉", "亥"}:
        return 0
    return -1


def _fortune_level(relation: str, branch: str) -> str:
    levels = ["凶", "小凶", "平", "小吉", "中吉", "上吉", "大吉"]
    base_map = {"生我": 5, "我克": 4, "克我": 1, "我生": 2, "同我": 4}
    index = max(0, min(6, base_map[relation] + _branch_bonus(branch)))
    return levels[index]


def _general_fortune(day_element: str, day_ganzhi: str, branch: str, date_str: str) -> tuple[str, str, str]:
    general_message = _pick(GENERAL_MESSAGES[day_element], f"general:{date_str}:{day_ganzhi}")
    wallpaper_lines = WALLPAPER_LINES[day_element]
    wallpaper_text = f"{wallpaper_lines[0]}\n{wallpaper_lines[1]}"
    blessing = _pick(BLESSINGS, f"blessing:{date_str}:{branch}")
    return general_message, wallpaper_text, blessing


def generate_daily_fortune(date, user_bazi=None) -> dict:
    target_date = date if isinstance(date, date_type) else datetime.strptime(str(date), "%Y-%m-%d").date()
    day_stem, day_branch = _ganzhi_for_day(target_date)
    day_ganzhi = f"{day_stem}{day_branch}"
    day_element = STEM_WUXING[day_stem]
    general_message, wallpaper_text, blessing = _general_fortune(day_element, day_ganzhi, day_branch, target_date.isoformat())

    result = {
        "date": target_date.isoformat(),
        "day_ganzhi": day_ganzhi,
        "day_wuxing": day_element,
        "fortune_level": "小吉" if _branch_bonus(day_branch) >= 0 else "平",
        "lucky_color": LUCKY_COLORS[day_element],
        "lucky_direction": LUCKY_DIRECTIONS[day_element],
        "lucky_number": LUCKY_NUMBERS[day_element],
        "general_message": general_message,
        "wallpaper_text": wallpaper_text,
        "blessing": blessing,
    }

    if isinstance(user_bazi, dict):
        day_master = (
            user_bazi.get("day_master")
            or user_bazi.get("day_master_stem")
            or user_bazi.get("day", {}).get("heavenly_stem")
            or user_bazi.get("four_pillars", {}).get("day", {}).get("heavenly_stem")
        )
        if day_master in STEM_WUXING:
            day_master_element = STEM_WUXING[day_master]
            relation = _element_relation(day_master_element, day_element)
            result["fortune_level"] = _fortune_level(relation, day_branch)
            result["personal_message"] = _pick(
                PERSONAL_MESSAGES[relation],
                f"personal:{target_date.isoformat()}:{day_master}:{day_ganzhi}",
            ).format(day_master=day_master, day_ganzhi=day_ganzhi)

    return result
