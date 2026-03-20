#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "data"
DEFAULT_INPUT = DATA_DIR / "famous_people.json"
DEFAULT_KEYWORDS = DATA_DIR / "blacklist_keywords.json"
DEFAULT_OUTPUT = DATA_DIR / "filtered_out.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按黑名单关键词过滤名人记录")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--keywords", type=Path, default=DEFAULT_KEYWORDS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_search_text(person: dict[str, Any]) -> str:
    values: list[str] = []
    for key in ("bio", "bio_zh", "bio_en", "bio_zh_hans", "bio_zh_hant", "summary", "field_zh", "field_en"):
        value = person.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value)
    occupation = person.get("occupation")
    if isinstance(occupation, list):
        values.extend(item for item in occupation if isinstance(item, str) and item.strip())
    return " ".join(values).lower()


def match_reason(search_text: str, keyword_config: dict[str, Any]) -> tuple[str, str] | None:
    categories = keyword_config.get("categories", {})
    for category, keywords in categories.items():
        for keyword in keywords:
            normalized = keyword.strip().lower()
            if normalized and normalized in search_text:
                return category, keyword
    for keyword in keyword_config.get("strict", []):
        normalized = keyword.strip().lower()
        if normalized and normalized in search_text:
            return "strict", keyword
    return None


def filter_people(people: list[dict[str, Any]], keyword_config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    filtered_records: list[dict[str, Any]] = []
    kept_records: list[dict[str, Any]] = []
    category_counter: Counter[str] = Counter()

    for person in people:
        search_text = build_search_text(person)
        matched = match_reason(search_text, keyword_config)
        if matched is None:
            kept_records.append(person)
            continue
        category, keyword = matched
        category_counter[category] += 1
        filtered_records.append(
            {
                "id": person.get("id"),
                "name_zh": person.get("name_zh"),
                "name_en": person.get("name_en"),
                "birth_date": person.get("birth_date"),
                "matched_category": category,
                "matched_keyword": keyword,
                "occupation": person.get("occupation", []),
                "summary": person.get("summary") or person.get("bio") or person.get("bio_zh"),
            }
        )

    report = {
        "total_input": len(people),
        "filtered_count": len(filtered_records),
        "kept_count": len(kept_records),
        "reason_breakdown": dict(sorted(category_counter.items())),
        "filtered_records": filtered_records,
    }
    return kept_records, report


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main() -> None:
    args = parse_args()
    people = load_json(args.input)
    if not isinstance(people, list):
        raise ValueError(f"{args.input} 不是名人列表")
    keyword_config = load_json(args.keywords)
    _, report = filter_people(people, keyword_config)
    write_report(args.output, report)
    print(
        "过滤完成：总计 {total} 条，过滤 {filtered} 条，保留 {kept} 条".format(
            total=report["total_input"],
            filtered=report["filtered_count"],
            kept=report["kept_count"],
        )
    )
    for category, count in report["reason_breakdown"].items():
        print(f"- {category}: {count}")


if __name__ == "__main__":
    main()
