#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_DIR = BASE_DIR / "knowledge"

DEFAULT_INPUT = DATA_DIR / "bazi_readings.json"
DEFAULT_OUTPUT_MD = KNOWLEDGE_DIR / "auto_rules.md"
DEFAULT_OUTPUT_STATS = KNOWLEDGE_DIR / "auto_rules_stats.json"

STEM_TO_ELEMENT = {
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从高置信八字研读结果中提炼规则")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--output-stats", type=Path, default=DEFAULT_OUTPUT_STATS)
    parser.add_argument("--confidence-threshold", type=float, default=0.8)
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def day_master_label(stem: str) -> str:
    return f"{stem}{STEM_TO_ELEMENT.get(stem, '')}日主"


def extract_month_branch(record: dict[str, Any]) -> str | None:
    month_pillar = (record.get("bazi_pillars") or {}).get("month")
    if not month_pillar or len(month_pillar) < 2:
        return None
    return month_pillar[-1]


def add_bucket(
    container: dict[str, dict[str, Any]],
    key: str,
    *,
    text: str,
    reasoning: str,
    confidence: float,
) -> None:
    bucket = container.setdefault(
        key,
        {"text": text, "count": 0, "confidence_sum": 0.0, "reasons": defaultdict(int)},
    )
    bucket["count"] += 1
    bucket["confidence_sum"] += confidence
    if reasoning:
        bucket["reasons"][reasoning] += 1


def finalize_buckets(
    buckets: dict[str, dict[str, Any]],
    total_samples: int,
    *,
    sort_key: str = "count",
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for bucket in buckets.values():
        top_reasons = sorted(
            bucket["reasons"].items(),
            key=lambda item: (-item[1], item[0]),
        )
        count = bucket["count"]
        items.append(
            {
                "text": bucket["text"],
                "count": count,
                "occurrence_rate": round(count / total_samples, 4) if total_samples else 0.0,
                "average_confidence": round(bucket["confidence_sum"] / count, 4) if count else 0.0,
                "top_reasons": [{"text": text, "count": reason_count} for text, reason_count in top_reasons[:3]],
            }
        )
    return sorted(items, key=lambda item: (-item[sort_key], item["text"]))


def extract_rules(readings: list[dict[str, Any]], confidence_threshold: float) -> dict[str, Any]:
    high_conf = []
    for item in readings:
        reading = item.get("reading") or {}
        confidence = reading.get("confidence")
        if isinstance(confidence, (int, float)) and confidence >= confidence_threshold:
            high_conf.append(item)

    grouped: dict[str, dict[str, Any]] = {}
    for item in high_conf:
        reading = item["reading"]
        day_master = reading.get("day_master")
        if not day_master:
            continue
        day_master_key = day_master_label(day_master)
        month_branch = extract_month_branch(item)
        confidence = float(reading.get("confidence") or 0.0)
        state = grouped.setdefault(
            day_master_key,
            {
                "sample_count": 0,
                "patterns": {},
                "useful_gods": {},
                "career_tendencies": {},
                "personality_traits": {},
            },
        )
        state["sample_count"] += 1

        pattern = normalize_text(reading.get("pattern"))
        if pattern:
            pattern_text = (
                f"{day_master_key[:-2]}生于{month_branch}月，多见{pattern}"
                if month_branch
                else f"{day_master_key[:-2]}多见{pattern}"
            )
            add_bucket(
                state["patterns"],
                f"{month_branch or 'unknown'}::{pattern}",
                text=pattern_text,
                reasoning=normalize_text(reading.get("pattern_reasoning")),
                confidence=confidence,
            )

        useful_god = normalize_text(reading.get("useful_god"))
        if useful_god:
            add_bucket(
                state["useful_gods"],
                useful_god,
                text=f"常见用神：{useful_god}",
                reasoning=normalize_text(reading.get("useful_god_reasoning")),
                confidence=confidence,
            )

        for career in reading.get("career_tendency") or []:
            career_text = normalize_text(career)
            if not career_text:
                continue
            add_bucket(
                state["career_tendencies"],
                career_text,
                text=f"适合{career_text}方向",
                reasoning=normalize_text(reading.get("career_reasoning")),
                confidence=confidence,
            )

        for trait in reading.get("personality_traits") or []:
            trait_text = normalize_text(trait)
            if not trait_text:
                continue
            add_bucket(
                state["personality_traits"],
                trait_text,
                text=trait_text,
                reasoning=normalize_text(reading.get("strength_reasoning") or reading.get("analysis_notes")),
                confidence=confidence,
            )

    stats = {
        "source": str(DEFAULT_INPUT.name),
        "confidence_threshold": confidence_threshold,
        "total_readings": len(readings),
        "high_confidence_readings": len(high_conf),
        "day_masters": {},
    }

    for day_master_key, payload in grouped.items():
        total_samples = payload["sample_count"]
        stats["day_masters"][day_master_key] = {
            "sample_count": total_samples,
            "patterns": finalize_buckets(payload["patterns"], total_samples),
            "useful_gods": finalize_buckets(payload["useful_gods"], total_samples),
            "career_tendencies": finalize_buckets(payload["career_tendencies"], total_samples),
            "personality_traits": finalize_buckets(payload["personality_traits"], total_samples),
        }

    return stats


def render_markdown(stats: dict[str, Any]) -> str:
    lines = [
        "# 自动提炼规则",
        "",
        f"- 置信度阈值：`{stats['confidence_threshold']}`",
        f"- 总研读样本：`{stats['total_readings']}`",
        f"- 高置信样本：`{stats['high_confidence_readings']}`",
        "",
    ]
    for day_master in sorted(stats["day_masters"].keys()):
        payload = stats["day_masters"][day_master]
        lines.append(f"## {day_master}")
        lines.append(f"- 高置信样本数：{payload['sample_count']}")

        for item in payload["patterns"]:
            lines.append(
                f"- {item['text']}（出现率{item['occurrence_rate'] * 100:.0f}%，样本{item['count']}条）"
            )

        for item in payload["useful_gods"]:
            lines.append(
                f"- {item['text']}（出现率{item['occurrence_rate'] * 100:.0f}%，样本{item['count']}条）"
            )

        for item in payload["career_tendencies"][:5]:
            lines.append(
                f"- {item['text']}（置信度{item['average_confidence']:.2f}，样本{item['count']}条）"
            )

        for item in payload["personality_traits"][:5]:
            lines.append(
                f"- 常见性格：{item['text']}（出现率{item['occurrence_rate'] * 100:.0f}%，样本{item['count']}条）"
            )

        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    readings = load_json(args.input)
    stats = extract_rules(readings, args.confidence_threshold)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(stats), encoding="utf-8")
    write_json(args.output_stats, stats)
    print(f"高置信样本: {stats['high_confidence_readings']}")
    print(f"规则文档已写入: {args.output_md}")
    print(f"统计文件已写入: {args.output_stats}")


if __name__ == "__main__":
    main()
