#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import requests
from lunar_python import Solar
from opencc import OpenCC
from requests import RequestException


WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
EN_WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
ZH_WIKIPEDIA_API_URL = "https://zh.wikipedia.org/w/api.php"
USER_AGENT = "bazichart-engine/1.0 (famous people crawler)"
ENTITY_BATCH_SIZE = 25
MIN_TOTAL_PEOPLE = 10000
MIN_TOTAL_PEOPLE_SCIENTISTS = 5000
MAX_ACCEPTABLE_RETRY_AFTER = 30
SMOKE_MIN_TOTAL_PEOPLE = 1
FAILURE_RETRY_BASE_DELAY_SECONDS = 300
FAILURE_RETRY_MAX_DELAY_SECONDS = 7200

CHINA_LIKE_QIDS = ["Q148", "Q865", "Q8646", "Q14773", "Q1054923", "Q3916279"]
WESTERN_COUNTRY_QIDS = [
    "Q30",
    "Q145",
    "Q142",
    "Q183",
    "Q38",
    "Q29",
    "Q16",
    "Q408",
    "Q27",
    "Q55",
    "Q31",
    "Q40",
    "Q39",
    "Q34",
    "Q20",
    "Q35",
    "Q33",
    "Q45",
    "Q664",
]
GLOBAL_EXTRA_COUNTRY_QIDS = [
    "Q17",
    "Q884",
    "Q668",
    "Q159",
    "Q155",
    "Q96",
    "Q414",
    "Q258",
    "Q43",
    "Q79",
]
WESTERN_EXTRA_COUNTRY_NAMES = [
    "Netherlands",
    "Poland",
    "Czech Republic",
    "Hungary",
    "Romania",
    "Bulgaria",
    "Croatia",
    "Serbia",
    "Ukraine",
    "Greece",
    "Luxembourg",
    "Slovakia",
    "Slovenia",
    "Lithuania",
    "Latvia",
    "Estonia",
    "Iceland",
]
GLOBAL_EXTRA_COUNTRY_NAMES = [
    "Turkey",
    "Iran",
    "Saudi Arabia",
    "United Arab Emirates",
    "Israel",
    "Nigeria",
    "Kenya",
    "Ethiopia",
    "Argentina",
    "Chile",
    "Colombia",
    "Peru",
    "Venezuela",
    "Indonesia",
    "Malaysia",
    "Thailand",
    "Vietnam",
    "Philippines",
    "Pakistan",
    "Bangladesh",
    "Nepal",
    "Sri Lanka",
    "Singapore",
    "Kazakhstan",
    "Uzbekistan",
]
OCCUPATION_QIDS = {
    "politician": "Q82955",
    "scientist": "Q901",
    "mathematician": "Q170790",
    "physicist": "Q169470",
    "chemist": "Q593644",
    "biologist": "Q864503",
    "astronomer": "Q11063",
    "computer_scientist": "Q82594",
    "inventor": "Q205375",
    "writer": "Q36180",
    "actor": "Q33999",
    "singer": "Q177220",
    "athlete": "Q2066131",
    "businessperson": "Q43845",
    "entrepreneur": "Q131524",
}
STANDARD_OCCUPATION_NAMES = ["企业家", "政治家", "演员", "运动员", "科学家", "作家", "音乐家"]
OCCUPATION_CATEGORY_BY_KEY = {
    "businessperson": "企业家",
    "entrepreneur": "企业家",
    "politician": "政治家",
    "actor": "演员",
    "athlete": "运动员",
    "scientist": "科学家",
    "mathematician": "科学家",
    "physicist": "科学家",
    "chemist": "科学家",
    "biologist": "科学家",
    "astronomer": "科学家",
    "computer_scientist": "科学家",
    "inventor": "科学家",
    "writer": "作家",
    "singer": "音乐家",
}
OCCUPATION_KEYWORDS = {
    "企业家": ["business", "entrepreneur", "executive", "industrialist", "tycoon", "商人", "企业家", "实业家", "总裁", "首席执行官"],
    "政治家": ["politician", "political", "statesperson", "president", "prime minister", "皇帝", "君主", "政治家", "政治人物", "总统", "首相"],
    "演员": ["actor", "actress", "film actor", "television actor", "演员", "艺人"],
    "运动员": ["athlete", "player", "footballer", "basketball", "baseball", "tennis", "olympic", "运动员", "选手", "球员", "奥运"],
    "科学家": ["scientist", "mathematician", "physicist", "chemist", "biologist", "astronomer", "computer scientist", "inventor", "engineer", "科学家", "数学家", "物理学家", "化学家", "生物学家", "天文学家", "计算机科学家", "发明家", "工程师"],
    "作家": ["writer", "author", "novelist", "poet", "essayist", "writer", "作家", "小说家", "诗人", "编剧"],
    "音乐家": ["singer", "musician", "composer", "rapper", "pianist", "violinist", "歌手", "音乐家", "作曲家", "演奏家"],
}
STANDARD_OCCUPATION_EN = {
    "企业家": "Entrepreneur",
    "政治家": "Politician",
    "演员": "Actor",
    "运动员": "Athlete",
    "科学家": "Scientist",
    "作家": "Writer",
    "音乐家": "Musician",
}
TRADITIONAL_CONVERTER = OpenCC("s2t")
SCIENTIST_OCCUPATIONS = [
    "scientist",
    "mathematician",
    "physicist",
    "chemist",
    "biologist",
    "astronomer",
    "computer_scientist",
    "inventor",
]
COHORT_CONFIGS = {
    "china_like": {
        "country_qids": CHINA_LIKE_QIDS,
        "language": "zh",
        "occupations": ["politician", "writer", "scientist", "actor", "singer", "businessperson", "entrepreneur"],
        "per_query_limit": 25,
        "pages": 4,
    },
    "western": {
        "country_qids": WESTERN_COUNTRY_QIDS,
        "extra_country_names": WESTERN_EXTRA_COUNTRY_NAMES,
        "language": "en",
        "occupations": ["politician", "scientist", "writer", "actor", "singer", "athlete", "businessperson", "entrepreneur"],
        "per_query_limit": 15,
        "pages": 3,
    },
    "global_extra": {
        "country_qids": GLOBAL_EXTRA_COUNTRY_QIDS,
        "extra_country_names": GLOBAL_EXTRA_COUNTRY_NAMES,
        "language": "en",
        "occupations": ["politician", "scientist", "writer", "actor", "singer", "athlete", "businessperson", "entrepreneur"],
        "per_query_limit": 15,
        "pages": 3,
    },
}

CATEGORY_GROUPS = {
    "china_like": [
        (EN_WIKIPEDIA_API_URL, "Category:Chinese emperors"),
        (EN_WIKIPEDIA_API_URL, "Category:Qing dynasty emperors"),
        (EN_WIKIPEDIA_API_URL, "Category:Ming dynasty emperors"),
        (EN_WIKIPEDIA_API_URL, "Category:Tang dynasty people"),
        (EN_WIKIPEDIA_API_URL, "Category:Song dynasty people"),
        (EN_WIKIPEDIA_API_URL, "Category:Han dynasty people"),
        (EN_WIKIPEDIA_API_URL, "Category:Chinese politicians"),
        (EN_WIKIPEDIA_API_URL, "Category:Chinese political philosophers"),
        (EN_WIKIPEDIA_API_URL, "Category:Chinese writers"),
        (EN_WIKIPEDIA_API_URL, "Category:Chinese poets"),
        (EN_WIKIPEDIA_API_URL, "Category:Chinese novelists"),
        (EN_WIKIPEDIA_API_URL, "Category:Chinese businesspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:Chinese chief executives"),
        (EN_WIKIPEDIA_API_URL, "Category:Chinese billionaires"),
        (EN_WIKIPEDIA_API_URL, "Category:Chinese scientists"),
        (EN_WIKIPEDIA_API_URL, "Category:Chinese mathematicians"),
        (EN_WIKIPEDIA_API_URL, "Category:Chinese physicists"),
        (EN_WIKIPEDIA_API_URL, "Category:Chinese inventors"),
        (EN_WIKIPEDIA_API_URL, "Category:Chinese historians"),
        (EN_WIKIPEDIA_API_URL, "Category:Chinese actors"),
        (EN_WIKIPEDIA_API_URL, "Category:Chinese actresses"),
        (EN_WIKIPEDIA_API_URL, "Category:Chinese singers"),
        (EN_WIKIPEDIA_API_URL, "Category:Chinese film directors"),
        (EN_WIKIPEDIA_API_URL, "Category:Hong Kong actors"),
        (EN_WIKIPEDIA_API_URL, "Category:Hong Kong singers"),
        (EN_WIKIPEDIA_API_URL, "Category:Taiwanese businesspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:Taiwanese actors"),
        (EN_WIKIPEDIA_API_URL, "Category:Taiwanese singers"),
        (ZH_WIKIPEDIA_API_URL, "Category:中国皇帝"),
        (ZH_WIKIPEDIA_API_URL, "Category:中国君主"),
        (ZH_WIKIPEDIA_API_URL, "Category:中国政治人物"),
        (ZH_WIKIPEDIA_API_URL, "Category:中国作家"),
        (ZH_WIKIPEDIA_API_URL, "Category:中国诗人"),
        (ZH_WIKIPEDIA_API_URL, "Category:中国企业家"),
        (ZH_WIKIPEDIA_API_URL, "Category:中国科学家"),
        (ZH_WIKIPEDIA_API_URL, "Category:中国数学家"),
        (ZH_WIKIPEDIA_API_URL, "Category:中国物理学家"),
        (ZH_WIKIPEDIA_API_URL, "Category:中国发明家"),
        (ZH_WIKIPEDIA_API_URL, "Category:中国教育家"),
        (ZH_WIKIPEDIA_API_URL, "Category:中国历史学家"),
        (ZH_WIKIPEDIA_API_URL, "Category:中国男演员"),
        (ZH_WIKIPEDIA_API_URL, "Category:中国女演员"),
        (ZH_WIKIPEDIA_API_URL, "Category:中国男歌手"),
        (ZH_WIKIPEDIA_API_URL, "Category:中国女歌手"),
        (ZH_WIKIPEDIA_API_URL, "Category:中国电影导演"),
        (ZH_WIKIPEDIA_API_URL, "Category:香港男演員"),
        (ZH_WIKIPEDIA_API_URL, "Category:香港女演員"),
        (ZH_WIKIPEDIA_API_URL, "Category:香港男歌手"),
        (ZH_WIKIPEDIA_API_URL, "Category:香港女歌手"),
        (ZH_WIKIPEDIA_API_URL, "Category:台灣企業家"),
        (ZH_WIKIPEDIA_API_URL, "Category:台灣男演員"),
        (ZH_WIKIPEDIA_API_URL, "Category:台灣女演員"),
        (ZH_WIKIPEDIA_API_URL, "Category:台灣男歌手"),
        (ZH_WIKIPEDIA_API_URL, "Category:台灣女歌手"),
        (ZH_WIKIPEDIA_API_URL, "Category:中国历史人物"),
    ],
    "western": [
        (EN_WIKIPEDIA_API_URL, "Category:Presidents of the United States"),
        (EN_WIKIPEDIA_API_URL, "Category:American politicians"),
        (EN_WIKIPEDIA_API_URL, "Category:American political writers"),
        (EN_WIKIPEDIA_API_URL, "Category:American businesspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:American chief executives"),
        (EN_WIKIPEDIA_API_URL, "Category:American billionaires"),
        (EN_WIKIPEDIA_API_URL, "Category:American scientists"),
        (EN_WIKIPEDIA_API_URL, "Category:American mathematicians"),
        (EN_WIKIPEDIA_API_URL, "Category:American physicists"),
        (EN_WIKIPEDIA_API_URL, "Category:American inventors"),
        (EN_WIKIPEDIA_API_URL, "Category:American actors"),
        (EN_WIKIPEDIA_API_URL, "Category:American actresses"),
        (EN_WIKIPEDIA_API_URL, "Category:American singers"),
        (EN_WIKIPEDIA_API_URL, "Category:American film directors"),
        (EN_WIKIPEDIA_API_URL, "Category:British politicians"),
        (EN_WIKIPEDIA_API_URL, "Category:British writers"),
        (EN_WIKIPEDIA_API_URL, "Category:British actors"),
        (EN_WIKIPEDIA_API_URL, "Category:British scientists"),
        (EN_WIKIPEDIA_API_URL, "Category:British singers"),
        (EN_WIKIPEDIA_API_URL, "Category:British businesspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:French scientists"),
        (EN_WIKIPEDIA_API_URL, "Category:French writers"),
        (EN_WIKIPEDIA_API_URL, "Category:French actors"),
        (EN_WIKIPEDIA_API_URL, "Category:German scientists"),
        (EN_WIKIPEDIA_API_URL, "Category:German inventors"),
        (EN_WIKIPEDIA_API_URL, "Category:German writers"),
        (EN_WIKIPEDIA_API_URL, "Category:Italian artists"),
        (EN_WIKIPEDIA_API_URL, "Category:Italian writers"),
        (EN_WIKIPEDIA_API_URL, "Category:Spanish painters"),
        (EN_WIKIPEDIA_API_URL, "Category:Spanish writers"),
        (EN_WIKIPEDIA_API_URL, "Category:Canadian businesspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:Canadian actors"),
        (EN_WIKIPEDIA_API_URL, "Category:Australian actors"),
        (EN_WIKIPEDIA_API_URL, "Category:American sportspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:American basketball players"),
        (EN_WIKIPEDIA_API_URL, "Category:American baseball players"),
        (EN_WIKIPEDIA_API_URL, "Category:American tennis players"),
        (EN_WIKIPEDIA_API_URL, "Category:British sportspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:Canadian sportspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:Australian sportspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:French sportspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:German sportspeople"),
    ],
    "global_extra": [
        (EN_WIKIPEDIA_API_URL, "Category:Japanese politicians"),
        (EN_WIKIPEDIA_API_URL, "Category:Japanese businesspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:Japanese scientists"),
        (EN_WIKIPEDIA_API_URL, "Category:Japanese writers"),
        (EN_WIKIPEDIA_API_URL, "Category:Japanese actors"),
        (EN_WIKIPEDIA_API_URL, "Category:Japanese actresses"),
        (EN_WIKIPEDIA_API_URL, "Category:Japanese singers"),
        (EN_WIKIPEDIA_API_URL, "Category:Japanese sportspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:South Korean politicians"),
        (EN_WIKIPEDIA_API_URL, "Category:South Korean businesspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:South Korean actors"),
        (EN_WIKIPEDIA_API_URL, "Category:South Korean actresses"),
        (EN_WIKIPEDIA_API_URL, "Category:South Korean singers"),
        (EN_WIKIPEDIA_API_URL, "Category:South Korean sportspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:Indian politicians"),
        (EN_WIKIPEDIA_API_URL, "Category:Indian businesspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:Indian scientists"),
        (EN_WIKIPEDIA_API_URL, "Category:Indian actors"),
        (EN_WIKIPEDIA_API_URL, "Category:Indian actresses"),
        (EN_WIKIPEDIA_API_URL, "Category:Indian singers"),
        (EN_WIKIPEDIA_API_URL, "Category:Indian sportspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:Russian politicians"),
        (EN_WIKIPEDIA_API_URL, "Category:Russian businesspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:Russian scientists"),
        (EN_WIKIPEDIA_API_URL, "Category:Russian writers"),
        (EN_WIKIPEDIA_API_URL, "Category:Russian actors"),
        (EN_WIKIPEDIA_API_URL, "Category:Russian singers"),
        (EN_WIKIPEDIA_API_URL, "Category:Russian sportspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:Brazilian politicians"),
        (EN_WIKIPEDIA_API_URL, "Category:Brazilian businesspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:Brazilian scientists"),
        (EN_WIKIPEDIA_API_URL, "Category:Brazilian actors"),
        (EN_WIKIPEDIA_API_URL, "Category:Brazilian singers"),
        (EN_WIKIPEDIA_API_URL, "Category:Brazilian sportspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:Mexican politicians"),
        (EN_WIKIPEDIA_API_URL, "Category:Mexican businesspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:Mexican scientists"),
        (EN_WIKIPEDIA_API_URL, "Category:Mexican actors"),
        (EN_WIKIPEDIA_API_URL, "Category:Mexican singers"),
        (EN_WIKIPEDIA_API_URL, "Category:Mexican sportspeople"),
        (EN_WIKIPEDIA_API_URL, "Category:French politicians"),
        (EN_WIKIPEDIA_API_URL, "Category:German politicians"),
        (EN_WIKIPEDIA_API_URL, "Category:Italian politicians"),
        (EN_WIKIPEDIA_API_URL, "Category:Spanish politicians"),
    ],
}


def build_sparql_query(language_wikipedia: str, country_qids: list[str], occupation_qid: str, limit: int, offset: int) -> str:
    values = " ".join(f"wd:{qid}" for qid in country_qids)
    return f"""
SELECT
  ?person
  ?birthDate
  ?precision
  ?sitelinks
WHERE {{
  ?person wdt:P31 wd:Q5 ;
          wdt:P106 wd:{occupation_qid} ;
          wdt:P27 ?country ;
          wikibase:sitelinks ?sitelinks .
  ?person p:P569/psv:P569 ?birthNode .
  ?birthNode wikibase:timeValue ?birthDate ;
             wikibase:timePrecision ?precision .
  FILTER(?precision >= 11)
  FILTER(?sitelinks >= 5)
  VALUES ?country {{ {values} }}
}}
ORDER BY DESC(?sitelinks)
LIMIT {limit}
OFFSET {offset}
""".strip()


def parse_birth_datetime(raw_value: str, precision: int) -> dict[str, Any] | None:
    match = re.match(r"^\+?(-?\d+)-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z$", raw_value)
    if not match:
        return None
    year = int(match.group(1))
    month = int(match.group(2))
    day = int(match.group(3))
    hour = int(match.group(4))
    minute = int(match.group(5))
    second = int(match.group(6))
    if year <= 0:
        return None
    if precision < 11:
        return None
    return {
        "year": year,
        "month": month,
        "day": day,
        "hour": hour if precision >= 12 else None,
        "minute": minute if precision >= 13 else 0,
        "second": second if precision >= 14 else 0,
        "precision": precision,
    }


def build_pillars(birth_info: dict[str, Any]) -> dict[str, str | None]:
    hour = birth_info["hour"] if birth_info["hour"] is not None else 12
    minute = birth_info["minute"] if birth_info["hour"] is not None else 0
    second = birth_info["second"] if birth_info["hour"] is not None else 0
    solar = Solar.fromYmdHms(birth_info["year"], birth_info["month"], birth_info["day"], hour, minute, second)
    eight_char = solar.getLunar().getEightChar()
    return {
        "year": eight_char.getYear(),
        "month": eight_char.getMonth(),
        "day": eight_char.getDay(),
        "hour": eight_char.getTime() if birth_info["hour"] is not None else None,
    }


def build_wuxing_distribution(birth_info: dict[str, Any]) -> dict[str, int]:
    hour = birth_info["hour"] if birth_info["hour"] is not None else 12
    minute = birth_info["minute"] if birth_info["hour"] is not None else 0
    second = birth_info["second"] if birth_info["hour"] is not None else 0
    solar = Solar.fromYmdHms(birth_info["year"], birth_info["month"], birth_info["day"], hour, minute, second)
    eight_char = solar.getLunar().getEightChar()
    values = [
        eight_char.getYearWuXing(),
        eight_char.getMonthWuXing(),
        eight_char.getDayWuXing(),
    ]
    if birth_info["hour"] is not None:
        values.append(eight_char.getTimeWuXing())

    counter = defaultdict(int)
    for value in values:
        for char in value:
            counter[char] += 1
    return {element: counter.get(element, 0) for element in ["金", "木", "水", "火", "土"]}


def claim_entity_ids(entity: dict[str, Any], property_id: str) -> list[str]:
    claims = entity.get("claims", {}).get(property_id, [])
    ids = []
    for claim in claims:
        data_value = claim.get("mainsnak", {}).get("datavalue", {})
        value = data_value.get("value", {})
        entity_id = value.get("id")
        if entity_id:
            ids.append(entity_id)
    return ids


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[index:index + size] for index in range(0, len(items), size)]


def fetch_entities(session: requests.Session, ids: list[str]) -> dict[str, Any]:
    entities = {}
    for batch in chunked(ids, ENTITY_BATCH_SIZE):
        for attempt in range(6):
            response = session.get(
                WIKIDATA_API_URL,
                params={
                    "action": "wbgetentities",
                    "format": "json",
                    "ids": "|".join(batch),
                    "languages": "zh|en",
                    "props": "labels|descriptions|claims",
                },
                timeout=90,
            )
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "5"))
                time.sleep(retry_after + attempt * 2)
                continue
            response.raise_for_status()
            entities.update(response.json().get("entities", {}))
            time.sleep(0.6)
            break
        else:
            response.raise_for_status()
    return entities


def label_value(entity: dict[str, Any], language: str) -> str:
    return entity.get("labels", {}).get(language, {}).get("value", "")


def description_value(entity: dict[str, Any], language: str) -> str:
    return entity.get("descriptions", {}).get(language, {}).get("value", "")


def resolve_entity_id(session: requests.Session, name: str) -> str | None:
    response = session.get(
        WIKIDATA_API_URL,
        params={
            "action": "wbsearchentities",
            "format": "json",
            "language": "en",
            "type": "item",
            "limit": 5,
            "search": name,
        },
        timeout=30,
    )
    response.raise_for_status()
    for item in response.json().get("search", []):
        description = (item.get("description") or "").lower()
        if "country" in description or "sovereign state" in description:
            return item.get("id")
    results = response.json().get("search", [])
    return results[0].get("id") if results else None


def expand_country_qids(session: requests.Session, base_qids: list[str], extra_country_names: list[str] | None = None) -> list[str]:
    qids = list(base_qids)
    for name in extra_country_names or []:
        try:
            entity_id = resolve_entity_id(session, name)
        except RequestException as exc:
            print(f"跳过国家名称 {name}：{exc}", flush=True)
            continue
        if entity_id and entity_id not in qids:
            qids.append(entity_id)
            print(f"追加国家 {name} -> {entity_id}", flush=True)
    return qids


def build_detail_map(session: requests.Session, person_ids: list[str]) -> dict[str, dict[str, Any]]:
    people_entities = fetch_entities(session, person_ids)
    related_ids = set()
    for entity in people_entities.values():
        related_ids.update(claim_entity_ids(entity, "P27"))
        related_ids.update(claim_entity_ids(entity, "P106"))
    related_entities = fetch_entities(session, sorted(related_ids)) if related_ids else {}

    details = {}
    for person_id, entity in people_entities.items():
        country_ids = claim_entity_ids(entity, "P27")
        occupation_ids = claim_entity_ids(entity, "P106")
        countries_zh = [label_value(related_entities.get(item, {}), "zh") or label_value(related_entities.get(item, {}), "en") for item in country_ids]
        countries_en = [label_value(related_entities.get(item, {}), "en") or label_value(related_entities.get(item, {}), "zh") for item in country_ids]
        fields_zh = [label_value(related_entities.get(item, {}), "zh") or label_value(related_entities.get(item, {}), "en") for item in occupation_ids]
        fields_en = [label_value(related_entities.get(item, {}), "en") or label_value(related_entities.get(item, {}), "zh") for item in occupation_ids]
        occupations = classify_occupations(occupation_ids, fields_zh, fields_en)
        summary_zh = description_value(entity, "zh") or ""
        summary_en = description_value(entity, "en") or ""
        details[person_id] = {
            "name_zh": label_value(entity, "zh") or label_value(entity, "en") or person_id,
            "name_en": label_value(entity, "en") or label_value(entity, "zh") or person_id,
            "summary": summary_zh or summary_en,
            "summary_zh": summary_zh,
            "summary_en": summary_en,
            "nationality_zh": "、".join(dict.fromkeys(item for item in countries_zh if item)),
            "nationality_en": ", ".join(dict.fromkeys(item for item in countries_en if item)),
            "field_zh": "、".join(dict.fromkeys(item for item in fields_zh if item)),
            "field_en": ", ".join(dict.fromkeys(item for item in fields_en if item)),
            "occupation": occupations,
        }
    return details


def classify_occupations(occupation_ids: list[str], fields_zh: list[str], fields_en: list[str]) -> list[str]:
    categories: list[str] = []
    for occupation_key, occupation_qid in OCCUPATION_QIDS.items():
        if occupation_qid in occupation_ids:
            category = OCCUPATION_CATEGORY_BY_KEY.get(occupation_key)
            if category and category not in categories:
                categories.append(category)

    labels = [item for item in [*fields_zh, *fields_en] if item]
    lower_labels = [item.lower() for item in labels]
    for category in STANDARD_OCCUPATION_NAMES:
        if category in categories:
            continue
        keywords = OCCUPATION_KEYWORDS[category]
        if any(keyword in label for keyword in keywords for label in lower_labels) or any(keyword in label for keyword in keywords for label in labels):
            categories.append(category)
    return categories


def to_traditional(text: str) -> str:
    if not text:
        return ""
    return TRADITIONAL_CONVERTER.convert(text)


def build_multilingual_fields(
    name_zh: str,
    name_en: str,
    nationality_zh: str,
    nationality_en: str,
    occupation: list[str],
    summary_zh: str,
    summary_en: str,
) -> dict[str, Any]:
    return {
        "name_zh_hant": to_traditional(name_zh),
        "nationality_zh_hant": to_traditional(nationality_zh),
        "occupation_en": [STANDARD_OCCUPATION_EN[item] for item in occupation if item in STANDARD_OCCUPATION_EN],
        "occupation_zh_hant": [to_traditional(item) for item in occupation],
        "bio_zh": summary_zh,
        "bio_en": summary_en,
        "bio_zh_hant": to_traditional(summary_zh),
    }


def enrich_person(row: dict[str, Any], cohort: str, details: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    birth = parse_birth_datetime(row["birthDate"]["value"], int(row["precision"]["value"]))
    if birth is None:
        return None

    pillars = build_pillars(birth)
    qid = row["person"]["value"].rsplit("/", 1)[-1]
    day_master = pillars["day"][0]
    detail = details.get(qid, {})
    name_zh = detail.get("name_zh") or qid
    name_en = detail.get("name_en") or qid
    nationality_zh = detail.get("nationality_zh", "")
    nationality_en = detail.get("nationality_en", "")
    occupation = detail.get("occupation", [])
    summary_zh = detail.get("summary_zh") or detail.get("summary", "")
    summary_en = detail.get("summary_en") or detail.get("summary", "")
    return {
        "id": qid,
        "name_zh": name_zh,
        "name_en": name_en,
        "birth_date": f"{birth['year']:04d}-{birth['month']:02d}-{birth['day']:02d}",
        "birth_hour": birth["hour"],
        "has_birth_hour": birth["hour"] is not None,
        "nationality_zh": nationality_zh,
        "nationality_en": nationality_en,
        "occupation": occupation,
        "field_zh": detail.get("field_zh", ""),
        "field_en": detail.get("field_en", ""),
        "summary": summary_zh or summary_en,
        "source": {
            "type": "wikidata",
            "cohort": cohort,
            "id": qid,
            "url": f"https://www.wikidata.org/wiki/{qid}",
        },
        "birth_precision": int(row["precision"]["value"]),
        "pillars": pillars,
        "day_pillar": pillars["day"],
        "day_master": day_master,
        "wuxing_distribution": build_wuxing_distribution(birth),
        **build_multilingual_fields(name_zh, name_en, nationality_zh, nationality_en, occupation, summary_zh, summary_en),
    }


def query_wikidata(session: requests.Session, query: str) -> list[dict[str, Any]]:
    response = session.get(
        WIKIDATA_SPARQL_URL,
        params={"query": query, "format": "json"},
        timeout=90,
        headers={"Accept": "application/sparql-results+json"},
    )
    response.raise_for_status()
    time.sleep(1.0)
    return response.json()["results"]["bindings"]


def fetch_cohort_from_countries(
    session: requests.Session,
    cohort: str,
    pipeline_state: dict[str, Any],
    country_qids: list[str],
    language: str,
    occupations: list[str],
    per_query_limit: int,
    pages: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for country_qid in country_qids:
        for occupation_name in occupations:
            occupation_qid = OCCUPATION_QIDS[occupation_name]
            for page in range(pages):
                job = build_query_job(cohort, language, country_qid, occupation_name, per_query_limit, page)
                try:
                    result_rows = run_query_job(session, pipeline_state, job, use_cache=True)
                except RequestException as exc:
                    break
                rows.extend(result_rows)
                print(
                    f"[{cohort}] 国家 {country_qid} × {occupation_name} 第 {page + 1} 页完成：{len(result_rows)}，累计 {len(rows)}",
                    flush=True,
                )
                if len(result_rows) < per_query_limit:
                    break

    return fetch_people_from_cached_rows(session, cohort, rows)


def run_query_job(
    session: requests.Session,
    pipeline_state: dict[str, Any],
    job: dict[str, Any],
    *,
    use_cache: bool,
) -> list[dict[str, Any]]:
    occupation_qid = OCCUPATION_QIDS[job["occupation"]]
    query = build_sparql_query(job["language"], [job["country_qid"]], occupation_qid, job["limit"], job["offset"])
    print(
        f"[{job['cohort']}] SPARQL 国家 {job['country_qid']} × {job['occupation']}，第 {job['page']} 页，限制 {job['limit']}",
        flush=True,
    )
    if use_cache:
        cached_rows = get_cached_rows(pipeline_state, job)
        if cached_rows is not None:
            print(
                f"[{job['cohort']}] 命中缓存 国家 {job['country_qid']} × {job['occupation']} 第 {job['page']} 页：{len(cached_rows)}",
                flush=True,
            )
            return cached_rows
    try:
        result_rows = query_wikidata(session, query)
    except RequestException as exc:
        record_failed_job(pipeline_state, job, str(exc))
        print(f"[{job['cohort']}] 跳过国家 {job['country_qid']} × {job['occupation']} 第 {job['page']} 页：{exc}", flush=True)
        raise
    cache_query_rows(pipeline_state, job, result_rows)
    clear_failed_job(pipeline_state, job)
    print(
        f"[{job['cohort']}] 国家 {job['country_qid']} × {job['occupation']} 第 {job['page']} 页完成：{len(result_rows)}",
        flush=True,
    )
    return result_rows


def collect_cached_rows(pipeline_state: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in pipeline_state["candidate_cache"]["pages"].values():
        cohort = item.get("job", {}).get("cohort", "unknown")
        for row in item.get("rows", []):
            row_copy = dict(row)
            row_copy["_cohort"] = cohort
            rows.append(row_copy)
    return rows


def fetch_people_from_cached_rows(session: requests.Session, cohort: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    qids = sorted({row["person"]["value"].rsplit("/", 1)[-1] for row in rows})
    print(f"[{cohort}] 准备补详情的去重 QID：{len(qids)}", flush=True)
    details = build_detail_map(session, qids)
    people = []
    for row in rows:
        person = enrich_person(row, row.get("_cohort", cohort), details)
        if person is not None:
            people.append(person)
    print(f"[{cohort}] 转换为名人记录：{len(people)}", flush=True)
    return people


def retry_failed_jobs(session: requests.Session, pipeline_state: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    retried_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    jobs = get_retryable_failure_jobs(pipeline_state)
    if not pipeline_state["failure_queue"]["jobs"]:
        print("失败队列为空，直接复用缓存候选页", flush=True)
        return retried_rows
    if not jobs:
        print("失败队列存在，但当前没有到期可补跑的任务", flush=True)
        return retried_rows
    print(f"开始补跑失败页：{len(jobs)}", flush=True)
    for item in jobs:
        job = item["job"]
        try:
            rows = run_query_job(session, pipeline_state, job, use_cache=False)
        except RequestException:
            continue
        retried_rows[job["cohort"]].extend(rows)
    return retried_rows


def get_json_with_retry(session: requests.Session, url: str, params: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    last_response = None
    last_exception: Exception | None = None
    for attempt in range(6):
        try:
            response = session.get(url, params=params, timeout=timeout)
            last_response = response
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "5"))
                if retry_after > MAX_ACCEPTABLE_RETRY_AFTER:
                    print(f"跳过长限流请求：{params.get('cmtitle') or params.get('titles') or params.get('ids')} ({retry_after}s)", flush=True)
                    raise RuntimeError("long_retry_after")
                print(f"请求被限流，{retry_after} 秒后重试：{params.get('cmtitle') or params.get('titles') or params.get('ids')}", flush=True)
                time.sleep(retry_after + attempt * 2)
                continue
            response.raise_for_status()
            time.sleep(0.6)
            return response.json()
        except RuntimeError:
            raise
        except RequestException as exc:
            last_exception = exc
            print(f"请求失败，第 {attempt + 1} 次重试：{params.get('cmtitle') or params.get('titles') or params.get('ids')} -> {exc}", flush=True)
            time.sleep(2 + attempt * 2)
    if last_response is None and last_exception is not None:
        raise last_exception
    assert last_response is not None
    last_response.raise_for_status()
    return {}


def fetch_category_titles(session: requests.Session, api_url: str, category: str, max_titles: int = 1000) -> list[str]:
    titles = []
    params = {
        "action": "query",
        "format": "json",
        "list": "categorymembers",
        "cmtitle": category,
        "cmtype": "page",
        "cmlimit": "500",
    }
    while len(titles) < max_titles:
        try:
            payload = get_json_with_retry(session, api_url, params, timeout=30)
        except (RequestException, RuntimeError) as exc:
            print(f"跳过分类 {category}：{exc}", flush=True)
            break
        titles.extend(item["title"] for item in payload.get("query", {}).get("categorymembers", []))
        if "continue" not in payload:
            break
        params.update(payload["continue"])
    return titles[:max_titles]


def fetch_wikibase_items_for_titles(session: requests.Session, api_url: str, titles: list[str]) -> list[str]:
    qids = []
    for batch in chunked(titles, 50):
        try:
            pages = get_json_with_retry(
                session,
                api_url,
                {
                    "action": "query",
                    "format": "json",
                    "prop": "pageprops",
                    "titles": "|".join(batch),
                    "ppprop": "wikibase_item",
                },
                timeout=30,
            ).get("query", {}).get("pages", {})
        except (RequestException, RuntimeError) as exc:
            print(f"跳过标题批次：{exc}", flush=True)
            continue
        for page in pages.values():
            qid = page.get("pageprops", {}).get("wikibase_item")
            if qid:
                qids.append(qid)
    return qids


def parse_birth_claim(entity: dict[str, Any]) -> dict[str, Any] | None:
    claims = entity.get("claims", {}).get("P569", [])
    for claim in claims:
        snak = claim.get("mainsnak", {})
        data_value = snak.get("datavalue", {}).get("value", {})
        raw_value = data_value.get("time")
        precision = int(data_value.get("precision", 0))
        if raw_value:
            parsed = parse_birth_datetime(raw_value, precision)
            if parsed is not None:
                return parsed
    return None


def person_from_entity(entity: dict[str, Any], cohort: str) -> dict[str, Any] | None:
    birth = parse_birth_claim(entity)
    if birth is None:
        return None
    qid = entity["id"]
    detail = {
        "name_zh": label_value(entity, "zh") or label_value(entity, "en") or qid,
        "name_en": label_value(entity, "en") or label_value(entity, "zh") or qid,
        "summary": description_value(entity, "zh") or description_value(entity, "en") or "",
        "nationality_zh": "",
        "nationality_en": "",
        "field_zh": "",
        "field_en": "",
    }
    return enrich_person(
        {
            "person": {"value": f"https://www.wikidata.org/entity/{qid}"},
            "birthDate": {"value": f"+{birth['year']:04d}-{birth['month']:02d}-{birth['day']:02d}T{(birth['hour'] or 0):02d}:{birth['minute']:02d}:{birth['second']:02d}Z"},
            "precision": {"value": str(birth["precision"])},
        },
        cohort,
        {qid: detail},
    )


def fill_related_labels(session: requests.Session, entities: dict[str, Any]) -> dict[str, Any]:
    related_ids = set()
    for entity in entities.values():
        related_ids.update(claim_entity_ids(entity, "P27"))
        related_ids.update(claim_entity_ids(entity, "P106"))
    related_entities = fetch_entities(session, sorted(related_ids)) if related_ids else {}

    for entity in entities.values():
        country_ids = claim_entity_ids(entity, "P27")
        occupation_ids = claim_entity_ids(entity, "P106")
        entity["_country_zh"] = "、".join(
            dict.fromkeys(label_value(related_entities.get(item, {}), "zh") or label_value(related_entities.get(item, {}), "en") for item in country_ids if related_entities.get(item))
        )
        entity["_country_en"] = ", ".join(
            dict.fromkeys(label_value(related_entities.get(item, {}), "en") or label_value(related_entities.get(item, {}), "zh") for item in country_ids if related_entities.get(item))
        )
        entity["_field_zh"] = "、".join(
            dict.fromkeys(label_value(related_entities.get(item, {}), "zh") or label_value(related_entities.get(item, {}), "en") for item in occupation_ids if related_entities.get(item))
        )
        entity["_field_en"] = ", ".join(
            dict.fromkeys(label_value(related_entities.get(item, {}), "en") or label_value(related_entities.get(item, {}), "zh") for item in occupation_ids if related_entities.get(item))
        )
        entity["_occupation"] = classify_occupations(
            occupation_ids,
            [label_value(related_entities.get(item, {}), "zh") or label_value(related_entities.get(item, {}), "en") for item in occupation_ids if related_entities.get(item)],
            [label_value(related_entities.get(item, {}), "en") or label_value(related_entities.get(item, {}), "zh") for item in occupation_ids if related_entities.get(item)],
        )
    return entities


def build_people_from_entities(entities: dict[str, Any], cohort: str) -> list[dict[str, Any]]:
    people = []
    for entity in entities.values():
        birth = parse_birth_claim(entity)
        if birth is None:
            continue
        pillars = build_pillars(birth)
        qid = entity["id"]
        day_master = pillars["day"][0]
        name_zh = label_value(entity, "zh") or label_value(entity, "en") or qid
        name_en = label_value(entity, "en") or label_value(entity, "zh") or qid
        nationality_zh = entity.get("_country_zh", "")
        nationality_en = entity.get("_country_en", "")
        occupation = entity.get("_occupation", [])
        summary_zh = description_value(entity, "zh") or ""
        summary_en = description_value(entity, "en") or ""
        people.append(
            {
                "id": qid,
                "name_zh": name_zh,
                "name_en": name_en,
                "birth_date": f"{birth['year']:04d}-{birth['month']:02d}-{birth['day']:02d}",
                "birth_hour": birth["hour"],
                "has_birth_hour": birth["hour"] is not None,
                "nationality_zh": nationality_zh,
                "nationality_en": nationality_en,
                "occupation": occupation,
                "field_zh": entity.get("_field_zh", ""),
                "field_en": entity.get("_field_en", ""),
                "summary": summary_zh or summary_en,
                "source": {
                    "type": "wikidata",
                    "cohort": cohort,
                    "id": qid,
                    "url": f"https://www.wikidata.org/wiki/{qid}",
                },
                "birth_precision": birth["precision"],
                "pillars": pillars,
                "day_pillar": pillars["day"],
                "day_master": day_master,
                "wuxing_distribution": build_wuxing_distribution(birth),
                **build_multilingual_fields(name_zh, name_en, nationality_zh, nationality_en, occupation, summary_zh, summary_en),
            }
        )
    return people


def fetch_cohort_from_categories(session: requests.Session, cohort: str, max_people: int) -> list[dict[str, Any]]:
    categories = CATEGORY_GROUPS[cohort]
    titles_by_api: dict[str, list[str]] = defaultdict(list)
    for api_url, category in categories:
        print(f"[{cohort}] 读取分类：{category}", flush=True)
        titles_by_api[api_url].extend(fetch_category_titles(session, api_url, category))
        print(f"[{cohort}] 已累计标题：{sum(len(items) for items in titles_by_api.values())}", flush=True)
    qids = set()
    for api_url, titles in titles_by_api.items():
        print(f"[{cohort}] 解析 Wikibase 条目：{api_url}，标题数 {len(sorted(set(titles)))}", flush=True)
        qids.update(fetch_wikibase_items_for_titles(session, api_url, sorted(set(titles))))
        print(f"[{cohort}] 已累计 QID：{len(qids)}", flush=True)
    qids = sorted(qids)
    print(f"[{cohort}] 拉取实体详情：{len(qids)}", flush=True)
    entities = fetch_entities(session, qids)
    entities = fill_related_labels(session, entities)
    people = build_people_from_entities(entities, cohort)
    print(f"[{cohort}] 实体转名人完成：{len(people)}", flush=True)
    return people[:max_people]


def dedupe_people(people: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped = {}
    for person in people:
        deduped[person["id"]] = person
    return sorted(deduped.values(), key=lambda item: (item["birth_date"], item["name_en"]))


def build_day_pillar_index(people: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for person in people:
        index[person["day_pillar"]].append(
            {
                "id": person["id"],
                "name_zh": person["name_zh"],
                "name_en": person["name_en"],
                "birth_date": person["birth_date"],
                "nationality_zh": person["nationality_zh"],
                "occupation": person.get("occupation", []),
                "field_zh": person["field_zh"],
                "summary": person["summary"],
            }
        )
    return {key: value for key, value in sorted(index.items())}


def validate_people(people: list[dict[str, Any]]) -> dict[str, Any]:
    invalid = []
    for person in people:
        required = [
            person.get("id"),
            person.get("name_zh"),
            person.get("name_en"),
            person.get("birth_date"),
            person.get("day_pillar"),
            person.get("day_master"),
        ]
        if not all(required):
            invalid.append(person.get("id", "unknown"))
    return {
        "total_people": len(people),
        "invalid_count": len(invalid),
        "invalid_ids": invalid[:20],
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def build_data_paths(output_suffix: str) -> dict[str, Path]:
    data_dir = Path(__file__).resolve().parent.parent / "data"
    return {
        "data_dir": data_dir,
        "famous_people": data_dir / f"famous_people{output_suffix}.json",
        "day_pillar_index": data_dir / f"day_pillar_index{output_suffix}.json",
        "report": data_dir / f"famous_people_report{output_suffix}.json",
        "candidate_cache": data_dir / f"famous_people_candidate_cache{output_suffix}.json",
        "failure_queue": data_dir / f"famous_people_failure_queue{output_suffix}.json",
    }


def build_query_job(
    cohort: str,
    language: str,
    country_qid: str,
    occupation_name: str,
    per_query_limit: int,
    page: int,
) -> dict[str, Any]:
    return {
        "cohort": cohort,
        "language": language,
        "country_qid": country_qid,
        "occupation": occupation_name,
        "limit": per_query_limit,
        "page": page + 1,
        "offset": page * per_query_limit,
    }


def build_query_job_key(job: dict[str, Any]) -> str:
    return "|".join(
        [
            job["cohort"],
            job["language"],
            job["country_qid"],
            job["occupation"],
            str(job["limit"]),
            str(job["page"]),
            str(job["offset"]),
        ]
    )


def load_pipeline_state(output_suffix: str) -> dict[str, Any]:
    paths = build_data_paths(output_suffix)
    failure_queue = read_json(paths["failure_queue"], {"jobs": []})
    normalized_jobs = []
    for item in failure_queue.get("jobs", []):
        attempt_count = int(item.get("attempt_count", 1))
        error = item.get("error", "")
        next_retry_at = int(item.get("next_retry_at", 0))
        if next_retry_at <= 0:
            next_retry_at = int(time.time()) + compute_failure_retry_delay(error, attempt_count)
        normalized_jobs.append(
            {
                **item,
                "attempt_count": attempt_count,
                "next_retry_at": next_retry_at,
            }
        )
    failure_queue["jobs"] = normalized_jobs
    return {
        "paths": paths,
        "candidate_cache": read_json(paths["candidate_cache"], {"pages": {}}),
        "failure_queue": failure_queue,
    }


def persist_pipeline_state(state: dict[str, Any]) -> None:
    write_json(state["paths"]["candidate_cache"], state["candidate_cache"])
    write_json(state["paths"]["failure_queue"], state["failure_queue"])


def get_cached_rows(state: dict[str, Any], job: dict[str, Any]) -> list[dict[str, Any]] | None:
    cached = state["candidate_cache"]["pages"].get(build_query_job_key(job))
    if cached is None:
        return None
    return cached.get("rows", [])


def cache_query_rows(state: dict[str, Any], job: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    state["candidate_cache"]["pages"][build_query_job_key(job)] = {
        "job": job,
        "row_count": len(rows),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rows": rows,
    }
    persist_pipeline_state(state)


def record_failed_job(state: dict[str, Any], job: dict[str, Any], error: str) -> None:
    job_key = build_query_job_key(job)
    existing = next((item for item in state["failure_queue"]["jobs"] if build_query_job_key(item["job"]) == job_key), None)
    jobs = [item for item in state["failure_queue"]["jobs"] if build_query_job_key(item["job"]) != job_key]
    attempt_count = int(existing.get("attempt_count", 0)) + 1 if existing else 1
    delay_seconds = compute_failure_retry_delay(error, attempt_count)
    jobs.append(
        {
            "job": job,
            "error": error,
            "attempt_count": attempt_count,
            "next_retry_at": int(time.time()) + delay_seconds,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    state["failure_queue"]["jobs"] = jobs
    persist_pipeline_state(state)


def clear_failed_job(state: dict[str, Any], job: dict[str, Any]) -> None:
    job_key = build_query_job_key(job)
    jobs = [item for item in state["failure_queue"]["jobs"] if build_query_job_key(item["job"]) != job_key]
    if len(jobs) != len(state["failure_queue"]["jobs"]):
        state["failure_queue"]["jobs"] = jobs
        persist_pipeline_state(state)


def build_pipeline_summary(state: dict[str, Any], now: int | None = None) -> dict[str, int]:
    ready_failed_jobs = sum(1 for item in state["failure_queue"]["jobs"] if is_failure_job_ready(item, now=now))
    return {
        "candidate_pages": len(state["candidate_cache"]["pages"]),
        "failed_jobs": len(state["failure_queue"]["jobs"]),
        "ready_failed_jobs": ready_failed_jobs,
    }


def compute_failure_retry_delay(error: str, attempt_count: int) -> int:
    delay = FAILURE_RETRY_BASE_DELAY_SECONDS * max(1, 2 ** max(0, attempt_count - 1))
    lowered = error.lower()
    if "504" in lowered or "timeout" in lowered:
        delay *= 2
    return min(delay, FAILURE_RETRY_MAX_DELAY_SECONDS)


def is_failure_job_ready(item: dict[str, Any], now: int | None = None) -> bool:
    now = int(time.time()) if now is None else now
    return int(item.get("next_retry_at", 0)) <= now


def get_retryable_failure_jobs(state: dict[str, Any], now: int | None = None) -> list[dict[str, Any]]:
    now = int(time.time()) if now is None else now
    retryable = [item for item in state["failure_queue"]["jobs"] if is_failure_job_ready(item, now=now)]
    return sorted(
        retryable,
        key=lambda item: (
            int(item.get("next_retry_at", 0)),
            int(item.get("attempt_count", 1)),
            build_query_job_key(item["job"]),
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="抓取名人数据并生成日柱索引")
    parser.add_argument(
        "--mode",
        choices=["full", "smoke"],
        default="full",
        help="full 为默认全量模式，smoke 只跑最小链路验证",
    )
    parser.add_argument(
        "--retry-failures",
        action="store_true",
        help="只补跑失败队列中的查询页，并复用现有候选池缓存生成结果",
    )
    parser.add_argument(
        "--focus",
        choices=["all", "scientists"],
        default="all",
        help="all 为默认综合名人，scientists 只抓科学家与数学家",
    )
    return parser.parse_args()


def build_runtime_configs(mode: str, focus: str = "all") -> tuple[dict[str, dict[str, Any]], int, str]:
    configs = {name: dict(config) for name, config in COHORT_CONFIGS.items()}
    output_suffix = ""
    min_total_people = MIN_TOTAL_PEOPLE
    if focus == "scientists":
        for config in configs.values():
            config["occupations"] = list(SCIENTIST_OCCUPATIONS)
        output_suffix += "_scientists"
        min_total_people = MIN_TOTAL_PEOPLE_SCIENTISTS
    if mode == "smoke":
        for config in configs.values():
            config["country_qids"] = config["country_qids"][:1]
            if focus == "all":
                config["occupations"] = config["occupations"][:2]
            config["pages"] = 1
            config["per_query_limit"] = min(config["per_query_limit"], 5)
            if "extra_country_names" in config:
                config["extra_country_names"] = []
        output_suffix += "_smoke"
        return configs, SMOKE_MIN_TOTAL_PEOPLE, output_suffix
    return configs, min_total_people, output_suffix


def main() -> int:
    args = parse_args()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    runtime_configs, min_total_people, output_suffix = build_runtime_configs(args.mode, args.focus)
    pipeline_state = load_pipeline_state(output_suffix)

    print(f"运行模式：{args.mode}", flush=True)
    print(f"抓取焦点：{args.focus}", flush=True)
    if args.retry_failures:
        print("补跑模式：只处理失败队列", flush=True)

    if args.retry_failures:
        retry_failed_jobs(session, pipeline_state)
        cached_rows = collect_cached_rows(pipeline_state)
        people = dedupe_people(fetch_people_from_cached_rows(session, "retry_failures", cached_rows))
        people_by_cohort: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for person in people:
            people_by_cohort[(person.get("source") or {}).get("cohort", "unknown")].append(person)
        chinese_people = people_by_cohort.get("china_like", [])
        western_people = people_by_cohort.get("western", [])
        global_extra_people = people_by_cohort.get("global_extra", [])
    else:
        print("抓取中文名人...", flush=True)
        chinese_config = dict(runtime_configs["china_like"])
        chinese_people = fetch_cohort_from_countries(session, "china_like", pipeline_state=pipeline_state, **chinese_config)
        print(f"中文名人抓取完成：{len(chinese_people)}", flush=True)

        print("抓取西方名人...", flush=True)
        western_config = dict(runtime_configs["western"])
        western_config["country_qids"] = expand_country_qids(
            session,
            western_config["country_qids"],
            western_config.pop("extra_country_names", []),
        )
        western_people = fetch_cohort_from_countries(session, "western", pipeline_state=pipeline_state, **western_config)
        print(f"西方名人抓取完成：{len(western_people)}", flush=True)

        print("抓取全球补充名人...", flush=True)
        global_extra_config = dict(runtime_configs["global_extra"])
        global_extra_config["country_qids"] = expand_country_qids(
            session,
            global_extra_config["country_qids"],
            global_extra_config.pop("extra_country_names", []),
        )
        global_extra_people = fetch_cohort_from_countries(session, "global_extra", pipeline_state=pipeline_state, **global_extra_config)
        print(f"全球补充名人抓取完成：{len(global_extra_people)}", flush=True)

        people = dedupe_people(chinese_people + western_people + global_extra_people)
    if len(people) < min_total_people:
        raise RuntimeError(f"名人总数不足 {min_total_people}，当前仅 {len(people)}")

    validation = validate_people(people)
    if validation["invalid_count"] != 0:
        raise RuntimeError(f"存在无效名人记录: {validation}")

    paths = pipeline_state["paths"]
    famous_people_path = paths["famous_people"]
    day_pillar_index_path = paths["day_pillar_index"]
    report_path = paths["report"]

    write_json(famous_people_path, people)
    write_json(day_pillar_index_path, build_day_pillar_index(people))
    write_json(
        report_path,
        {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mode": args.mode,
            "focus": args.focus,
            "min_total_people": min_total_people,
            "total_people": len(people),
            "chinese_people": len(chinese_people),
            "western_people": len(western_people),
            "global_extra_people": len(global_extra_people),
            "validation": validation,
            "pipeline": build_pipeline_summary(pipeline_state),
        },
    )
    print(f"输出完成：{famous_people_path}", flush=True)
    print(f"输出完成：{day_pillar_index_path}", flush=True)
    print(f"输出完成：{report_path}", flush=True)
    print(f"总人数：{len(people)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
