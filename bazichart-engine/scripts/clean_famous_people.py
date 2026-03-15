#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "data"
INPUT_PATH = DATA_DIR / "famous_people.json"
OUTPUT_PATH = DATA_DIR / "famous_people.json"
DAY_PILLAR_INDEX_PATH = DATA_DIR / "day_pillar_index.json"
DELETED_REPORT_PATH = DATA_DIR / "deleted_report.json"
REVIEW_LIST_PATH = DATA_DIR / "review_list.json"
CRAWL_SCRIPT_PATH = SCRIPT_DIR / "crawl_famous_people.py"

SPEC = importlib.util.spec_from_file_location("crawl_famous_people_cleaner", CRAWL_SCRIPT_PATH)
CRAWL_MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["crawl_famous_people_cleaner"] = CRAWL_MODULE
SPEC.loader.exec_module(CRAWL_MODULE)


STRICT_BLACKLIST = [
    {
        "category": "战争与暴力",
        "reason": "二战战犯或侵华战争相关核心人物",
        "aliases": [
            "阿道夫·希特勒", "Adolf Hitler",
            "赫尔曼·戈林", "Hermann Göring", "Hermann Goring",
            "约瑟夫·戈培尔", "約瑟夫·戈培爾", "Joseph Goebbels",
            "海因里希·希姆莱", "Heinrich Himmler",
            "阿道夫·艾希曼", "Adolf Eichmann",
            "本尼托·墨索里尼", "Benito Mussolini",
            "东条英机", "東條英機", "Hideki Tojo", "Hideki Tōjō",
            "广田弘毅", "Koki Hirota", "Kōki Hirota",
            "土肥原贤二", "土肥原賢二", "Kenji Doihara",
            "松井石根", "Iwane Matsui",
            "板垣征四郎", "板垣征四郎", "Seishiro Itagaki", "Seishirō Itagaki",
            "木村兵太郎", "Heitaro Kimura", "Heitarō Kimura",
            "梅津美治郎", "Yoshijiro Umezu", "Yoshijirō Umezu",
            "武藤章", "Akira Muto",
            "寺内寿一", "Hisaichi Terauchi",
            "伊藤博文", "Ito Hirobumi", "Itō Hirobumi",
            "汪精卫", "Wang Jingwei",
            "阿尔弗雷德·冯·瓦德西", "Alfred von Waldersee",
            "额尔金伯爵", "James Bruce, 8th Earl of Elgin",
        ],
    },
    {
        "category": "战争与暴力",
        "reason": "恐怖组织头目、种族灭绝实施者或大规模暴力实施者",
        "aliases": [
            "奥萨马·本·拉登", "本·拉登", "Osama bin Laden",
            "阿布·巴克尔·巴格达迪", "阿布·贝克尔·巴格达迪", "Abu Bakr al-Baghdadi",
            "艾曼·扎瓦希里", "Ayman al-Zawahiri",
            "拉多万·卡拉季奇", "Radovan Karadžić", "Radovan Karadzic",
            "拉特科·姆拉迪奇", "Ratko Mladić", "Ratko Mladic",
            "波尔布特", "Pol Pot",
            "萨达姆·侯赛因", "Saddam Hussein",
        ],
    },
    {
        "category": "政治敏感",
        "reason": "分裂主义、反华制裁、叛逃或间谍相关人物",
        "aliases": [
            "第十四世达赖喇嘛", "第十四世達賴喇嘛", "Tenzin Gyatso", "Dalai Lama",
            "热比娅", "熱比婭", "Rebiya Kadeer",
            "黄之锋", "黃之鋒", "Joshua Wong",
            "柴玲", "Chai Ling",
            "刘晓波", "劉曉波", "Liu Xiaobo",
            "史明", "Su Beng",
            "朴延美", "Park Yeon-mi",
            "马英九", "馬英九", "Ma Ying-jeou",
            "李登辉", "李登輝", "Lee Teng-hui",
            "蔡英文", "Tsai Ing-wen",
            "蓬佩奥", "Mike Pompeo",
            "博尔顿", "John Bolton",
            "斯诺登", "Edward Snowden",
            "安娜·查普曼", "Anna Chapman",
            "亚历山大·利特维年科", "亞歷山大·利特維年科", "Alexander Litvinenko",
        ],
    },
    {
        "category": "犯罪类",
        "reason": "重大诈骗、毒枭、黑帮或性犯罪相关人物",
        "aliases": [
            "伯纳德·麦道夫", "Bernard Madoff",
            "巴勃罗·埃斯科巴", "Pablo Escobar",
            "华金·古斯曼", "Joaquín Guzmán", "Joaquin Guzman", "El Chapo",
            "约翰·高蒂", "John Gotti",
            "哈维·韦恩斯坦", "Harvey Weinstein",
            "杰弗里·爱泼斯坦", "Jeffrey Epstein",
        ],
    },
    {
        "category": "邪教与极端",
        "reason": "邪教、极端宗教、军火或奴隶贸易相关人物",
        "aliases": [
            "麻原彰晃", "Shoko Asahara", "Shōkō Asahara",
            "吉姆·琼斯", "Jim Jones",
            "查尔斯·曼森", "Charles Manson",
            "大卫·考雷什", "David Koresh",
            "大卫·伯格", "David Berg",
            "李洪志", "Li Hongzhi",
            "洪秀全", "Hong Xiuquan",
            "奥姆真理教", "Aum Shinrikyo",
            "Sun Myung Moon", "文鲜明", "文鮮明",
            "维克托·布特", "Viktor Bout",
            "塞西尔·罗得斯", "Cecil Rhodes",
        ],
    },
    {
        "category": "心理不适",
        "reason": "连环杀手、大规模枪击案凶手或负面心理暗示极强人物",
        "aliases": [
            "泰德·邦迪", "Ted Bundy",
            "杰弗里·达默", "Jeffrey Dahmer",
            "约翰·韦恩·盖西", "John Wayne Gacy",
            "理查德·拉米雷斯", "Richard Ramirez",
            "安德烈·契卡提罗", "Andrei Chikatilo",
            "埃里克·哈里斯", "Eric Harris",
            "迪伦·克莱伯德", "Dylan Klebold",
        ],
    },
]

DELETE_PATTERNS = [
    ("战争与暴力", "命中战争/恐怖/屠杀关键词", [
        r"战犯", r"纳粹", r"nazi", r"terrorist", r"terrorism", r"恐怖分子", r"恐怖组织",
        r"genocide", r"种族灭绝", r"massacre", r"大屠杀", r"war criminal", r"甲级战犯",
        r"侵华", r"南京大屠杀", r"新纳粹", r"neo-?nazi",
    ]),
    ("政治敏感", "命中分裂/间谍/制裁关键词", [
        r"台独", r"港独", r"藏独", r"疆独", r"分裂主义", r"separatist",
        r"叛逃", r"defector", r"sanction", r"制裁", r"3k党", r"kkk", r"white supremacist", r"种族主义者",
        r"human rights activist", r"人权活动家", r"民主运动", r"异议人士", r"dissident",
        r"\bspy\b", r"间谍", r"intelligence officer", r"西藏精神领袖", r"民运人士", r"自治", r"抗议领袖",
    ]),
    ("犯罪类", "命中严重犯罪关键词", [
        r"serial killer", r"连环杀手", r"mass shooter", r"枪击案凶手", r"ponzi", r"庞氏骗局",
        r"fraudster", r"诈骗犯", r"drug lord", r"毒枭", r"mafia boss", r"黑帮头目",
        r"sex offender", r"sexual predator", r"性犯罪", r"pedophile", r"恋童", r"强奸犯",
    ]),
    ("邪教与极端", "命中邪教/军火/奴隶贸易关键词", [
        r"cult leader", r"cult founder", r"邪教", r"邪教教主", r"邪教创始人", r"extremist", r"极端主义", r"极端宗教",
        r"doomsday cult", r"religious extremist", r"terror guru", r"cult", r"奥姆真理教",
        r"法轮功", r"统一教", r"太平天国", r"arms dealer", r"军火商",
        r"slave trader", r"奴隶贩子", r"colonialist", r"殖民者",
    ]),
    ("心理不适", "命中心理不适高风险关键词", [
        r"suicide", r"自杀", r"mass murderer", r"大规模谋杀", r"school shooting", r"校园枪击",
        r"mental illness", r"精神疾病", r"精神分裂", r"躁郁症",
    ]),
]

REVIEW_PATTERNS = [
    ("心理不适", "疑似自杀、意外死亡或早逝，需人工复核", [
        r"自杀身亡", r"自殺身亡", r"died by suicide", r"killed in", r"died in", r"意外身亡",
        r"空难", r"枪杀", r"刺杀", r"assassinated", r"air crash", r"plane crash", r"accident",
    ]),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="全面清洗名人数据库敏感人物")
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--index-output", type=Path, default=DAY_PILLAR_INDEX_PATH)
    parser.add_argument("--deleted-report", type=Path, default=DELETED_REPORT_PATH)
    parser.add_argument("--review-output", type=Path, default=REVIEW_LIST_PATH)
    return parser.parse_args()


def normalize_text(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.strip().lower())


def compile_strict_aliases() -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for entry in STRICT_BLACKLIST:
        for alias in entry["aliases"]:
            index[normalize_text(alias)] = {"category": entry["category"], "reason": entry["reason"]}
    return index


def build_search_text(person: dict[str, Any]) -> str:
    values = [
        person.get("name_zh", ""),
        person.get("name_en", ""),
        person.get("name_zh_hans", ""),
        person.get("name_zh_hant", ""),
        person.get("summary", ""),
        person.get("bio_zh_hans", ""),
        person.get("bio_zh_hant", ""),
        person.get("bio_en", ""),
        person.get("field_zh", ""),
        person.get("field_en", ""),
        " ".join(person.get("occupation", [])),
        " ".join(person.get("occupation_en", [])),
    ]
    return " | ".join(item for item in values if item)


def detect_early_death(person: dict[str, Any], search_text: str) -> dict[str, str] | None:
    birth_date = person.get("birth_date", "")
    match = re.search(r"(18|19|20)\d{2}\s*[—–-]\s*((18|19|20)\d{2})", search_text)
    if not birth_date or not match:
        return None
    birth_year = int(birth_date[:4])
    death_year = int(match.group(2))
    age = death_year - birth_year
    lowered = search_text.lower()
    accidental_keywords = ["accident", "空难", "意外", "坠机", "车祸", "枪杀", "assassinated", "killed in", "died in"]
    if "suicide" in lowered or "自杀" in search_text or "自殺" in search_text:
        return {"category": "心理不适", "reason": f"检测到自杀相关描述，死亡年龄约 {age} 岁"}
    if age < 30 and any(keyword in lowered or keyword in search_text for keyword in accidental_keywords):
        return {"category": "心理不适", "reason": f"检测到 30 岁以下意外死亡描述，死亡年龄约 {age} 岁"}
    return None


def detect_by_patterns(search_text: str, patterns: list[tuple[str, str, list[str]]]) -> dict[str, str] | None:
    lowered = search_text.lower()
    for category, reason, rule_patterns in patterns:
        for pattern in rule_patterns:
            if re.search(pattern, search_text, re.IGNORECASE) or re.search(pattern, lowered, re.IGNORECASE):
                return {"category": category, "reason": f"{reason}: {pattern}"}
    return None


def evaluate_person(person: dict[str, Any], strict_aliases: dict[str, dict[str, str]]) -> tuple[str, dict[str, str] | None]:
    for field in ["name_zh", "name_en", "name_zh_hans", "name_zh_hant"]:
        normalized = normalize_text(person.get(field, ""))
        if normalized and normalized in strict_aliases:
            return "delete", strict_aliases[normalized]

    search_text = build_search_text(person)
    early_death = detect_early_death(person, search_text)
    if early_death is not None:
        return "delete", early_death

    delete_match = detect_by_patterns(search_text, DELETE_PATTERNS)
    if delete_match is not None:
        return "delete", delete_match

    review_match = detect_by_patterns(search_text, REVIEW_PATTERNS)
    if review_match is not None:
        return "delete", {
            "category": review_match["category"],
            "reason": f"疑似即删除: {review_match['reason']}",
        }

    return "keep", None


def build_result_item(person: dict[str, Any], matched: dict[str, str]) -> dict[str, Any]:
    return {
        "id": person.get("id", ""),
        "name_zh": person.get("name_zh", ""),
        "name_en": person.get("name_en", ""),
        "birth_date": person.get("birth_date", ""),
        "category": matched["category"],
        "reason": matched["reason"],
    }


def clean_people(people: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    strict_aliases = compile_strict_aliases()
    kept: list[dict[str, Any]] = []
    deleted: list[dict[str, Any]] = []
    for person in people:
        decision, matched = evaluate_person(person, strict_aliases)
        if decision == "delete" and matched is not None:
            deleted.append(build_result_item(person, matched))
            continue
        kept.append(person)
    return kept, deleted, []


def build_summary(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    return counts


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    people = json.loads(args.input.read_text(encoding="utf-8"))
    cleaned, deleted, review = clean_people(people)
    write_json(args.output, cleaned)
    write_json(args.index_output, CRAWL_MODULE.build_day_pillar_index(cleaned))
    write_json(
        args.deleted_report,
        {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "before_count": len(people),
            "after_count": len(cleaned),
            "deleted_count": len(deleted),
            "deleted_by_category": build_summary(deleted),
            "deleted_people": deleted,
        },
    )
    write_json(
        args.review_output,
        {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "review_count": 0,
            "review_by_category": {},
            "review_people": [],
        },
    )
    print(f"清洗前人数：{len(people)}")
    print(f"删除人数：{len(deleted)}")
    print(f"复核人数：{len(review)}")
    print(f"清洗后人数：{len(cleaned)}")
    print(f"删除报告：{args.deleted_report}")
    print(f"复核列表：{args.review_output}")
    print(f"日柱索引：{args.index_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
