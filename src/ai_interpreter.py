from __future__ import annotations

from typing import Any


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
        "narrative_zh": "你更像“启动者”：看到方向就会想先把路开出来。你对成长、推进与开疆拓土的敏感度很高。在高质量状态下，你能把愿景变成可执行的第一步；在压力状态下，你可能会把“推进”当作安全感来源，变得急、硬、对阻力不耐烦。你的练习不在于更用力，而在于学会让“推进”与“倾听/校准”并存。",
        "narrative_en": "You're a natural starter - when you see a direction, you want to clear the path first. At your best, you turn vision into actionable first steps. Under stress, you may push too hard and lose patience with resistance. Your growth edge: letting momentum coexist with listening and recalibration.",
    },
    "乙": {
        "en": "The Diplomat",
        "narrative_zh": "你更像“生长型适配者”：擅长顺势、渗透、缠绕式成长。你不一定用最强硬的方式达成目标，但很会在复杂系统里找到缝隙。高质量的乙是柔韧、审美在线、关系敏感；压力下可能变成过度迁就或犹疑不决。你的成长方向是：保留温柔，但把边界说清楚。",
        "narrative_en": "You're an adaptive grower - skilled at finding gaps in complex systems and working through them with flexibility rather than force. At your best, you're resilient, aesthetically attuned, and relationally sensitive. Under stress, you may over-accommodate. Growth means keeping your gentleness while making boundaries clear.",
    },
    "丙": {
        "en": "The Luminary",
        "narrative_zh": "你更像“照亮者”：自带外向表达与感染力，想法一旦点燃就会自然外化。高质量的丙是坦率、热情、带动连接；低质量时可能因为过度在意热度而失去耐心。你的练习是：让热情变成可持续燃料, 会收火、会复盘。",
        "narrative_en": "You're a natural illuminator - expressive, warm, and energizing. Ideas ignite and radiate outward. Under stress, enthusiasm may become impatience or impulsive commitment. Growth means turning passion into sustainable fuel: knowing when to dial down and reflect.",
    },
    "丁": {
        "en": "The Alchemist",
        "narrative_zh": "你更像“内在火种”：不一定外放，但有稳定的审美与意义感。你对细微情绪与氛围更敏感，擅长用含蓄的方式影响他人。压力下可能变成把情绪憋在心里、用冷处理保护自己。你的成长方向是：把感受翻译为对方能听懂的话。",
        "narrative_en": "You're an inner flame - not necessarily loud, but carrying stable aesthetic sense and meaning. You're sensitive to subtle emotions. Under stress, you may internalize and withdraw. Growth means translating feelings into language others can receive.",
    },
    "戊": {
        "en": "The Mountain",
        "narrative_zh": "你更像“承重结构”：习惯先把系统稳住，再谈扩张。高质量的戊是可靠、抗压、能扛事；压力下可能变成过度控制或固执。你的练习是：在稳态里给变化留空间，允许小范围试错。",
        "narrative_en": "You're a load-bearing structure - stabilize first, expand later. At your best, you're reliable, pressure-resistant, and dependable. Under stress, stability may harden into control. Growth means leaving room for change within your steady framework.",
    },
    "己": {
        "en": "The Garden",
        "narrative_zh": "你更像“滋养型土壤”：擅长维护关系与日常运转，让人感觉被照顾。压力下可能把“照顾”变成讨好或牺牲。你的成长方向是：照顾别人之前先照顾边界；当你说“不”，关系反而更真实。",
        "narrative_en": "You're nurturing soil - skilled at maintaining relationships and daily operations. Under stress, caring may become people-pleasing or self-sacrifice. Growth means setting boundaries before giving: when you say 'no,' relationships become more authentic.",
    },
    "庚": {
        "en": "The Warrior",
        "narrative_zh": "你更像“切割者与执行者”：擅长快速下判断、立标准。高质量的庚是果断、公正、行动到位；压力下可能变得锋利、情感表达粗糙。你的练习是：保留标准，但把“刀”变成“手术刀” - 对事精准、对人保留余地。",
        "narrative_en": "You're a cutter and executor - quick to judge, set standards, and act. At your best, decisive and fair. Under stress, sharpness may become bluntness. Growth means keeping your standards while turning the blade into a scalpel: precise on issues, generous with people.",
    },
    "辛": {
        "en": "The Jeweler",
        "narrative_zh": "你更像“精炼者”：追求质感、秩序与边界美学。压力下可能陷入完美主义与挑剔。你的成长方向是：允许“足够好”先落地，再用精炼能力迭代升级。",
        "narrative_en": "You're a refiner - pursuing texture, order, and aesthetic precision. Under stress, refinement may become perfectionism and criticism. Growth means letting 'good enough' land first, then using your refining ability to iterate upward.",
    },
    "壬": {
        "en": "The Ocean",
        "narrative_zh": "你更像“江河式思维”：信息量大、联想强、适应快。压力下可能因信息过载而焦虑，或因不喜欢被限制而难以承诺。你的练习是：把流动性变成选择 - 给自己设几个真正重要的锚点。",
        "narrative_en": "You're a river mind - high-volume, associative, adaptive. Under stress, information overload may cause anxiety, or resistance to commitment. Growth means converting flow into choice: set a few anchors that truly matter.",
    },
    "癸": {
        "en": "The Rain",
        "narrative_zh": "你更像“深水感受者”：敏感、内省、对隐性情绪与风险信号很快捕捉。压力下可能走向退缩或自我消耗。你的成长方向是：把敏感从“负担”升级为“工具” - 用清晰表达与边界来保护你的深度。",
        "narrative_en": "You're a deep-water sensor - sensitive, introspective, quick to pick up hidden emotional signals. Under stress, you may withdraw or self-deplete. Growth means upgrading sensitivity from burden to instrument: protect your depth with clear expression and boundaries.",
    },
}


class AIInterpreter:
    def _build_prompt(self, chart_data: dict[str, Any], lang: str = "both") -> str:
        day_master = chart_data.get("day_master", "未知")
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
                f"{god}更像一种自我保护模式：它通常在保护你对“{data['archetype']}”的需要。"
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
        dominant_gods = self._extract_dominant_gods(chart_data) or ["比肩", "正印"]

        if lang == "both":
            zh_day_master = self._build_day_master_section(day_master_value, "zh")
            en_day_master = self._build_day_master_section(day_master_value, "en")
            zh_gods = [self._build_god_section(god, "zh") for god in dominant_gods]
            en_gods = [self._build_god_section(god, "en") for god in dominant_gods]
            return {
                "lang": "both",
                "day_master": {"zh": zh_day_master, "en": en_day_master},
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
            "lang": resolved_lang,
            "day_master": day_master,
            "dominant_gods": gods,
            "narrative": self._compose_text(day_master, gods, resolved_lang),
        }


def post_interpret(payload: dict[str, Any]) -> dict[str, Any]:
    interpreter = AIInterpreter()
    lang = payload.get("lang", "both")
    if lang not in {"en", "zh", "both"}:
        lang = "both"
    return interpreter._generate_mock_interpretation(payload, lang=lang)


def get_interpret_archetypes() -> dict[str, dict[str, str]]:
    return TEN_GOD_ARCHETYPES
