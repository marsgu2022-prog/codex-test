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
DEFAULT_OUTPUT = DATA_DIR / "data_quality_stats.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="统计名人数据库数据质量")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def load_people(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"{path} 不是名人列表")
    return payload


def has_birth_time(person: dict[str, Any]) -> bool:
    if person.get("has_birth_hour") is True:
        return True
    birth_hour = person.get("birth_hour")
    birth_time = person.get("birth_time")
    return birth_hour not in (None, "") or birth_time not in (None, "")


def has_birth_city(person: dict[str, Any]) -> bool:
    return any(person.get(key) not in (None, "") for key in ("birth_city", "birth_place_city"))


def has_occupation(person: dict[str, Any]) -> bool:
    occupation = person.get("occupation")
    return isinstance(occupation, list) and len([item for item in occupation if item]) > 0


def has_notable_events(person: dict[str, Any]) -> bool:
    notable_events = person.get("notable_events")
    return isinstance(notable_events, list) and len(notable_events) > 0


def ratio(count: int, total: int) -> float:
    return round((count / total), 6) if total else 0.0


def build_stats(people: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(people)
    metrics = {
        "birth_time": 0,
        "birth_city": 0,
        "occupation": 0,
        "notable_events": 0,
    }
    occupation_distribution: Counter[str] = Counter()

    for person in people:
        if has_birth_time(person):
            metrics["birth_time"] += 1
        if has_birth_city(person):
            metrics["birth_city"] += 1
        if has_occupation(person):
            metrics["occupation"] += 1
            occupation_distribution.update(item for item in person.get("occupation", []) if item)
        if has_notable_events(person):
            metrics["notable_events"] += 1

    return {
        "total_count": total,
        "with_birth_time": {
            "count": metrics["birth_time"],
            "ratio": ratio(metrics["birth_time"], total),
        },
        "with_birth_city": {
            "count": metrics["birth_city"],
            "ratio": ratio(metrics["birth_city"], total),
        },
        "with_occupation": {
            "count": metrics["occupation"],
            "ratio": ratio(metrics["occupation"], total),
        },
        "with_notable_events": {
            "count": metrics["notable_events"],
            "ratio": ratio(metrics["notable_events"], total),
        },
        "occupation_distribution": dict(sorted(occupation_distribution.items(), key=lambda item: (-item[1], item[0]))),
    }


def write_stats(path: Path, stats: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(stats, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main() -> None:
    args = parse_args()
    people = load_people(args.input)
    stats = build_stats(people)
    write_stats(args.output, stats)
    print(
        "总条数：{total}；有时辰：{birth_time}；有出生城市：{birth_city}；有职业：{occupation}；有重大事件：{events}".format(
            total=stats["total_count"],
            birth_time=stats["with_birth_time"]["count"],
            birth_city=stats["with_birth_city"]["count"],
            occupation=stats["with_occupation"]["count"],
            events=stats["with_notable_events"]["count"],
        )
    )


if __name__ == "__main__":
    main()
