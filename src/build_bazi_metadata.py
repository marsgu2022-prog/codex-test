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
MONTH_BRANCHES = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"]
SEASON_BY_BRANCH = {
    "寅": "spring",
    "卯": "spring",
    "辰": "spring",
    "巳": "summer",
    "午": "summer",
    "未": "summer",
    "申": "autumn",
    "酉": "autumn",
    "戌": "autumn",
    "亥": "winter",
    "子": "winter",
    "丑": "winter",
}

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

TIAOHOU_RAW = {
    "甲": [
        ("丙火", "癸水", "初春木嫩，先丙解冻，再癸润泽。"),
        ("庚金", "丁火", "仲春木旺，庚金修枝，丁火发荣。"),
        ("庚金", "丁火", "辰月木盛土湿，可辅壬水润根。"),
        ("癸水", "丁火", "初夏木燥，先癸后丁，庚金佐之。"),
        ("癸水", "丁火", "午火炎烈，先润后暖。"),
        ("癸水", "丁火", "未月燥土养木，仍以癸丁并行为先。"),
        ("丁火", "庚金", "申月金旺伐木，丁火制金后取庚成材。"),
        ("丁火", "甲木", "酉月金强，宜丁制金、比助扶身。"),
        ("甲木", "庚金", "戌月燥土藏火，甲助根气，庚成器，癸可润燥。"),
        ("丁火", "戊土", "亥月寒水生木，先丁暖局，再戊止泛，甲可帮身。"),
        ("丁火", "庚金", "冬木寒冷，先丁后庚，甲木辅身。"),
        ("甲木", "庚金", "丑月寒湿土冻，先扶根，再以庚金成材，丁火解寒。"),
    ],
    "乙": [
        ("癸水", "丙火", "寅月藤萝得气，先癸滋藤，再丙照暖。"),
        ("丙火", "癸水", "卯月专旺，丙癸并用。"),
        ("癸水", "丙火", "辰月木郁土湿，可佐戊土培根。"),
        ("癸水", "丙火", "巳月火渐旺，先润后暖，可借戊土护水。"),
        ("癸水", "丙火", "午月燥烈，癸水为急，丙火次之。"),
        ("癸水", "丙火", "未月木气退而土燥，仍先润后暖。"),
        ("癸水", "丁火", "申月金旺伤乙，先癸护木，再丁制金。"),
        ("癸水", "丁火", "酉月金重，先水护柔木，再丁解寒。"),
        ("癸水", "辛金", "戌月燥土藏火，宜癸润、辛修，丁可辅暖。"),
        ("癸水", "戊土", "亥月寒湿，癸不离戊，重在培土制泛。"),
        ("丙火", "癸水", "子月寒水包木，丙火为先，癸水辅之。"),
        ("丙火", "癸水", "丑月冻土压木，丙癸并用，甲可劈土通根。"),
    ],
    "丙": [
        ("壬水", "庚金", "寅月丙火初生，壬水调候，庚金发源。"),
        ("壬水", "庚金", "卯月木火通明，仍要壬水节烈。"),
        ("壬水", "甲木", "辰月火渐升，壬甲并见最清。"),
        ("壬水", "庚金", "巳月火旺，壬水第一，庚癸可辅。"),
        ("壬水", "庚金", "午月烈火炎上，专取壬水济火。"),
        ("壬水", "庚金", "未月火土燥，壬先庚后，甲可疏土。"),
        ("壬水", "戊土", "申月金旺生火，壬水调候，戊土制水，丙可辅映。"),
        ("壬水", "甲木", "酉月金凉火衰，壬甲相济。"),
        ("壬水", "甲木", "戌月燥土晦火，壬润甲生。"),
        ("甲木", "戊土", "亥月火绝，专赖甲木生火，戊土制水，庚可佐。"),
        ("甲木", "戊土", "子月水寒火灭，先甲后戊。"),
        ("甲木", "戊土", "丑月湿寒晦火，甲戊并行，庚金可助发源。"),
    ],
    "丁": [
        ("甲木", "庚金", "寅月丁火柔生，甲木引燃，庚金劈甲。"),
        ("甲木", "庚金", "卯月木旺火相，甲庚并用。"),
        ("甲木", "庚金", "辰月湿土晦火，先甲引丁，再庚助发。"),
        ("甲木", "庚金", "巳月丁火通根，甲庚并用，癸水可济燥。"),
        ("甲木", "壬水", "午月火盛，甲木为源，壬水为济，庚金为辅。"),
        ("甲木", "壬水", "未月火余土燥，先甲后壬。"),
        ("甲木", "庚金", "申月财旺伤火，甲庚同取，丙火可帮。"),
        ("甲木", "庚金", "酉月金寒火弱，甲庚丙配合较佳。"),
        ("甲木", "庚金", "戌月燥土藏火，先甲后庚。"),
        ("庚金", "甲木", "亥月寒水灭灯，庚甲并行。"),
        ("庚金", "甲木", "子月专寒，仍取庚甲。"),
        ("甲木", "庚金", "丑月湿寒，甲庚为主，丙火可增暖。"),
    ],
    "戊": [
        ("甲木", "丙火", "寅月戊土疏松，甲木疏土，丙火温养，癸水润之。"),
        ("甲木", "丙火", "卯月官旺制身，甲丙癸三者并参。"),
        ("甲木", "丙火", "辰月土旺，甲木疏土最先，丙癸调燥湿。"),
        ("甲木", "癸水", "巳月火燥土焦，甲癸为先，丙火次之。"),
        ("壬水", "甲木", "午月燥土太过，壬甲最急。"),
        ("甲木", "丙火", "未月稼穑之土，甲丙癸相辅。"),
        ("丙火", "癸水", "申月金泄土气，丙暖癸润，甲可疏。"),
        ("丙火", "癸水", "酉月金寒土燥，丙癸并行。"),
        ("甲木", "丙火", "戌月燥土极重，甲丙癸缺一难灵。"),
        ("甲木", "丙火", "亥月土寒水泛，甲丙癸并看。"),
        ("丙火", "甲木", "子月冻土，先丙暖土，再甲疏土，癸可润。"),
        ("丙火", "甲木", "丑月寒湿重，丙甲为主。"),
    ],
    "己": [
        ("丙火", "癸水", "寅月湿土初开，丙暖癸润，甲可疏土。"),
        ("丙火", "癸水", "卯月官木旺，先丙后癸。"),
        ("丙火", "癸水", "辰月土湿泥重，丙癸甲并用。"),
        ("癸水", "丙火", "巳月土燥，先癸后丙。"),
        ("癸水", "丙火", "午月焦土，专赖癸水，丙火次之。"),
        ("癸水", "丙火", "未月燥湿夹杂，癸丙仍为主轴。"),
        ("丙火", "癸水", "申月土薄金寒，丙癸甲相参。"),
        ("丙火", "癸水", "酉月土泄于金，先丙后癸。"),
        ("甲木", "丙火", "戌月燥土结块，甲疏丙暖，癸可润。"),
        ("丙火", "甲木", "亥月湿寒，先丙，再甲，癸水酌用。"),
        ("丙火", "甲木", "子月冻土，丙火第一，甲木次之。"),
        ("丙火", "甲木", "丑月寒湿，仍主丙甲。"),
    ],
    "庚": [
        ("丁火", "甲木", "寅月金失令，丁火炼金，甲木为炉料。"),
        ("丁火", "甲木", "卯月财旺耗金，丁甲庚三者协调最佳。"),
        ("丁火", "甲木", "辰月湿土埋金，丁甲癸并用。"),
        ("壬水", "癸水", "巳月金逢长生，壬癸为先，丁火辅炼。"),
        ("壬水", "癸水", "午月火旺销金，专取壬癸。"),
        ("丁火", "甲木", "未月土燥埋金，丁甲并行。"),
        ("丁火", "甲木", "申月建禄太刚，丁火炼之，甲木疏达。"),
        ("丁火", "甲木", "酉月专旺，先丁后甲。"),
        ("甲木", "壬水", "戌月燥土脆金，甲木疏土，壬水润金。"),
        ("丁火", "甲木", "亥月寒金喜火，丁甲并见。"),
        ("丁火", "甲木", "子月寒金清冷，丁火为急。"),
        ("丁火", "甲木", "丑月湿寒埋金，仍取丁甲。"),
    ],
    "辛": [
        ("壬水", "己土", "寅月辛金嫩弱，壬水淘洗，己土生金。"),
        ("壬水", "甲木", "卯月财旺耗身，壬甲并参。"),
        ("壬水", "甲木", "辰月湿土晦金，壬甲最宜。"),
        ("壬水", "癸水", "巳月火炼辛金，壬癸甲可并看。"),
        ("壬水", "己土", "午月火烈，壬己癸并用。"),
        ("壬水", "甲木", "未月土燥，先壬后甲。"),
        ("壬水", "癸水", "申月金旺喜水淘洗。"),
        ("壬水", "甲木", "酉月建禄，壬水为先，甲木次之。"),
        ("壬水", "甲木", "戌月燥土埋珠，壬甲并行。"),
        ("壬水", "甲木", "亥月金寒水冷，仍取壬甲。"),
        ("丙火", "", "子月寒金水冷，专用丙火暖局。"),
        ("丙火", "", "丑月冻土藏金，亦以丙火为先。"),
    ],
    "壬": [
        ("庚金", "辛金", "寅月壬水泄气，庚辛生扶为先。"),
        ("庚金", "辛金", "卯月木旺泄水，仍重金源。"),
        ("甲木", "庚金", "辰月水库开源，甲庚辛并见为佳。"),
        ("辛金", "甲木", "巳月水绝火旺，辛甲庚并取。"),
        ("辛金", "壬水", "午月火炽，辛壬庚并用。"),
        ("辛金", "甲木", "未月土燥克水，辛甲庚共济。"),
        ("戊土", "丁火", "申月金水成势，戊丁制泛最先。"),
        ("甲木", "庚金", "酉月金多水浊，甲庚并用。"),
        ("甲木", "庚金", "戌月燥土耗水，甲庚为主。"),
        ("戊土", "甲木", "亥月旺水奔流，戊土立堤，甲木疏导。"),
        ("戊土", "丙火", "子月帝旺，先戊止水，再丙暖局。"),
        ("丙火", "甲木", "丑月寒湿，丙火暖水，甲木疏土。"),
    ],
    "癸": [
        ("辛金", "丙火", "寅月癸水尚弱，辛金发源，丙火调候。"),
        ("辛金", "庚金", "卯月木旺泄水，辛庚并取。"),
        ("丙火", "辛金", "辰月水库虽旺，丙辛甲相参。"),
        ("辛金", "", "巳月火旺水绝，专取辛金滋源。"),
        ("庚金", "辛金", "午月火烈，庚辛并用。"),
        ("辛金", "甲木", "未月土燥水微，辛甲相辅。"),
        ("丁火", "甲木", "申月金旺水清，丁甲可化秀。"),
        ("辛金", "", "酉月印旺，专取辛金清润。"),
        ("辛金", "甲木", "戌月燥土，辛甲并见较佳。"),
        ("庚金", "辛金", "亥月水旺仍喜金清源。"),
        ("丙火", "辛金", "子月寒水凝冰，丙火为先，辛金次之。"),
        ("丙火", "辛金", "丑月湿寒，丙辛甲并参。"),
    ],
}

SHENSHEN_COMBOS_RAW = [
    (["伤官", "正财"], "伤官生财", "才华转化为财富，适合靠输出与创意变现。", ["日主有根", "财星通门户"], ["枭神夺食", "比劫争财"], ["艺术家", "创业者", "自媒体"]),
    (["食神", "正财"], "食神生财", "温和稳定地产出价值，适合长期经营。", ["食神有力", "财星清纯"], ["偏印过旺", "财星被冲"], ["餐饮", "教育", "内容运营"]),
    (["七杀", "正印"], "杀印相生", "压力转化为权力与执行力，适合制度型岗位。", ["七杀有制", "印星通关"], ["财星坏印", "身弱无根"], ["管理者", "军警", "法务"]),
    (["正官", "正印"], "官印相生", "规则、资历、文凭互相成就，利仕途与专业晋升。", ["官印两停", "身不太弱"], ["伤官见官", "财星破印"], ["公务员", "教师", "研究员"]),
    (["食神", "七杀"], "食神制杀", "以技能与产出化解压力，适合技术型突破。", ["食神透出", "七杀不过旺"], ["枭神夺食", "财星泄食"], ["工程师", "顾问", "产品经理"]),
    (["伤官", "正官"], "伤官见官", "表达与权威冲突，处理得好可成破局者。", ["有印化伤", "财星通关"], ["官星孤露", "伤官太旺"], ["媒体人", "律师", "公关"]),
    (["比肩", "正财"], "比劫争财", "合作与竞争并存，资源容易被同类分走。", ["官星制比", "财星有库"], ["比劫成群", "财星独弱"], ["合伙创业", "销售", "渠道经营"]),
    (["劫财", "偏财"], "劫财夺财", "来财快去财也快，适合高流动资源场景。", ["官杀制劫", "食伤生财"], ["比劫混杂", "偏财无根"], ["贸易", "投融资", "项目制行业"]),
    (["正财", "正官"], "财官双美", "现实执行与规则意识并存，利稳定上升。", ["身能任财官", "印星不坏"], ["财多压身", "伤官破官"], ["企业管理", "金融", "行政"]),
    (["偏财", "七杀"], "财滋杀旺", "商业冲劲强，敢承担风险。", ["印星护身", "食神制杀"], ["身弱财杀重", "无印无比"], ["创业", "投资", "商业拓展"]),
    (["正印", "比肩"], "印比帮身", "学习力与自我支撑强，抗压性好。", ["身弱印比为喜", "官杀不过旺"], ["财星坏印", "比劫太重"], ["学术", "策划", "内控"]),
    (["偏印", "食神"], "枭神夺食", "灵感与稳定输出冲突，易时好时坏。", ["偏印受制", "财星泄枭"], ["偏印成群", "食神孤弱"], ["研究", "自由创作", "咨询"]),
    (["偏印", "七杀"], "枭杀并见", "警觉性强，思维偏锋，适合高压判断场景。", ["印能化杀", "身不太弱"], ["杀旺无制", "财来坏印"], ["风控", "刑侦", "安全行业"]),
    (["正印", "伤官"], "伤官佩印", "才华经由系统训练后可成名。", ["印足以化伤", "官星不坏"], ["财星坏印", "伤官太露"], ["写作", "设计", "培训"]),
    (["食神", "正印"], "食印相涵", "温润表达配合学习系统，适合知识服务。", ["印食流通", "财星不破"], ["枭印夺食", "比劫太重"], ["教师", "咨询师", "作者"]),
    (["伤官", "偏财"], "伤官生偏财", "偏商业化和流量变现能力强。", ["财星得地", "身强能任"], ["劫财夺财", "官杀混战"], ["营销", "直播", "品牌操盘"]),
    (["食神", "偏财"], "食神生偏财", "凭产品和口碑获取外财，宜慢热增长。", ["食神通关", "偏财不杂"], ["偏印夺食", "比劫分财"], ["餐饮", "IP经营", "服务业"]),
    (["七杀", "偏印"], "杀枭相生", "强压中出偏门技能，利非标准路径。", ["身有根", "财星不坏印"], ["枭多闭塞", "食神受伤"], ["医生", "玄学", "数据安全"]),
    (["正官", "正财"], "财生官", "资源推动身份与职责提升。", ["财官通根", "身旺"], ["伤官破官", "比劫夺财"], ["企业高管", "公务体系", "运营管理"]),
    (["偏财", "正官"], "财官相辅", "会经营也懂规则，适合对外型职位。", ["官星清", "偏财有制"], ["财多官弱", "比劫混局"], ["商务", "政商顾问", "渠道管理"]),
    (["比肩", "七杀"], "比杀并行", "执行强、竞争意识高。", ["印星化杀", "食神制杀"], ["七杀无制", "比劫太旺"], ["军警", "体育", "项目攻坚"]),
    (["劫财", "正官"], "劫官相战", "不服约束，宜在竞争中求规则。", ["印星缓冲", "财星通关"], ["伤官再透", "官星孤弱"], ["销售管理", "公关", "谈判"]),
    (["比肩", "偏印"], "比枭同见", "自我主张强，擅研究与独立作业。", ["食神有出路", "财星可疏印"], ["枭印闭塞", "比劫无制"], ["研究", "程序开发", "独立顾问"]),
    (["劫财", "偏印"], "劫枭并见", "资源竞争与非主流思维交织，人生起伏较大。", ["官杀可约束", "财星可疏导"], ["财星弱", "食神受伤"], ["创投", "咨询", "自由职业"]),
    (["正印", "正财"], "财印相碍", "现实资源与理想学习常互相拉扯。", ["官星协调", "身强可兼顾"], ["财多坏印", "印重碍财"], ["行政", "财会", "教培"]),
    (["偏印", "偏财"], "偏财坏印", "外部机会来时容易打断原有学习节奏。", ["官星护印", "食伤生财"], ["印为用而财旺", "身弱"], ["投资", "咨询", "自由市场"]),
    (["正官", "食神"], "食神生官", "温和表达服务规则与名位。", ["官星清纯", "食神不受制"], ["枭神夺食", "伤官混入"], ["教师", "培训", "公共表达"]),
    (["七杀", "伤官"], "伤官驾杀", "以锋芒驾驭压力，易走极端也易成名。", ["印星护身", "财星通关"], ["伤杀太过", "无印无根"], ["媒体", "创业", "竞技"]),
    (["正印", "七杀", "正官"], "官杀印并透", "体制压力大但上升通道也多。", ["印星有力", "官杀有序"], ["财星破印", "身弱不任"], ["公务", "大型组织", "法务"]),
    (["食神", "正财", "正官"], "食神生财生官", "产出变资源，资源再变身份。", ["流通顺畅", "日主有根"], ["比劫截财", "伤官破官"], ["企业主", "培训机构", "品牌主理人"]),
    (["伤官", "正财", "正官"], "伤官生财配官", "商业表达强，但必须处理规则边界。", ["财星通关", "印星辅佐"], ["伤官直接克官", "财弱无桥"], ["市场总监", "公关总监", "律师"]),
    (["七杀", "食神", "正印"], "杀印食三停", "能扛压、能输出、能学习，成事率高。", ["三神有序", "身有根气"], ["枭神夺食", "财星坏印"], ["顾问", "管理者", "技术负责人"]),
    (["偏财", "七杀", "正印"], "财杀印流通", "资源、压力、资历形成闭环。", ["印星真能化杀", "财不过重"], ["身弱财杀齐来", "印星被冲"], ["投资经理", "创业者", "项目负责人"]),
    (["正财", "正印", "比肩"], "财印比并见", "重稳定也重安全，易在组织内成长。", ["比印帮身", "财星有序"], ["财多压身", "比劫乱局"], ["会计", "人事", "运营"]),
    (["偏印", "伤官", "偏财"], "枭伤偏财", "灵感型变现强，但节奏起伏明显。", ["财星落地", "官星不扰"], ["枭印太重", "伤官无制"], ["内容创作", "策展", "顾问"]),
    (["食神", "偏财", "七杀"], "食神制杀生财", "靠专业能力拿下高压商业结果。", ["食神有力", "偏财可承"], ["七杀失控", "比劫争财"], ["销售管理", "项目制创业", "顾问"]),
    (["比肩", "食神"], "比食同流", "自我驱动下稳定输出，适合长期个人品牌。", ["财星承接", "官星不压"], ["偏印夺食", "比劫太多"], ["写作者", "设计师", "知识博主"]),
    (["劫财", "伤官"], "劫伤并见", "好胜心强、表达锋利。", ["印星能化", "官杀有度"], ["官星受损", "财星被夺"], ["销售", "辩论", "创业"]),
    (["正官", "偏印"], "官印偏杂", "有制度感也有另类思考。", ["官星清", "偏印不夺食"], ["伤官混入", "财星破印"], ["顾问", "策划", "法务"]),
    (["正财", "食神", "比肩"], "食财比三见", "既能生产价值又有执行落地力。", ["财星有源", "比肩不争"], ["劫财夺财", "偏印夺食"], ["电商", "产品经营", "手作品牌"]),
    (["伤官", "正印", "七杀"], "伤印杀并行", "适合难题处理与危机沟通。", ["印化伤杀", "身有根"], ["财星坏印", "伤杀无序"], ["公关危机", "律师", "调查类工作"]),
    (["七杀", "偏财", "劫财"], "财杀劫同来", "高风险高波动格局，适合快节奏竞争场。", ["印星救身", "食神制杀"], ["身弱无救", "财杀劫齐旺"], ["交易", "拓展", "创业"]),
    (["正官", "正财", "正印"], "财官印全", "传统意义上的稳定成就组合。", ["三者清纯", "身旺"], ["伤官破官", "财多坏印"], ["公务体系", "专业服务", "管理岗位"]),
    (["偏财", "食神", "正印"], "食财印相续", "能把知识、产品和商业连接起来。", ["印食顺生", "财不坏印"], ["比劫争财", "枭印夺食"], ["课程产品", "咨询", "文化产业"]),
    (["比肩", "正印", "食神"], "印比食流通", "内在稳定，外在有持续输出。", ["身弱得助", "财星可承接"], ["偏印夺食", "比劫过多"], ["教育", "写作", "咨询"]),
    (["劫财", "正财", "正官"], "劫财配官", "竞争中学会守规则，适合带团队。", ["官星得力", "财星不孤"], ["伤官破官", "劫财太旺"], ["销售主管", "渠道经理", "BD"]),
    (["偏印", "七杀", "伤官"], "枭杀伤组合", "反应快、带攻击性，利极端情境决策。", ["印可化杀", "财星疏枭"], ["食神受尽", "官星被冲"], ["风控", "舆情", "安防"]),
    (["正印", "正官", "食神"], "官印食三奇", "学识、身份、表达兼具。", ["三者顺序清", "身不弱"], ["伤官混局", "财星坏印"], ["教师", "演讲者", "顾问"]),
    (["伤官", "偏财", "七杀"], "伤财杀联动", "野心、资源、行动力三者并强。", ["印星护身", "财杀不过重"], ["伤官太露", "比劫夺财"], ["创业者", "投资人", "媒体经营"]),
    (["食神", "正印", "正官"], "食印官一体", "温和表达服务组织目标，适合公共型职业。", ["官印有序", "食神不受损"], ["偏印夺食", "伤官破官"], ["公职培训", "高校", "公共事务"]),
    (["比肩", "偏财", "食神"], "比财食并见", "靠个人品牌与产品化获得收入。", ["食神稳定", "偏财可守"], ["劫财争财", "偏印夺食"], ["个体经营", "咨询", "内容创业"]),
]

EN_KNOWLEDGE = [
    {
        "source_lang": "en",
        "source_type": "article",
        "source_url": "https://www.joeyyap.com/dl/Introduction/Introduction_Note.pdf",
        "topic": "Day Master 入门",
        "content_summary": "Joey Yap 将日主作为解读命盘的核心入口，强调先看日主属性、再看十神与运势如何作用。",
        "rules_extracted": ["分析英文 BaZi 教材时可先以 Day Master 对应日主作为第一索引。", "十神关系需要围绕日主展开，而不是孤立看单个元素。"],
        "terms_mapping": {"Day Master": "日主", "Ten Gods": "十神"},
        "school_perspective": "马来西亚派",
        "quality_score": 0.86,
    },
    {
        "source_lang": "en",
        "source_type": "book",
        "source_url": "https://www.iuniverse.com/en/bookstore/bookdetails/114369-four-pillars-of-destiny",
        "topic": "Jerry King 的四柱观",
        "content_summary": "Jerry King 将四柱视为可操作的人生导航系统，强调命盘、人生数字与易经结构之间的对应关系。",
        "rules_extracted": ["英文新派教材常把四柱视为趋势导航，而非绝对宿命。", "实际解读时会把命盘结构与决策建议直接绑定。"],
        "terms_mapping": {"Four Pillars of Destiny": "四柱八字"},
        "school_perspective": "新派",
        "quality_score": 0.7,
    },
    {
        "source_lang": "en",
        "source_type": "article",
        "source_url": "https://www.fengshuitoday.com/filestore/pdf/FST_Aug15_BaZi.pdf",
        "topic": "Jerry King 的英文教学框架",
        "content_summary": "资料把命盘解释与风水、时机判断结合，强调可执行建议与生活场景映射。",
        "rules_extracted": ["英文普及材料偏重把命理结论转换为生活策略。", "职业、关系、财富常被拆成独立模块讲解。"],
        "terms_mapping": {"Luck Pillar": "大运", "Wealth": "财"},
        "school_perspective": "新派",
        "quality_score": 0.66,
    },
    {
        "source_lang": "en",
        "source_type": "book",
        "source_url": "https://obnb.uk/p13033536-the-complete-guide-to-chinese-astrology-the-most-comprehensive-study-of-the-subject-ever-published-in-the-english-language",
        "topic": "Derek Walters 的中国占星综述",
        "content_summary": "Derek Walters 从更大的中国占星框架来讲四柱，重视天干地支、五行和传统象意的整体性。",
        "rules_extracted": ["英文传统派常把 BaZi 放在中国历法和五行系统的总框架下理解。", "术语翻译更偏传统，如 Heavenly Stems、Earthly Branches、Five Elements。"],
        "terms_mapping": {"Heavenly Stems": "天干", "Earthly Branches": "地支", "Five Elements": "五行"},
        "school_perspective": "传统派",
        "quality_score": 0.74,
    },
    {
        "source_lang": "en",
        "source_type": "forum",
        "source_url": "https://www.reddit.com/r/taoism/comments/1kxj75f",
        "topic": "Useful God 与命运可塑性",
        "content_summary": "帖子强调 Useful God 不只是判断好坏，而是帮助人顺势而为，认为 BaZi 展示的是潜能结构而非绝对命定。",
        "rules_extracted": ["英文社区常把 Useful God 解释为策略性平衡点。", "Luck Pillars 与 Annual Pillars 被视为动态互动层，不是宿命宣判。"],
        "terms_mapping": {"Useful God": "用神", "Luck Pillars": "大运", "Annual Pillars": "流年"},
        "school_perspective": "现代解释派",
        "quality_score": 0.62,
    },
    {
        "source_lang": "en",
        "source_type": "forum",
        "source_url": "https://www.reddit.com/r/ChineseZodiac/comments/1ke69lz",
        "topic": "Solar Time 校正",
        "content_summary": "用户反馈中反复强调真太阳时对排盘准确度的重要性，认为不校时的排盘会影响十神与用神判断。",
        "rules_extracted": ["英文用户对 Solar Time 的敏感度较高。", "涉及边界时辰时，应优先校正真太阳时再论十神。"],
        "terms_mapping": {"Solar Time": "真太阳时"},
        "school_perspective": "现代技术派",
        "quality_score": 0.65,
    },
    {
        "source_lang": "en",
        "source_type": "forum",
        "source_url": "https://www.reddit.com/r/ChineseZodiac/comments/1m4r27a",
        "topic": "Sidereal BaZi 讨论",
        "content_summary": "帖子主张四柱应回到天象基础，虽然观点争议大，但反映英文社区对历法基准与算法差异的持续讨论。",
        "rules_extracted": ["英文社区存在对算法基准的分歧。", "遇到英文资料时需标记其是否采用 sidereal 口径。"],
        "terms_mapping": {"Sidereal BaZi": "恒星历八字"},
        "school_perspective": "争议性新派",
        "quality_score": 0.4,
    },
    {
        "source_lang": "en",
        "source_type": "article",
        "source_url": "https://event.joeyyap.com/grwb",
        "topic": "BaZi 与财富、事业、关系应用",
        "content_summary": "Joey Yap 的课程页强调 BaZi 可直接用于财富、事业、关系策略，属于强应用导向的英文传播路径。",
        "rules_extracted": ["英文商业化教学常按财富、事业、关系分场景输出。", "应用导向资料更关注可执行建议而非古籍原句。"],
        "terms_mapping": {"Wealth": "财运", "Career": "事业", "Relationship": "关系"},
        "school_perspective": "马来西亚派",
        "quality_score": 0.68,
    },
]

JA_KNOWLEDGE = [
    {
        "source_lang": "ja",
        "source_type": "article",
        "source_url": "https://sup.andyou.jp/hoshi/shichusuimei-juniunsei/",
        "topic": "四柱推命与十二運星",
        "content_summary": "日文资料常把四柱推命拆解为命式、通変星、十二運等层次，强调读盘步骤的教学清晰度。",
        "rules_extracted": ["日文入门资料重视按步骤读取命式。", "十神通常以通変星体系来讲解。"],
        "terms_mapping": {"通変星": "十神", "命式": "命局"},
        "school_perspective": "日本教学派",
        "quality_score": 0.79,
    },
    {
        "source_lang": "ja",
        "source_type": "article",
        "source_url": "https://www.5pm-j.com/articles/7458",
        "topic": "四柱推命名人案例",
        "content_summary": "用日本名人命式做讲解，偏重把性格、职业与大运事件连起来说明。",
        "rules_extracted": ["日文案例文喜欢用名人命例做十神与职业对应。", "断语通常比中文古籍口径更生活化。"],
        "terms_mapping": {"有名人": "名人", "実例": "案例"},
        "school_perspective": "日本实务派",
        "quality_score": 0.72,
    },
    {
        "source_lang": "ja",
        "source_type": "article",
        "source_url": "https://8761234.jp/uranai/shichusuimei/",
        "topic": "四柱推命基础概念",
        "content_summary": "网站以大众传播口吻解释日干、五行、通変星和运势周期，适合术语映射。",
        "rules_extracted": ["日文大众资料常把日主称为日干。", "运势解读会同时讲年运与大运。"],
        "terms_mapping": {"日干": "日主", "五行": "五行"},
        "school_perspective": "日本大众派",
        "quality_score": 0.7,
    },
    {
        "source_lang": "ja",
        "source_type": "article",
        "source_url": "https://spicomi.net/media/articles/2111",
        "topic": "通変星解释",
        "content_summary": "集中讲通変星性格与职业象，对比肩、劫财、食神、傷官等词的日文对应较稳定。",
        "rules_extracted": ["日文语境中十神多按性格与职业双重维度讲述。", "比肩、劫財、食神、傷官等译名基本固定。"],
        "terms_mapping": {"比肩": "比肩", "劫財": "劫财", "傷官": "伤官"},
        "school_perspective": "日本教学派",
        "quality_score": 0.76,
    },
    {
        "source_lang": "ja",
        "source_type": "article",
        "source_url": "https://woman.mynavi.jp/article/230214-4/",
        "topic": "四柱推命性格与关系",
        "content_summary": "面向大众用户，重点解释恋爱、婚姻、工作倾向，反映日本内容市场的使用场景。",
        "rules_extracted": ["日文市场中四柱推命常与恋爱和适职结合。", "关系解读比中文古籍更强调心理体验。"],
        "terms_mapping": {"恋愛": "感情", "適職": "适职"},
        "school_perspective": "日本大众派",
        "quality_score": 0.64,
    },
    {
        "source_lang": "ja",
        "source_type": "article",
        "source_url": "https://note.com/mikoto_shichu/n/n9b7fe50b8c56",
        "topic": "四柱推命实例如名人分析",
        "content_summary": "独立作者用名人命式做推演，强调事件应期与命式结构的对应。",
        "rules_extracted": ["日文独立作者常用名人实例如事件验证。", "大运与年运的触发时点是案例文重点。"],
        "terms_mapping": {"大運": "大运", "年運": "流年"},
        "school_perspective": "日本实务派",
        "quality_score": 0.6,
    },
]

KO_KNOWLEDGE = [
    {
        "source_lang": "ko",
        "source_type": "article",
        "source_url": "https://namu.wiki/w/%EC%82%AC%EC%A3%BC",
        "topic": "사주 基础概念",
        "content_summary": "韩文资料通常把 사주、십성、용신、대운等术语直接纳入解释框架，重视基础概念定义。",
        "rules_extracted": ["韩文资料中 사주 常直接对应四柱命盘整体。", "용신 与 십성 是读盘核心术语。"],
        "terms_mapping": {"사주": "四柱八字", "용신": "用神", "십성": "十神"},
        "school_perspective": "韩国教学派",
        "quality_score": 0.73,
    },
    {
        "source_lang": "ko",
        "source_type": "article",
        "source_url": "https://www.joongang.co.kr/article/25152719",
        "topic": "사주 与 유명인 사례",
        "content_summary": "韩文媒体会用 유명인 命盘做趋势与性格分析，偏实务应用。",
        "rules_extracted": ["韩文案例常把名人职业转折与大运绑定。", "解释风格偏结论型、节奏快。"],
        "terms_mapping": {"유명인": "名人", "사주분석": "命盘分析"},
        "school_perspective": "韩国实务派",
        "quality_score": 0.67,
    },
    {
        "source_lang": "ko",
        "source_type": "article",
        "source_url": "https://m.blog.naver.com/PostView.naver?blogId=barunmyungri&logNo=223242215081",
        "topic": "십성 讲解",
        "content_summary": "Naver 博客类资料常系统整理 십성 的性格、职业与人际象意。",
        "rules_extracted": ["韩文十神资料非常重视性格与人际映射。", "比肩、劫财会按同辈竞争关系来解释。"],
        "terms_mapping": {"비견": "比肩", "겁재": "劫财"},
        "school_perspective": "韩国教学派",
        "quality_score": 0.69,
    },
    {
        "source_lang": "ko",
        "source_type": "article",
        "source_url": "https://m.blog.naver.com/PostView.naver?blogId=barunmyungri&logNo=223215948001",
        "topic": "용신 与 조후",
        "content_summary": "韩文命理写作会把 용신 和 조후 分开讲，说明结构用神与气候调节并非同义。",
        "rules_extracted": ["韩文资料常明确区分 용신 与 조후용신。", "调候在寒热偏极的命式中会被优先讨论。"],
        "terms_mapping": {"조후": "调候", "조후용신": "调候用神"},
        "school_perspective": "韩国实务派",
        "quality_score": 0.71,
    },
    {
        "source_lang": "ko",
        "source_type": "article",
        "source_url": "https://brunch.co.kr/@sajuclass/25",
        "topic": "대운 与 年度事件",
        "content_summary": "韩文文章常以大运、岁运并临、冲合刑害去解释工作和感情节点。",
        "rules_extracted": ["韩文案例重视大运与流年的同向叠加。", "冲合刑害常被直接关联到现实事件。"],
        "terms_mapping": {"대운": "大运", "세운": "流年"},
        "school_perspective": "韩国案例派",
        "quality_score": 0.68,
    },
    {
        "source_lang": "ko",
        "source_type": "article",
        "source_url": "https://contents.premium.naver.com/sajuclass/saju/contents/230915103012860dp",
        "topic": "유명인 사주분석",
        "content_summary": "以 유명인 命式做事例分析，结合职业节点和舆论事件验证命理结构。",
        "rules_extracted": ["韩文命理内容偏好真实公众人物案例。", "事业、名气、感情是最常见三类验证点。"],
        "terms_mapping": {"사주팔자": "生辰八字", "유명인": "名人"},
        "school_perspective": "韩国案例派",
        "quality_score": 0.63,
    },
]

TEN_GOD_TERM_MAP = [
    ("比肩", ["Companion Star", "Friend Star", "Peer Star"], ["比肩"], ["비견"], "与日主同五行同阴阳的天干"),
    ("劫财", ["Rob Wealth", "Robber Star", "Rival Star"], ["劫財"], ["겁재"], "与日主同五行异阴阳的天干"),
    ("食神", ["Eating God", "Output Star", "Food God"], ["食神"], ["식신"], "日主所生且同性之神"),
    ("伤官", ["Hurting Officer", "Output Star", "Expression Star"], ["傷官"], ["상관"], "日主所生且异性之神"),
    ("正财", ["Direct Wealth", "Proper Wealth"], ["正財"], ["정재"], "日主所克且异性之神"),
    ("偏财", ["Indirect Wealth", "Unexpected Wealth"], ["偏財"], ["편재"], "日主所克且同性之神"),
    ("正官", ["Direct Officer", "Proper Authority"], ["正官"], ["정관"], "克日主且异性之神"),
    ("七杀", ["Seven Killings", "Indirect Officer"], ["偏官", "七殺"], ["칠살", "편관"], "克日主且同性之神"),
    ("正印", ["Direct Resource", "Proper Seal"], ["印綬", "正印"], ["정인"], "生日主且异性之神"),
    ("偏印", ["Indirect Resource", "Indirect Seal"], ["偏印", "枭神"], ["편인"], "生日主且同性之神"),
]

WUXING_TERM_MAP = [
    ("木", ["Wood"], ["木"], ["목"], "五行之一，主生发"),
    ("火", ["Fire"], ["火"], ["화"], "五行之一，主炎上"),
    ("土", ["Earth"], ["土"], ["토"], "五行之一，主承载"),
    ("金", ["Metal"], ["金"], ["금"], "五行之一，主肃杀"),
    ("水", ["Water"], ["水"], ["수"], "五行之一，主流动"),
]

COMMON_PATTERN_TERM_MAP = [
    ("正官格", ["Direct Officer Structure"], ["正官格"], ["정관격"], "以正官为核心立格的格局"),
    ("七杀格", ["Seven Killings Structure"], ["七殺格"], ["칠살격"], "以七杀为核心立格的格局"),
    ("食神格", ["Eating God Structure"], ["食神格"], ["식신격"], "以食神为核心立格的格局"),
    ("伤官格", ["Hurting Officer Structure"], ["傷官格"], ["상관격"], "以伤官为核心立格的格局"),
    ("正财格", ["Direct Wealth Structure"], ["正財格"], ["정재격"], "以正财为核心立格的格局"),
    ("偏财格", ["Indirect Wealth Structure"], ["偏財格"], ["편재격"], "以偏财为核心立格的格局"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成八字知识图谱元数据")
    parser.add_argument(
        "--targets",
        nargs="+",
        choices=[
            "rule_fragments",
            "concept_relations",
            "term_aliases",
            "contradictions",
            "tiaohuo_table",
            "shenshen_combos",
            "dayun_rules",
            "multilang_knowledge_en",
            "multilang_knowledge_ja",
            "multilang_knowledge_ko",
            "term_mapping_multilang",
        ],
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


def build_tiaohuo_table() -> list[dict[str, str]]:
    table: list[dict[str, str]] = []
    for day_master, rows in TIAOHOU_RAW.items():
        for month_branch, (primary, secondary, notes) in zip(MONTH_BRANCHES, rows, strict=True):
            table.append(
                {
                    "day_master": day_master,
                    "month_branch": month_branch,
                    "season": SEASON_BY_BRANCH[month_branch],
                    "primary_yongshen": primary,
                    "secondary_yongshen": secondary,
                    "notes": notes,
                    "source": "穷通宝鉴",
                }
            )
    return table


def build_shenshen_combos() -> list[dict[str, Any]]:
    combos: list[dict[str, Any]] = []
    for index, (combination, pattern_name, interpretation, favorable, unfavorable, occupations) in enumerate(SHENSHEN_COMBOS_RAW, start=1):
        combos.append(
            {
                "combo_id": f"SG{index:03d}",
                "combination": combination,
                "pattern_name": pattern_name,
                "interpretation": interpretation,
                "favorable_conditions": favorable,
                "unfavorable_conditions": unfavorable,
                "typical_occupations": occupations,
                "famous_examples": [],
            }
        )
    return combos


def build_dayun_rules() -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []

    def add(trigger: str, effect: str, severity: str, mitigating: list[str], events: list[str]) -> None:
        rules.append(
            {
                "rule_id": f"DY{len(rules) + 1:03d}",
                "trigger": trigger,
                "effect": effect,
                "severity": severity,
                "mitigating_factors": mitigating,
                "typical_events": events,
            }
        )

    stem_attack_rules = [
        ("流年天干冲克日主", "压力年，事业或健康有波动", "high", ["有印星通关", "大运帮身"], ["换工作", "健康检查", "官非"]),
        ("流年天干生日主", "支援增加，学习和贵人机会变多", "medium", ["原局不过寒湿", "印星不过旺"], ["考证", "入职", "得到帮助"]),
        ("流年天干泄日主", "输出增加，适合曝光与创造，但体能消耗大", "medium", ["有印星回补", "财星能承接"], ["发布作品", "频繁出差", "项目交付"]),
        ("流年天干合日主", "关系与合作议题上升，容易出现绑定关系", "medium", ["合化成喜神", "官印协调"], ["签约", "合作", "感情推进"]),
        ("大运天干克日主", "十年主旋律偏压制，需稳结构再谈扩张", "high", ["地支有根", "流年帮身"], ["岗位压力", "家庭责任", "慢性疲劳"]),
        ("大运天干生日主", "十年整体恢复和积累能力增强", "medium", ["原局需要扶助", "财官不过旺"], ["学习深造", "积累资源", "回归稳定"]),
    ]
    for item in stem_attack_rules:
        add(*item)

    for branch_a, _, branch_b, _, implication in CHONG_RELATIONS:
        add(
            f"流年地支{branch_a}冲命局{branch_b}",
            f"{implication}，应事速度快。",
            "high",
            ["天干有合化缓冲", "大运同党护盘"],
            ["搬家", "跳槽", "关系变化"],
        )
        add(
            f"大运地支{branch_a}冲命局{branch_b}",
            f"{implication}，十年主旋律会明显重组。",
            "high",
            ["原局有三合局化解", "喜神被引动"],
            ["迁居", "行业切换", "家庭结构变化"],
        )

    for branch_a, _, branch_b, _, implication in HE_RELATIONS[:6]:
        add(
            f"流年地支{branch_a}合命局{branch_b}",
            f"{implication}，资源和关系容易聚拢。",
            "medium",
            ["合而不化也可取缓和之象", "忌神不被引动"],
            ["合作", "恋爱", "签约"],
        )
        add(
            f"大运地支{branch_a}合命局{branch_b}",
            f"{implication}，长期进入绑定、合作或稳态阶段。",
            "medium",
            ["合神为喜", "原局不逢冲破"],
            ["结婚", "长期合伙", "定居"],
        )

    for branch_a, _, branch_b, _, implication in XING_RELATIONS[:6]:
        add(
            f"流年地支{branch_a}刑命局{branch_b}",
            f"{implication}，更偏内耗、纠结或制度摩擦。",
            "medium",
            ["有合可缓", "印星能稳心神"],
            ["合同纠纷", "关系僵持", "反复决策"]),
        add(
            f"大运地支{branch_a}刑命局{branch_b}",
            f"{implication}，容易形成长期心理或责任压力。",
            "medium",
            ["食伤有出口", "喜神到位"],
            ["慢性压力", "家庭摩擦", "组织博弈"],
        )

    ten_god_rules = [
        ("流年引动正财", "收入、现金流和伴侣议题上升", "medium", ["比劫不重", "官星护财"], ["加薪", "恋爱", "购置资产"]),
        ("流年引动偏财", "机会财与人脉财增强，但波动也更大", "medium", ["身强能任", "官杀制比"], ["副业", "投资", "商务机会"]),
        ("流年引动正官", "规则、职位、责任感变强", "medium", ["伤官不见官", "印星协同"], ["升职", "考试", "被监管"]),
        ("流年引动七杀", "压力、竞争、行动力同时上升", "high", ["有印化杀", "食神制杀"], ["竞聘", "冲刺项目", "外部冲突"]),
        ("流年引动正印", "学习、证照、贵人、恢复力增强", "low", ["财星不过旺", "印不闭塞"], ["进修", "遇导师", "身体恢复"]),
        ("流年引动偏印", "灵感增强但节奏不稳，易转向冷门方向", "medium", ["食神有出口", "财星可疏印"], ["研究", "转岗", "突然改变兴趣"]),
        ("流年引动食神", "表达、输出、产品化能力增强", "low", ["财星承接", "偏印不夺食"], ["创作", "演讲", "生意增长"]),
        ("流年引动伤官", "锋芒外放，适合突破但易顶撞规则", "medium", ["印星约束", "财星通关"], ["换赛道", "爆红", "争执"]),
        ("流年引动比肩", "自我意识和独立行动增强", "medium", ["官星制比", "财星有库"], ["创业", "单干", "团队分工变化"]),
        ("流年引动劫财", "竞争者增加，钱财与关系都易波动", "high", ["官杀制劫", "财星根深"], ["分利", "抢项目", "合作拆分"]),
    ]
    for item in ten_god_rules:
        add(*item)

    extra_rules = [
        ("岁运并临", "同一干支重复引动，事件集中且幅度放大", "high", ["原局喜用被引动", "有合化缓冲"], ["大事决断", "搬迁", "婚育"]),
        ("大运与流年同来帮身", "阶段性底盘变稳，适合扩张和积累", "medium", ["原局确实偏弱", "财官不过重"], ["创业起步", "升学", "复苏"]),
        ("大运与流年同来克身", "压力叠加，需保守行事", "high", ["印比到位", "宫位未被冲坏"], ["裁员", "病痛", "现金流紧张"]),
        ("流年冲夫妻宫", "婚恋和合作关系明显波动", "high", ["合星同至", "财官为喜"], ["分手", "结婚", "伴侣换工作"]),
        ("流年冲财库", "资产、储蓄、地产议题被打开", "medium", ["财星为喜", "有官星护财"], ["购房", "还债", "资金周转"]),
        ("流年冲官禄位", "职业方向调整，岗位职责变化", "medium", ["印星稳定", "命局不见多冲"], ["转岗", "被调动", "升降职"]),
        ("流年与命局成三合局", "某一五行之事被集中放大", "medium", ["合局成喜神", "不过度偏枯"], ["结盟", "资源整合", "迁居"]),
        ("流年与命局成三会局", "环境整体换气，阶段感强", "high", ["会局为喜", "原局有承载"], ["换城市", "行业转场", "团队重组"]),
        ("忌神在大运得令", "问题不一定立刻爆发，但十年主题会围绕其展开", "high", ["流年有喜神抵消", "原局本身稳定"], ["慢性消耗", "长期责任", "隐性压力"]),
        ("喜神在大运得令", "十年主旋律顺势，容易获得放大器", "medium", ["原局不失衡", "流年不过度冲破"], ["发展机会", "名气提升", "家庭改善"]),
    ]
    for item in extra_rules:
        add(*item)

    return rules


def build_multilang_knowledge_en() -> list[dict[str, Any]]:
    return EN_KNOWLEDGE


def build_multilang_knowledge_ja() -> list[dict[str, Any]]:
    return JA_KNOWLEDGE


def build_multilang_knowledge_ko() -> list[dict[str, Any]]:
    return KO_KNOWLEDGE


def build_term_mapping_multilang() -> list[dict[str, Any]]:
    mapping: list[dict[str, Any]] = []
    for zh, en, ja, ko, definition in TEN_GOD_TERM_MAP + WUXING_TERM_MAP + COMMON_PATTERN_TERM_MAP:
        mapping.append({"zh": zh, "en": en, "ja": ja, "ko": ko, "definition": definition})
    for stem, _, _ in STEMS:
        mapping.append({"zh": stem, "en": [f"{stem} Heavenly Stem"], "ja": [stem], "ko": [stem], "definition": f"十天干之一：{stem}"})
    for branch, _, _ in BRANCHES:
        mapping.append({"zh": branch, "en": [f"{branch} Earthly Branch"], "ja": [branch], "ko": [branch], "definition": f"十二地支之一：{branch}"})
    return mapping


def main() -> None:
    args = parse_args()
    knowledge_path = detect_knowledge_path()
    _ = knowledge_path.read_text(encoding="utf-8")

    builders = {
        "rule_fragments": build_rule_fragments,
        "concept_relations": build_concept_relations,
        "term_aliases": build_term_aliases,
        "contradictions": build_contradictions,
        "tiaohuo_table": build_tiaohuo_table,
        "shenshen_combos": build_shenshen_combos,
        "dayun_rules": build_dayun_rules,
        "multilang_knowledge_en": build_multilang_knowledge_en,
        "multilang_knowledge_ja": build_multilang_knowledge_ja,
        "multilang_knowledge_ko": build_multilang_knowledge_ko,
        "term_mapping_multilang": build_term_mapping_multilang,
    }

    for target in args.targets:
        payload = builders[target]()
        write_json(args.metadata_dir / f"{target}.json", payload)
        print(f"{target}={len(payload)}")


if __name__ == "__main__":
    main()
