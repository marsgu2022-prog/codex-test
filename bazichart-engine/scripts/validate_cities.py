#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def iter_country_files(source_dir: Path) -> list[Path]:
    return sorted(path for path in source_dir.glob("*.json") if path.name != "validation_report.json")


def is_valid_timezone(value: str) -> bool:
    if not value:
        return False
    try:
        ZoneInfo(value)
        return True
    except ZoneInfoNotFoundError:
        return False


def validate_country(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cities = payload.get("cities", [])
    invalid = []
    complete = 0

    for index, city in enumerate(cities):
        latitude = city.get("latitude")
        longitude = city.get("longitude")
        timezone = city.get("timezone", "")
        issues = []
        if latitude is None or not (-90 <= float(latitude) <= 90):
            issues.append("latitude")
        if longitude is None or not (-180 <= float(longitude) <= 180):
            issues.append("longitude")
        if not is_valid_timezone(timezone):
            issues.append("timezone")
        if issues:
            invalid.append({"index": index, "name": city.get("name", ""), "issues": issues})
        else:
            complete += 1

    return {
        "country_code": payload.get("country_code", ""),
        "country_name": payload.get("country_name", ""),
        "file": path.name,
        "city_count": len(cities),
        "complete_count": complete,
        "invalid_count": len(invalid),
        "invalid_samples": invalid[:20],
    }


def validate_directory(source_dir: Path) -> dict:
    files = iter_country_files(source_dir)
    reports = [validate_country(path) for path in files]
    total_cities = sum(item["city_count"] for item in reports)
    total_complete = sum(item["complete_count"] for item in reports)
    total_invalid = sum(item["invalid_count"] for item in reports)
    return {
        "countries": len(reports),
        "total_cities": total_cities,
        "complete_cities": total_complete,
        "invalid_cities": total_invalid,
        "coverage_ratio": (total_complete / total_cities) if total_cities else 0.0,
        "reports": reports,
    }


def write_report(source_dir: Path, summary: dict) -> Path:
    target = source_dir / "validation_report.json"
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def build_parser() -> argparse.ArgumentParser:
    root_dir = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="校验补全后的城市数据")
    parser.add_argument("--source-dir", type=Path, default=root_dir / "enriched_cities", help="待校验目录")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.source_dir.exists():
        print(f"目录不存在：{args.source_dir}", file=sys.stderr)
        return 1

    summary = validate_directory(args.source_dir)
    report_path = write_report(args.source_dir, summary)
    print(f"国家文件数: {summary['countries']}")
    print(f"城市总数: {summary['total_cities']}")
    print(f"通过校验: {summary['complete_cities']}")
    print(f"无效城市: {summary['invalid_cities']}")
    print(f"覆盖率: {summary['coverage_ratio']:.2%}")
    print(f"报告文件: {report_path}")
    return 0 if summary["invalid_cities"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
