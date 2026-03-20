from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_METADATA_DIR = ROOT_DIR / "data" / "metadata"
KNOWLEDGE_CANDIDATES = [
    ROOT_DIR / "bazichart-engine" / "knowledge" / "BAZI.md",
    Path.home() / ".openclaw" / "agents" / "main" / "agent" / "knowledge" / "BAZI.md",
]

STEMS = [
    ("甲", "阳", "木"),
    ("乙", "阴", "木"),
    ("丙", "阳", "火"),
    ("丁", "阴", "火"),
    ("戊", "阳", "土"),
    ("己", "阴", "土"),
    ("庚", "阳", "金"),
    ("辛", "阴", "金"),
    ("壬", "阳", "水"),
    ("癸", "阴", "水"),
]

BRANCHES = [
    ("子", "水", ["癸"]),
    ("丑", "土", ["己", "癸", "辛"]),
    ("寅", "木", ["甲", "丙", "戊"]),
    ("卯", "木", ["乙"]),
    ("辰", "土", ["戊", "乙", "癸"]),
    ("巳", "火", ["丙", "戊", "庚"]),
    ("午", "火", ["丁", "己"]),
    ("未", "土", ["己", "丁", "乙"]),
    ("申", "金", ["庚", "壬", "戊"]),
    ("酉", "金", ["辛"]),
    ("戌", "土", ["戊", "辛", "丁"]),
    ("亥", "水", ["壬", "甲"]),
]

TEN_GODS_DEFINITIONS = [
    ("生我者", "异性", "正印"),
    ("生我者", "同性", "偏印"),
    ("我生者", "异性", "伤官"),
    ("我生者", "同性", "食神"),
    ("克我者", "异性", "正官"),
    ("克我者", "同性", "七杀"),
    ("我克者", "异性", "正财"),
    ("我克者", "同性", "偏财"),
    ("同我者", "异性", "劫财"),
    ("同我者", "同性", "比肩"),
]

TEN_GODS_TRAITS = [
    ("比肩", "独立、自尊、固执、竞争"),
    ("劫财", "果断、冲动、好胜、交际广"),
    ("食神", "温和、懒散、有口福、艺术感"),
    ("伤官", "聪明、叛逆、口才好、不服管"),
    ("偏财", "慷慨、风流、投机、人缘好"),
    ("正财", "务实、节俭、重承诺、保守"),
    ("七杀", "魄力、压力、军警气质、刚烈"),
    ("正官", "守规矩、有责任感、谨慎、官运"),
    ("偏印", "孤僻、钻研、直觉强、不稳定"),
    ("正印", "善良、包容、学历好、依赖性"),
]

COMMON_PATTERNS = ["正官格", "七杀格", "正印格", "偏印格", "食神格", "伤官格", "正财格", "偏财格"]
SPECIAL_PATTERNS = ["从强", "从弱", "从儿", "从财", "从杀", "化气格"]

FIVE_ELEMENTS_RELATIONS = [
    ("木", "生", "火", "木火通明", "木气得火而发，利表达与名声"),
    ("火", "生", "土", "火土相生", "火势化土，利落地与承载"),
    ("土", "生", "金", "土金相生", "土厚能生金，利资源沉淀"),
    ("金", "生", "水", "金白水清", "金气肃清，利思维与流动"),
    ("水", "生", "木", "水木相涵", "水润木荣，利学习与生发"),
    ("木", "克", "土", "木土相制", "木旺时能疏土，化呆滞为生机"),
    ("土", "克", "水", "土水相制", "土旺可制水泛，利稳定"),
    ("水", "克", "火", "水火既济", "水盛能制火烈，也易形成冲突"),
    ("火", "克", "金", "火炼真金", "火克金时常见压力下成器"),
    ("金", "克", "木", "金木交战", "金旺克木，利修剪也易伤生机"),
]

HE_RELATIONS = [
    ("甲", "合", "己", "天干五合", "甲己合多主协调、合作与转化"),
    ("乙", "合", "庚", "天干五合", "乙庚合常见资源与规则结合"),
    ("丙", "合", "辛", "天干五合", "丙辛合多主表达与秩序相逢"),
    ("丁", "合", "壬", "天干五合", "丁壬合常见情感与思维互动"),
    ("戊", "合", "癸", "天干五合", "戊癸合多主现实与智慧相接"),
    ("子", "合", "丑", "地支六合", "子丑合多主关系缓和与资源聚拢"),
    ("寅", "合", "亥", "地支六合", "寅亥合利学习、成长与远行"),
    ("卯", "合", "戌", "地支六合", "卯戌合利名誉与合作"),
    ("辰", "合", "酉", "地支六合", "辰酉合多主事务整合"),
    ("巳", "合", "申", "地支六合", "巳申合多主变动与执行"),
    ("午", "合", "未", "地支六合", "午未合多主人情与缓冲"),
]

CHONG_RELATIONS = [
    ("子", "冲", "午", "地支六冲", "子午冲多主情绪、居所或节奏变动"),
    ("丑", "冲", "未", "地支六冲", "丑未冲多主家庭、地产或脾胃议题"),
    ("寅", "冲", "申", "地支六冲", "寅申冲多主事业、人际或迁移起伏"),
    ("卯", "冲", "酉", "地支六冲", "卯酉冲多主关系、审美或合作波动"),
    ("辰", "冲", "戌", "地支六冲", "辰戌冲多主结构重组与信念碰撞"),
    ("巳", "冲", "亥", "地支六冲", "巳亥冲多主出行、思维或健康波动"),
]

XING_RELATIONS = [
    ("寅", "刑", "巳", "三刑", "寅巳刑多主行动急、压力大"),
    ("巳", "刑", "申", "三刑", "巳申刑多主计划反复与执行摩擦"),
    ("申", "刑", "寅", "三刑", "申寅刑多主竞争与外部压力"),
    ("丑", "刑", "戌", "持势之刑", "丑戌刑多主责任、规则或地产压力"),
    ("戌", "刑", "未", "持势之刑", "戌未刑多主家庭与价值观磨合"),
    ("未", "刑", "丑", "持势之刑", "未丑刑多主内耗与现实牵扯"),
    ("子", "刑", "卯", "无礼之刑", "子卯刑多主关系失衡与表达冲突"),
    ("辰", "刑", "辰", "自刑", "辰辰自刑多主反复内耗"),
    ("午", "刑", "午", "自刑", "午午自刑多主情绪与心火偏旺"),
    ("酉", "刑", "酉", "自刑", "酉酉自刑多主完美主义与压抑"),
    ("亥", "刑", "亥", "自刑", "亥亥自刑多主思虑过重"),
]

TERM_ALIASES = [
    {"standard_term": "比肩", "aliases": ["比劫之阳", "同类帮身", "兄弟星"], "english": "Companion Star"},
    {"standard_term": "劫财", "aliases": ["比劫之阴", "争财星", "同类夺财"], "english": "Rob Wealth"},
    {"standard_term": "食神", "aliases": ["福星", "寿星", "我生之吉神"], "english": "Eating God"},
    {"standard_term": "伤官", "aliases": ["秀气之神", "才华外泄", "我生之偏神"], "english": "Hurting Officer"},
    {"standard_term": "正财", "aliases": ["妻财", "正妻星", "稳定之财"], "english": "Direct Wealth"},
    {"standard_term": "偏财", "aliases": ["横财", "外财", "流动之财"], "english": "Indirect Wealth"},
    {"standard_term": "正官", "aliases": ["官星", "贵气之神", "约束之星"], "english": "Direct Officer"},
    {"standard_term": "七杀", "aliases": ["偏官", "将星", "压力之神"], "english": "Seven Killings"},
    {"standard_term": "正印", "aliases": ["印绶", "护身之印", "文书星"], "english": "Direct Resource"},
    {"standard_term": "偏印", "aliases": ["枭神", "倒食", "异路之印"], "english": "Indirect Resource"},
    {"standard_term": "日主", "aliases": ["日元", "命主", "身主"], "english": "Day Master"},
    {"standard_term": "用神", "aliases": ["喜用", "主用之神", "命局平衡点"], "english": "Useful God"},
    {"standard_term": "忌神", "aliases": ["所忌之神", "失衡之源", "不喜之神"], "english": "Unfavorable God"},
    {"standard_term": "相神", "aliases": ["辅神", "辅助用神", "成格之佐"], "english": "Assistant God"},
    {"standard_term": "调候", "aliases": ["寒暖燥湿调整", "气候平衡", "四时调剂"], "english": "Climate Adjustment"},
    {"standard_term": "扶抑", "aliases": ["抑强扶弱", "平衡取用", "强弱取法"], "english": "Balance Method"},
    {"standard_term": "通关", "aliases": ["桥梁之神", "解战之法", "转化之神"], "english": "Mediator Method"},
    {"standard_term": "格局", "aliases": ["命格", "成格", "立格"], "english": "Structure"},
    {"standard_term": "从强", "aliases": ["从旺", "顺势从强", "专旺从势"], "english": "Follow Strong"},
    {"standard_term": "从弱", "aliases": ["从势", "弃命从弱", "顺弱之局"], "english": "Follow Weak"},
    {"standard_term": "从财", "aliases": ["弃命从财", "财旺从势", "从财格"], "english": "Follow Wealth"},
    {"standard_term": "从杀", "aliases": ["弃命从官杀", "从官杀", "从杀格"], "english": "Follow Killing"},
    {"standard_term": "化气格", "aliases": ["化神格", "五合化气", "化气成格"], "english": "Transformative Structure"},
    {"standard_term": "正官格", "aliases": ["官格", "官星立格", "正官成格"], "english": "Direct Officer Structure"},
    {"standard_term": "七杀格", "aliases": ["杀格", "偏官格", "七杀成格"], "english": "Seven Killings Structure"},
    {"standard_term": "食神格", "aliases": ["食神成格", "福神格", "食神立格"], "english": "Eating God Structure"},
    {"standard_term": "伤官格", "aliases": ["伤官成格", "秀气格", "伤官立格"], "english": "Hurting Officer Structure"},
    {"standard_term": "正财格", "aliases": ["财格", "正财成格", "妻财格"], "english": "Direct Wealth Structure"},
    {"standard_term": "偏财格", "aliases": ["偏财成格", "外财格", "活财格"], "english": "Indirect Wealth Structure"},
    {"standard_term": "六亲", "aliases": ["亲属象", "亲缘关系", "家属定位"], "english": "Six Relations"},
    {"standard_term": "夫妻宫", "aliases": ["日支", "婚姻宫", "配偶宫"], "english": "Spouse Palace"},
    {"standard_term": "月令", "aliases": ["月支司令", "当令之气", "司权之支"], "english": "Monthly Command"},
    {"standard_term": "天干", "aliases": ["十干", "十天干", "干"], "english": "Heavenly Stem"},
    {"standard_term": "地支", "aliases": ["十二支", "十二地支", "支"], "english": "Earthly Branch"},
    {"standard_term": "藏干", "aliases": ["支中人元", "地支藏气", "支内天干"], "english": "Hidden Stems"},
    {"standard_term": "财星", "aliases": ["财富之星", "我克之神", "资源输出对象"], "english": "Wealth Star"},
    {"standard_term": "官星", "aliases": ["权力之星", "克我之神", "名位之星"], "english": "Officer Star"},
    {"standard_term": "印星", "aliases": ["资源之星", "生我之神", "靠山之星"], "english": "Resource Star"},
    {"standard_term": "比劫", "aliases": ["比肩劫财", "同党", "同类之神"], "english": "Peers"},
]

CONTRADICTIONS = [
    {
        "topic": "用神取法",
        "school_a": "子平真诠",
        "position_a": "以月令司令为纲，先定格再取用神，相神辅佐。",
        "school_b": "滴天髓",
        "position_b": "以日主旺衰、气势流通为核心，所喜所赖者即用神。",
        "resolution": "先看月令与格局，再回到日主强弱和流通校验，避免只守单一口径。",
    },
    {
        "topic": "调候优先级",
        "school_a": "穷通宝鉴",
        "position_a": "四时寒暖燥湿先定，再谈格局与扶抑。",
        "school_b": "子平真诠",
        "position_b": "格局成立与月令透干优先，调候属于取用层面的补充。",
        "resolution": "寒暖失衡明显时先调候，气候平衡后再按格局与扶抑细化。",
    },
    {
        "topic": "从格成立条件",
        "school_a": "子平真诠",
        "position_a": "从格必须真从，日主无根无助，不可见明显逆势之神。",
        "school_b": "盲派",
        "position_b": "以实际应事为主，只要气势一边倒即可从，不拘泥细根细助。",
        "resolution": "先按真从严判，边界盘再结合行运与应事经验修正。",
    },
    {
        "topic": "伤官见官",
        "school_a": "子平真诠",
        "position_a": "伤官与正官交战，多主破格，宜有印化或财通关。",
        "school_b": "盲派",
        "position_b": "伤官见官未必尽凶，若组合成名成事，反主强表达与破局能力。",
        "resolution": "同时看是否有印、财、合化与行运引动，不能机械断凶。",
    },
    {
        "topic": "七杀成用",
        "school_a": "滴天髓",
        "position_a": "七杀得制得化则成权，关键在气势流转。",
        "school_b": "子平真诠",
        "position_b": "七杀须先看是否成格，再论印化食制，不成格则多主压迫。",
        "resolution": "先辨成格与否，再看制化是否顺气，兼顾结构与动态。",
    },
    {
        "topic": "六亲定位",
        "school_a": "韩立知识库",
        "position_a": "男命财为妻、女命官为夫，以十神对应六亲。",
        "school_b": "盲派",
        "position_b": "六亲除十神外还要重宫位、组合与应期，不可只看单一星。",
        "resolution": "十神用于定类，宫位与组合用于定人定事，二者并看。",
    },
    {
        "topic": "断事方法",
        "school_a": "滴天髓",
        "position_a": "重视原局气象、流通与体用，不宜拘泥单条口诀。",
        "school_b": "盲派",
        "position_b": "重视快速应期和象法，强调口诀直断与事件映射。",
        "resolution": "底层判断用体用气势，落到事件层时再借助象法提速。",
    },
    {
        "topic": "月令是否绝对优先",
        "school_a": "子平真诠",
        "position_a": "月令为提纲，判格优先级最高。",
        "school_b": "滴天髓",
        "position_b": "若全局气势成象，月令虽重但不必绝对压倒全局。",
        "resolution": "常规命局尊月令，特殊气势盘需把月令放回全局权重中审视。",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成八字知识图谱元数据")
    parser.add_argument(
        "--targets",
        nargs="+",
        choices=["rule_fragments", "concept_relations", "term_aliases", "contradictions"],
        required=True,
    )
    parser.add_argument("--metadata-dir", type=Path, default=DEFAULT_METADATA_DIR)
    return parser.parse_args()


def detect_knowledge_path() -> Path:
    for path in KNOWLEDGE_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("未找到 BAZI.md")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def build_rule_fragments() -> list[dict[str, Any]]:
    fragments: list[dict[str, Any]] = []

    def add(
        source: str,
        category: str,
        condition: str,
        conclusion: str,
        confidence: str = "medium",
        exceptions: list[str] | None = None,
    ) -> None:
        fragments.append(
            {
                "rule_id": f"RF{len(fragments) + 1:03d}",
                "source": source,
                "category": category,
                "condition": condition,
                "conclusion": conclusion,
                "exceptions": exceptions or [],
                "confidence": confidence,
                "contradicts": [],
            }
        )

    for stem, yinyang, element in STEMS:
        add("韩立知识库", "十神", f"命局出现天干{stem}", f"{stem}属{yinyang}干，五行为{element}", "high")
        add("滴天髓", "十神", f"日主为{stem}", f"先按{element}性与{yinyang}属性观察日主气势与流通", "medium")

    for branch, element, hidden_stems in BRANCHES:
        add("韩立知识库", "格局", f"命局出现地支{branch}", f"{branch}主五行为{element}", "high")
        add("韩立知识库", "格局", f"分析地支{branch}", f"{branch}藏干为{'、'.join(hidden_stems)}", "high")

    for relation, polarity, god in TEN_GODS_DEFINITIONS:
        add("韩立知识库", "十神", f"以日主为中心，{relation}且为{polarity}", f"十神取{god}", "high")

    for god, trait in TEN_GODS_TRAITS:
        add("盲派", "十神", f"命局{god}明显", f"多见{trait}", "medium", ["需结合旺衰与组合，不能只凭性格词直断"])

    add("子平真诠", "格局", "判格时先看月令", "月支藏干透出天干者可作为格局判断重点", "high")
    for pattern in COMMON_PATTERNS:
        add("子平真诠", "格局", f"月令透出符合{pattern}条件", f"可按{pattern}立格", "medium")
    for pattern in SPECIAL_PATTERNS:
        add(
            "子平真诠",
            "格局",
            f"命局整体趋向{pattern}",
            f"按特殊格局{pattern}处理，不再完全沿普通扶抑法",
            "medium",
            ["若日主仍有有力根气或逆势之神透出，则可能不能真从"],
        )

    add("滴天髓", "用神", "日主偏强", "宜取泄、耗、克之神以平衡命局", "high")
    add("滴天髓", "用神", "日主偏弱", "宜取生、扶、助之神以扶身", "high")
    add("滴天髓", "用神", "两种五行相战不下", "宜取通关之神化解冲突", "high")
    add("穷通宝鉴", "调候", "冬季寒局明显", "宜用火调候，先解寒湿再谈成格", "high")
    add("穷通宝鉴", "调候", "夏季热局明显", "宜用水调候，先解炎燥再谈扶抑", "high")

    add("韩立知识库", "断事", "大运每十年一变", "可据此划分人生阶段主旋律", "medium")
    add("盲派", "断事", "流年与命局形成刑冲合害", "常为事件应期", "high")
    add("盲派", "断事", "大运流年与命局形成三合三会", "多主大事发生", "medium")

    kinship_rules = [
        ("男命见正财", "多取妻星"),
        ("男命见偏财", "多取父星"),
        ("男命见正印", "多取母星"),
        ("男命见正官", "多取女星"),
        ("男命见七杀", "多取子星"),
        ("女命见正官", "多取夫星"),
        ("女命见七杀", "多取情缘压力位"),
        ("女命见食神", "多取女星"),
        ("女命见伤官", "多取子星"),
        ("女命见偏财", "多取父星"),
    ]
    for condition, conclusion in kinship_rules:
        add("韩立知识库", "六亲", condition, conclusion, "medium", ["需结合宫位、旺衰和组合同参"])

    judgments = [
        ("看婚姻", "男看财星，女看官星，并结合日支夫妻宫"),
        ("看财运", "看财星旺衰及大运流年是否走财运"),
        ("看事业", "看官杀与印星，并结合月柱事业宫"),
        ("看健康", "看五行偏枯及受克五行所主器官"),
    ]
    for condition, conclusion in judgments:
        add("韩立知识库", "断事", condition, conclusion, "high")

    ordinary_rule = next(item for item in fragments if item["condition"] == "判格时先看月令")
    strong_rule = next(item for item in fragments if item["condition"] == "日主偏强")
    weak_rule = next(item for item in fragments if item["condition"] == "日主偏弱")
    special_rules = [item for item in fragments if item["condition"].startswith("命局整体趋向")]
    for item in special_rules:
        item["contradicts"] = [ordinary_rule["rule_id"], strong_rule["rule_id"], weak_rule["rule_id"]]
    ordinary_rule["contradicts"] = [item["rule_id"] for item in special_rules]
    strong_rule["contradicts"] = [item["rule_id"] for item in special_rules if "从强" in item["condition"]]
    weak_rule["contradicts"] = [item["rule_id"] for item in special_rules if "从弱" in item["condition"]]

    return fragments


def build_concept_relations() -> list[dict[str, str]]:
    relations: list[dict[str, str]] = []

    def add(a: str, relation: str, b: str, context: str, implication: str) -> None:
        relations.append(
            {
                "concept_a": a,
                "relation": relation,
                "concept_b": b,
                "context": context,
                "implication": implication,
            }
        )

    for stem, yinyang, element in STEMS:
        add(stem, "属", element, "十天干五行归属", f"{stem}按{element}处理五行气势")
        add(stem, "为", f"{yinyang}干", "十天干阴阳归属", f"{stem}带有{yinyang}性表达")

    for branch, element, hidden_stems in BRANCHES:
        add(branch, "属", element, "十二地支五行归属", f"{branch}按{element}看地支主气")
        for hidden_stem in hidden_stems:
            add(branch, "藏", hidden_stem, "地支藏干", f"{branch}内含{hidden_stem}之气")

    for relation, polarity, god in TEN_GODS_DEFINITIONS:
        add(relation, "定义为", god, "十神判定", f"{relation}且为{polarity}时取{god}")

    for god, trait in TEN_GODS_TRAITS:
        add(god, "对应", trait, "十神性格特征", f"{god}常引出{trait}")

    for source, relation, target, context, implication in FIVE_ELEMENTS_RELATIONS:
        add(source, relation, target, context, implication)

    for source, relation, target, context, implication in HE_RELATIONS:
        add(source, relation, target, context, implication)

    for source, relation, target, context, implication in CHONG_RELATIONS:
        add(source, relation, target, context, implication)

    for source, relation, target, context, implication in XING_RELATIONS:
        add(source, relation, target, context, implication)

    add("伤官", "生", "财星", "伤官生财格", "聪明才智可转化为财富")
    add("正官", "喜", "印绶", "官印相生", "规范与资源相互扶持")
    add("七杀", "喜", "印星", "杀印相生", "压力可转化为权力与执行力")
    add("食神", "制", "七杀", "食神制杀", "缓冲压力并化攻击性为产出")
    add("财星", "助", "官星", "财生官", "资源可推动名位与责任")
    add("比肩", "争", "财星", "比劫争财", "同类竞争会分走资源")

    return relations


def build_term_aliases() -> list[dict[str, Any]]:
    return TERM_ALIASES


def build_contradictions() -> list[dict[str, str]]:
    return CONTRADICTIONS


def main() -> None:
    args = parse_args()
    knowledge_path = detect_knowledge_path()
    _ = knowledge_path.read_text(encoding="utf-8")

    builders = {
        "rule_fragments": build_rule_fragments,
        "concept_relations": build_concept_relations,
        "term_aliases": build_term_aliases,
        "contradictions": build_contradictions,
    }

    for target in args.targets:
        payload = builders[target]()
        write_json(args.metadata_dir / f"{target}.json", payload)
        print(f"{target}={len(payload)}")


if __name__ == "__main__":
    main()
