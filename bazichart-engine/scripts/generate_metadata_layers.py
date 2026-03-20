#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "data"
DEFAULT_PEOPLE = DATA_DIR / "famous_people.json"
DEFAULT_METADATA_DIR = DATA_DIR / "metadata"
DEFAULT_BAZI_KNOWLEDGE = Path.home() / ".openclaw" / "agents" / "main" / "agent" / "knowledge" / "BAZI.md"

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
USEFUL_GOD_RULES = [
    ("身强", "宜取泄耗克制之神"),
    ("身弱", "宜取生扶助身之神"),
    ("两神相战", "宜取通关之神"),
    ("冬季寒局", "宜用火调候"),
    ("夏季热局", "宜用水调候"),
]
FORTUNE_RULES = [
    ("大运每十年一变", "看人生阶段主旋律"),
    ("流年与命局形成刑冲合害", "常为事件应期"),
    ("大运流年与命局成三合三会", "多主大事发生"),
]
KINSHIP_RULES = [
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
JUDGMENT_RULES = [
    ("看婚姻", "男看财星，女看官星，并结合日支夫妻宫"),
    ("看财运", "看财星旺衰及大运流年是否走财运"),
    ("看事业", "看官杀与印星，并结合月柱事业宫"),
    ("看健康", "看五行偏枯及受克五行所主器官"),
]

ELEMENT_RELATIONS = [
    ("木", "生", "火"),
    ("火", "生", "土"),
    ("土", "生", "金"),
    ("金", "生", "水"),
    ("水", "生", "木"),
    ("木", "克", "土"),
    ("土", "克", "水"),
    ("水", "克", "火"),
    ("火", "克", "金"),
    ("金", "克", "木"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成八字元数据层 JSON 文件")
    parser.add_argument("--people", type=Path, default=DEFAULT_PEOPLE)
    parser.add_argument("--metadata-dir", type=Path, default=DEFAULT_METADATA_DIR)
    parser.add_argument("--knowledge", type=Path, default=DEFAULT_BAZI_KNOWLEDGE)
    return parser.parse_args()


def load_people(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"{path} 不是名人列表")
    return payload


def build_rule_fragments() -> list[dict[str, Any]]:
    fragments: list[dict[str, Any]] = []
    index = 1

    def add_fragment(source: str, category: str, condition: str, conclusion: str, confidence: str = "medium", exceptions: list[str] | None = None) -> None:
        nonlocal index
        fragments.append(
            {
                "rule_id": f"RF{index:03d}",
                "source": source,
                "category": category,
                "condition": condition,
                "conclusion": conclusion,
                "exceptions": exceptions or [],
                "confidence": confidence,
                "contradicts": [],
            }
        )
        index += 1

    for stem, yinyang, element in STEMS:
        add_fragment("韩立知识库", "基础", f"命局出现天干{stem}", f"{stem}属{yinyang}干，五行为{element}", "high")
        add_fragment("韩立知识库", "基础", f"分析日主为{stem}", f"先按{element}性与{yinyang}属性入手判断强弱与取用", "medium")

    for branch, element, hidden_stems in BRANCHES:
        add_fragment("韩立知识库", "基础", f"命局出现地支{branch}", f"{branch}主五行为{element}", "high")
        add_fragment("韩立知识库", "基础", f"分析地支{branch}", f"{branch}藏干为{'、'.join(hidden_stems)}", "high")

    for relation, polarity, god in TEN_GODS_DEFINITIONS:
        add_fragment("韩立知识库", "十神", f"以日主为中心，{relation}且为{polarity}", f"十神取{god}", "high")

    for god, trait in TEN_GODS_TRAITS:
        add_fragment("韩立知识库", "十神", f"命局{god}明显", f"多见{trait}", "medium")

    add_fragment("韩立知识库", "格局", "判格时先看月令", "月支藏干透出天干者可作为格局判断重点", "high")
    for pattern in COMMON_PATTERNS:
        add_fragment("韩立知识库", "格局", f"月令透出符合{pattern}条件", f"可按{pattern}立格", "medium")
    for pattern in SPECIAL_PATTERNS:
        add_fragment("韩立知识库", "格局", f"命局整体趋向{pattern}", f"按特殊格局{pattern}处理，不再完全沿普通扶抑法", "medium")

    for condition, conclusion in USEFUL_GOD_RULES:
        category = "调候" if "冬季" in condition or "夏季" in condition else "用神"
        add_fragment("韩立知识库", category, condition, conclusion, "high" if category == "用神" else "medium")

    for condition, conclusion in FORTUNE_RULES:
        add_fragment("韩立知识库", "断事", condition, conclusion, "medium")

    for condition, conclusion in KINSHIP_RULES:
        add_fragment("韩立知识库", "六亲", condition, conclusion, "medium")

    for condition, conclusion in JUDGMENT_RULES:
        add_fragment("韩立知识库", "断事", condition, conclusion, "high")

    return fragments


def build_concept_relations() -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []

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

    for source, relation, target in ELEMENT_RELATIONS:
        add(source, relation, target, "五行生克", f"{source}{relation}{target}影响命局平衡")

    add("伤官", "生", "财星", "伤官生财格", "聪明才智可转化为财富")
    add("正官", "喜", "印绶", "官印相生", "规范与资源相互扶持")
    add("七杀", "喜", "印星", "杀印相生", "压力可转化为权力与执行力")
    add("食神", "制", "七杀", "食神制杀", "缓冲压力并化攻击性为产出")
    add("财星", "助", "官星", "财生官", "资源可推动名位与责任")
    add("比肩", "争", "财星", "比劫争财", "同类竞争会分走资源")
    add("木", "对应", "仁", "五行取象", "木旺多主生发与仁性")
    add("火", "对应", "礼", "五行取象", "火旺多主表达与礼仪")
    add("土", "对应", "信", "五行取象", "土旺多主承载与守信")
    add("金", "对应", "义", "五行取象", "金旺多主规则与决断")
    add("水", "对应", "智", "五行取象", "水旺多主思维与流动")

    return relations


def infer_event_type(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("结婚", "婚", "marriage", "married")):
        return "marriage"
    if any(token in lowered for token in ("病", "health", "diagnosed", "康复")):
        return "health"
    if any(token in lowered for token in ("去世", "逝世", "death", "died")):
        return "death"
    if any(token in lowered for token in ("上市", "融资", "财富", "billion", "wealth")):
        return "wealth"
    if any(token in lowered for token in ("转型", "辞职", "加入", "change", "switch")):
        return "career_change"
    return "career_peak"


def build_case_event_links(people: list[dict[str, Any]]) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    for person in people:
        if not person.get("has_birth_hour"):
            continue
        notable_events = person.get("notable_events")
        if not isinstance(notable_events, list) or not notable_events:
            continue
        for event in notable_events[:3]:
            if isinstance(event, dict):
                event_year = event.get("year")
                event_text = event.get("event") or event.get("description") or ""
            else:
                event_year = None
                event_text = str(event)
            if not event_text:
                continue
            links.append(
                {
                    "person_id": person.get("id"),
                    "event": event_text,
                    "event_year": event_year,
                    "event_type": infer_event_type(event_text),
                    "bazi_correlation": {
                        "da_yun": None,
                        "liu_nian": f"{event_year}年流年" if event_year else None,
                        "interaction": "待补充：需结合完整四柱与大运排盘计算",
                    },
                }
            )
            if len(links) >= 100:
                return links
    return links


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main() -> None:
    args = parse_args()
    _ = args.knowledge.read_text(encoding="utf-8")
    people = load_people(args.people)

    rule_fragments = build_rule_fragments()
    concept_relations = build_concept_relations()
    case_event_links = build_case_event_links(people)

    write_json(args.metadata_dir / "rule_fragments.json", rule_fragments)
    write_json(args.metadata_dir / "concept_relations.json", concept_relations)
    write_json(args.metadata_dir / "case_event_links.json", case_event_links)

    print(f"rule_fragments={len(rule_fragments)}")
    print(f"concept_relations={len(concept_relations)}")
    print(f"case_event_links={len(case_event_links)}")


if __name__ == "__main__":
    main()
