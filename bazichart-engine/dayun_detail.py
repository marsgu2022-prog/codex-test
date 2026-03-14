from __future__ import annotations

from hashlib import sha256
from random import Random
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
LIUHE = {
    frozenset({"子", "丑"}): "六合",
    frozenset({"寅", "亥"}): "六合",
    frozenset({"卯", "戌"}): "六合",
    frozenset({"辰", "酉"}): "六合",
    frozenset({"巳", "申"}): "六合",
    frozenset({"午", "未"}): "六合",
}
CHONG = {
    frozenset({"子", "午"}): "相冲",
    frozenset({"丑", "未"}): "相冲",
    frozenset({"寅", "申"}): "相冲",
    frozenset({"卯", "酉"}): "相冲",
    frozenset({"辰", "戌"}): "相冲",
    frozenset({"巳", "亥"}): "相冲",
}
XING = {
    frozenset({"寅", "巳"}): "相刑",
    frozenset({"巳", "申"}): "相刑",
    frozenset({"寅", "申"}): "相刑",
    frozenset({"丑", "戌"}): "相刑",
    frozenset({"戌", "未"}): "相刑",
    frozenset({"丑", "未"}): "相刑",
}
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
SHISHEN_TEXTS = {
    "比肩": [
        {"zh": "比肩运来，同频者聚，适合并肩开路。", "en": "Peers gather in this cycle; shared force opens the road."},
        {"zh": "比肩主自主与边界，此运宜自立自强。", "en": "This cycle favors autonomy, boundaries, and self-directed strength."},
        {"zh": "比肩当令，宜结同道，不宜孤立自己。", "en": "Kindred allies matter now; isolation costs more than usual."},
        {"zh": "比肩之运重执行，脚踏实地比空谈更有力。", "en": "Execution outweighs rhetoric in a peer-driven season."},
        {"zh": "比肩旺时，先稳住自己，再谈带动他人。", "en": "Hold your own center first, then lead others from it."},
    ],
    "劫财": [
        {"zh": "劫财运动荡中带机会，关键在分寸与规则。", "en": "Opportunity hides inside volatility; rules and restraint matter most."},
        {"zh": "劫财之运宜争先，但不宜逞强夺势。", "en": "Move first if needed, but do not confuse force with mastery."},
        {"zh": "此运重资源调度，合作与竞争常常并行。", "en": "Resources, rivalry, and alliances will often travel together now."},
        {"zh": "劫财临运，宜讲清边界，免得好意变消耗。", "en": "Clear terms protect goodwill from turning into drain."},
        {"zh": "此运有破局之势，胆大之外更需心细。", "en": "Breakthrough is possible, but precision must walk beside courage."},
    ],
    "食神": [
        {"zh": "食神运柔而有光，适合创作、表达与养成。", "en": "A gentle brightness favors creation, expression, and cultivation."},
        {"zh": "食神主舒展，此运宜把才华慢慢做实。", "en": "Let talent ripen into steady craft rather than sudden display."},
        {"zh": "食神之运利口碑，温和反而更能积累影响。", "en": "Quiet consistency may build more influence than noise now."},
        {"zh": "此运适合让生活有节律，身心会因此更稳。", "en": "Rhythm and care will strengthen both body and spirit in this period."},
        {"zh": "食神到位，宜做长期作品，不宜过度冒进。", "en": "Make what can last; haste weakens the gift of this cycle."},
    ],
    "伤官": [
        {"zh": "伤官运锋芒毕露，表达力强，也更需分寸。", "en": "Sharp expression rises here; what matters is how cleanly you wield it."},
        {"zh": "伤官当运，适合破旧立新，但别只求快感。", "en": "Break conventions if you must, but build something better in their place."},
        {"zh": "此运利创意与突破，也易因直率得罪人。", "en": "Innovation is near, though bluntness may cost more than you think."},
        {"zh": "伤官之时宜把批判变成方案，才更有价值。", "en": "Turn critique into design; that is where the real power lives."},
        {"zh": "此运适合做难题，不适合做情绪的出口。", "en": "Use the edge for hard problems, not as a vessel for mood."},
    ],
    "偏财": [
        {"zh": "偏财运机会活络，利项目、资源与外部合作。", "en": "Opportunity moves quickly here, especially through projects and networks."},
        {"zh": "偏财之运宜开源拓路，但不宜贪多失衡。", "en": "Expand your channels, but do not let abundance become excess."},
        {"zh": "此运更重应变力，眼光和节奏都很重要。", "en": "Adaptability is wealth in this cycle; timing matters as much as vision."},
        {"zh": "偏财临运，宜主动找机会，不必一直等确定性。", "en": "Seek opportunity instead of waiting for certainty to knock."},
        {"zh": "资源流动加快，取舍得当就能见财。", "en": "Resources move faster now; wise selection turns movement into gain."},
    ],
    "正财": [
        {"zh": "正财运重稳定积累，适合守成、理财与踏实经营。", "en": "Steady accumulation is the blessing here; build, manage, and stay grounded."},
        {"zh": "正财之运宜务实，慢慢做反而更容易见成果。", "en": "Practical steps will outperform dramatic leaps in this cycle."},
        {"zh": "此运重责任与兑现，越稳越能生财。", "en": "Responsibility becomes revenue when held with steadiness."},
        {"zh": "正财到位，适合把日常系统做得更可靠。", "en": "Refine your systems now; reliability becomes a form of wealth."},
        {"zh": "此运宜守正出新，先稳住根基再谈扩大。", "en": "Preserve the core first, then let expansion happen from strength."},
    ],
    "七杀": [
        {"zh": "七杀运压强很大，越能定心越能转危为机。", "en": "Pressure intensifies here; composure turns threat into leverage."},
        {"zh": "七杀之运利决断与担当，也考验情绪承压。", "en": "This cycle rewards decisive courage and tests emotional stamina."},
        {"zh": "此运像逆风行舟，方向比蛮力更重要。", "en": "Like rowing against wind, direction matters more than brute force."},
        {"zh": "七杀当令，适合立威立规，不宜逞一时之气。", "en": "Establish order, not ego. Authority needs shape more than heat."},
        {"zh": "若能把压力化成纪律，这一步运反而很能成事。", "en": "When pressure becomes discipline, this cycle can accomplish much."},
    ],
    "正官": [
        {"zh": "正官运重规则、责任与位置，利升职与正名。", "en": "Order, role, and recognition define this official season."},
        {"zh": "正官之运宜守规矩，也宜用实力赢得尊重。", "en": "Honor the structure, then let competence speak within it."},
        {"zh": "此运利建立信誉，越稳重越能得信任。", "en": "Credibility grows here; gravity becomes a quiet advantage."},
        {"zh": "正官临运，适合进体制、担职位、立名分。", "en": "Titles, institutions, and formal authority are especially meaningful now."},
        {"zh": "责任会增加，但也意味着格局和位置在上升。", "en": "Greater responsibility often means your place is rising too."},
    ],
    "偏印": [
        {"zh": "偏印运主思考、技术与内在修炼，适合深耕专业。", "en": "A reflective, technical season — ideal for deepening mastery."},
        {"zh": "偏印之运宜独处学习，也宜建立自己的方法论。", "en": "Solitude and method-making become powerful allies now."},
        {"zh": "此运贵在看透本质，而不是只追表面热闹。", "en": "Look beneath surfaces; essence matters more than excitement."},
        {"zh": "偏印当令，利研究、写作、系统搭建与洞察。", "en": "Research, writing, systems, and insight all thrive in this period."},
        {"zh": "此运像灯下磨剑，未必喧哗，却很能蓄势。", "en": "Like sharpening steel under lamplight, this cycle stores quiet power."},
    ],
    "正印": [
        {"zh": "正印运温润而稳，利学习、资历、贵人与恢复。", "en": "Gentle and steady, this cycle favors learning, support, and replenishment."},
        {"zh": "正印之运宜进修、取证、积累名望与信任。", "en": "Study, credentials, and earned trust are especially fruitful now."},
        {"zh": "此运像春雨润物，适合慢慢补足底层能力。", "en": "Like spring rain, it nourishes the roots rather than the leaves."},
        {"zh": "正印临运，贵人助力增多，也更适合回到基本功。", "en": "Support increases now, and so does the value of returning to fundamentals."},
        {"zh": "此运宜养身养心，稳住根本，比急着冒头更重要。", "en": "Care for body and mind; rootedness matters more than display."},
    ],
}


def _pick(options: list[dict[str, str]], seed_text: str) -> dict[str, str]:
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


def _branch_interactions(dayun_branch: str, natal_branches: list[str]) -> tuple[list[str], int]:
    interactions: list[str] = []
    score = 0
    for branch in natal_branches:
        pair = frozenset({dayun_branch, branch})
        if pair in LIUHE:
            interactions.append(f"与{branch}成六合")
            score += 2
        elif pair in CHONG:
            interactions.append(f"与{branch}相冲")
            score -= 2
        elif pair in XING:
            interactions.append(f"与{branch}相刑")
            score -= 1
    return interactions, score


def _overall_level(effect_score: int) -> str:
    if effect_score >= 3:
        return "上吉"
    if effect_score >= 1:
        return "中吉"
    if effect_score == 0:
        return "平"
    if effect_score <= -3:
        return "小凶"
    return "平"


def _advice_for_relation(relation_score: int, favorable_hit: bool) -> str:
    if favorable_hit and relation_score >= 0:
        return "宜学习进修，积累资源，顺势放大长期优势，忌急功近利。"
    if relation_score < 0:
        return "宜稳住节奏，先处理风险点，再谈扩张，忌情绪化决策。"
    return "宜守正出新，先稳后进，给重要关系和项目留出调整空间。"


def generate_dayun_detail(pillars, dayun_ganzhi, gender) -> dict:
    day_master = pillars["day"]["heavenly_stem"]
    dayun_stem = dayun_ganzhi[0]
    dayun_branch = dayun_ganzhi[1]
    shishen = _shishen(day_master, dayun_stem)
    template = _pick(SHISHEN_TEXTS[shishen], f"{day_master}:{dayun_ganzhi}:{gender}")

    natal_branches = [pillars[key]["earthly_branch"] for key in ("year", "month", "day", "hour")]
    interactions, branch_score = _branch_interactions(dayun_branch, natal_branches)

    day_master_element = STEM_WUXING[day_master]
    dayun_element = STEM_WUXING[dayun_stem]
    favorable_elements = []
    if day_master_element == dayun_element or GENERATES[day_master_element] == dayun_element:
        favorable_elements.append(dayun_element)
    unfavorable_hit = CONTROLS[dayun_element] == day_master_element
    favorable_hit = bool(favorable_elements) and not unfavorable_hit

    effect_score = branch_score + (2 if favorable_hit else 0) - (2 if unfavorable_hit else 0)
    overall = _overall_level(effect_score)

    relation_text = "、".join(interactions) if interactions else "与原局地支关系平稳"
    wuxing_text = "有助命局喜用" if favorable_hit else ("对命局形成一定压力" if unfavorable_hit else "对命局影响中性")
    theme = template["zh"]
    career = f"{shishen}主运阶段，{theme}事业层面{relation_text}，{wuxing_text}。"
    wealth = "财运以稳为主，宜顺势累积，不宜激进投资和情绪化决策。"
    relationship = f"{dayun_branch}支入局后{relation_text}，关系层面宜多沟通、多校准节奏。"
    health = "注意脾胃、睡眠与压力管理，作息规律比短期冲刺更重要。"
    advice = _advice_for_relation(branch_score, favorable_hit)

    return {
        "ganzhi": dayun_ganzhi,
        "shishen": shishen,
        "overall": overall,
        "theme": theme,
        "career": career,
        "wealth": wealth,
        "relationship": relationship,
        "health": health,
        "advice": advice,
    }
