from __future__ import annotations

from hashlib import sha256
from random import Random


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
STEM_YINYANG = {
    "甲": "阳",
    "乙": "阴",
    "丙": "阳",
    "丁": "阴",
    "戊": "阳",
    "己": "阴",
    "庚": "阳",
    "辛": "阴",
    "壬": "阳",
    "癸": "阴",
}
GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
CONTROLS = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}
SHISHEN_LABELS = {
    ("同我", True): "比肩",
    ("同我", False): "劫财",
    ("我生", True): "食神",
    ("我生", False): "伤官",
    ("我克", True): "偏财",
    ("我克", False): "正财",
    ("克我", True): "七杀",
    ("克我", False): "正官",
    ("生我", True): "偏印",
    ("生我", False): "正印",
}
DIMENSION_TEXTS = {
    "比肩": {
        "career": [
            {"zh": "比肩流年事业重执行与并肩协作，适合稳步推进既定目标。", "en": "Career favors steady execution and strong peer alignment this year."},
            {"zh": "同类之气偏旺，适合拓展团队与共同项目。", "en": "Shared energy helps teams and collaborative projects gain traction."},
            {"zh": "今年事业更适合自己掌舵，也要避免与同级争强。", "en": "Lead your own course, but avoid wasting strength in rivalry."},
            {"zh": "比肩主自立，适合把能力做成稳定输出。", "en": "Self-reliance becomes influence when your skills turn consistent."},
            {"zh": "此年事业宜稳扎稳打，慢一点反而更能见成效。", "en": "Measured progress may accomplish more than aggressive expansion."},
        ],
        "wealth": [
            {"zh": "财运以守成为主，开支多与人情协作相关。", "en": "Wealth is best managed through preservation and careful collaboration."},
            {"zh": "今年适合共担资源，但不宜冲动合伙。", "en": "Shared resources can help, but impulsive partnerships should wait."},
            {"zh": "比肩旺时财来财去，预算要更清楚。", "en": "Money may move quickly now; budgeting must be precise."},
            {"zh": "收益稳中有升，重在靠实力而非侥幸。", "en": "Returns grow through ability, not chance."},
            {"zh": "今年宜留现金流，勿因义气扩大风险。", "en": "Keep cash flow healthy; do not let loyalty enlarge risk."},
        ],
        "relationship": [
            {"zh": "关系讲求平等，越坦诚越能维系长久。", "en": "Relationships thrive on equality and plain honesty this year."},
            {"zh": "比肩流年容易各有主张，需主动协调节奏。", "en": "Everyone may have a view; harmony needs active pacing."},
            {"zh": "同类之气有共鸣，也有较劲，沟通要柔一些。", "en": "Resonance and friction may arrive together; speak with softness."},
            {"zh": "感情宜并肩前进，不宜反复比较得失。", "en": "Walk side by side rather than measuring every gain and loss."},
            {"zh": "今年适合建立更清晰的相处边界。", "en": "Clearer relational boundaries will be especially helpful now."},
        ],
        "health": [
            {"zh": "身心状态总体平稳，注意筋骨和运动恢复。", "en": "Overall vitality is stable; care for joints and physical recovery."},
            {"zh": "比肩旺时易硬撑，疲劳要及时释放。", "en": "Do not let stubborn endurance replace real rest."},
            {"zh": "今年宜规律运动，胜过短期冲刺。", "en": "Consistent movement is better than bursts of intensity."},
            {"zh": "注意肩颈与体能耗损，劳逸要平衡。", "en": "Watch neck, shoulders, and gradual depletion of energy."},
            {"zh": "健康关键在节律，不在一时逞强。", "en": "Rhythm matters more than pushing yourself too hard."},
        ],
        "advice": [
            {"zh": "把边界说清，把节奏稳住，很多事就顺了。", "en": "Name your boundaries and steady your rhythm; much will follow."},
            {"zh": "宜并肩成事，忌无谓较劲。", "en": "Build with others, avoid needless rivalry."},
            {"zh": "守住自己的路，也给别人留空间。", "en": "Hold your path without crowding another’s."},
            {"zh": "今年重在稳，不在抢。", "en": "This year values steadiness over haste."},
            {"zh": "以长期眼光安排资源与关系。", "en": "Let long vision guide your resources and ties."},
        ],
    },
}


def _clone_for_all_shishen() -> dict:
    base = DIMENSION_TEXTS["比肩"]
    labels = ["劫财", "食神", "伤官", "偏财", "正财", "七杀", "正官", "偏印", "正印"]
    cloned = {"比肩": base}
    for label in labels:
        cloned[label] = base
    return cloned


ALL_TEXTS = _clone_for_all_shishen()


def _pick(options, seed_text):
    rng = Random(int(sha256(seed_text.encode("utf-8")).hexdigest(), 16))
    return options[rng.randrange(len(options))]


def _relation(day_element: str, target_element: str) -> str:
    if day_element == target_element:
        return "同我"
    if GENERATES[day_element] == target_element:
        return "我生"
    if GENERATES[target_element] == day_element:
        return "生我"
    if CONTROLS[day_element] == target_element:
        return "我克"
    return "克我"


def _shishen(day_master: str, target_stem: str) -> str:
    relation = _relation(STEM_WUXING[day_master], STEM_WUXING[target_stem])
    same_polarity = STEM_YINYANG[day_master] == STEM_YINYANG[target_stem]
    return SHISHEN_LABELS[(relation, same_polarity)]


def _score(base: int, delta: int) -> int:
    return max(0, min(100, base + delta))


def generate_liunian_detail(pillars, dayun_ganzhi, liunian_ganzhi, gender) -> dict:
    day_master = pillars["day"]["heavenly_stem"]
    liunian_stem = liunian_ganzhi[0]
    liunian_branch = liunian_ganzhi[1]
    shishen = _shishen(day_master, liunian_stem)
    text_bank = ALL_TEXTS[shishen]
    seed = f"{day_master}:{dayun_ganzhi}:{liunian_ganzhi}:{gender}"

    branch_bonus = 5 if liunian_branch in {"寅", "卯", "巳", "午"} else (-5 if liunian_branch in {"申", "酉", "亥"} else 0)
    career_score = _score(70, branch_bonus)
    wealth_score = _score(68, 10 if shishen in {"偏财", "正财"} else branch_bonus)
    relationship_score = _score(65, -5 if shishen in {"七杀", "伤官"} else 5 if shishen in {"正印", "正官"} else 0)
    health_score = _score(72, -8 if shishen in {"七杀", "劫财"} else 0)
    avg = round((career_score + wealth_score + relationship_score + health_score) / 4)
    overall = "上吉" if avg >= 80 else "中吉" if avg >= 65 else "平" if avg >= 50 else "小凶"

    return {
        "ganzhi": liunian_ganzhi,
        "shishen": shishen,
        "overall": overall,
        "career": {"score": career_score, "text": _pick(text_bank["career"], f"{seed}:career")},
        "wealth": {"score": wealth_score, "text": _pick(text_bank["wealth"], f"{seed}:wealth")},
        "relationship": {"score": relationship_score, "text": _pick(text_bank["relationship"], f"{seed}:relationship")},
        "health": {"score": health_score, "text": _pick(text_bank["health"], f"{seed}:health")},
        "advice": _pick(text_bank["advice"], f"{seed}:advice"),
    }
