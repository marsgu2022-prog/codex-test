#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from lunar_python import Solar

from generate_solar_terms import DEFAULT_OUTPUT_PATH, END_YEAR, SOLAR_TERM_SPECS, START_YEAR


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_PATH = BASE_DIR / "data" / "solar_terms_validation_report.json"
BEIJING_TZ = timezone(timedelta(hours=8))
TERM_ORDER = [spec.name for spec in SOLAR_TERM_SPECS]
TERM_SET = set(TERM_ORDER)
MAX_ENGINE_DELTA_MINUTES = 2.0
ALIAS_TO_NAME = {
    "XIAO_HAN": "小寒",
    "DA_HAN": "大寒",
    "LI_CHUN": "立春",
    "YU_SHUI": "雨水",
    "JING_ZHE": "惊蛰",
    "CHUN_FEN": "春分",
    "QING_MING": "清明",
    "GU_YU": "谷雨",
    "LI_XIA": "立夏",
    "XIAO_MAN": "小满",
    "MANG_ZHONG": "芒种",
    "XIA_ZHI": "夏至",
    "XIAO_SHU": "小暑",
    "DA_SHU": "大暑",
    "LI_QIU": "立秋",
    "CHU_SHU": "处暑",
    "BAI_LU": "白露",
    "QIU_FEN": "秋分",
    "HAN_LU": "寒露",
    "SHUANG_JIANG": "霜降",
    "LI_DONG": "立冬",
    "XIAO_XUE": "小雪",
    "DA_XUE": "大雪",
    "DONG_ZHI": "冬至",
}
# 香港天文台《年历》公开节气时刻抽样，用于分钟级 spot check。
HKO_SAMPLE_REFERENCES = {
    2024: {
        "小寒": "2024-01-06T04:49:00+08:00",
        "立春": "2024-02-04T16:27:00+08:00",
        "惊蛰": "2024-03-05T10:23:00+08:00",
        "清明": "2024-04-04T15:02:00+08:00",
        "立夏": "2024-05-05T08:10:00+08:00",
        "芒种": "2024-06-05T12:10:00+08:00",
        "小暑": "2024-07-06T22:20:00+08:00",
        "立秋": "2024-08-07T08:09:00+08:00",
        "白露": "2024-09-07T11:11:00+08:00",
        "寒露": "2024-10-08T03:00:00+08:00",
        "立冬": "2024-11-07T06:20:00+08:00",
        "大雪": "2024-12-06T23:17:00+08:00",
    }
}


def parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def load_dataset(path: Path = DEFAULT_OUTPUT_PATH) -> dict[str, list[dict[str, Any]]]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_engine_reference_terms(year: int) -> dict[str, datetime]:
    table = Solar.fromYmdHms(year, 1, 1, 0, 0, 0).getLunar().getJieQiTable()
    results: dict[str, datetime] = {}
    for raw_name, solar in table.items():
        name = ALIAS_TO_NAME.get(raw_name, raw_name)
        if name not in TERM_SET:
            continue
        dt = datetime.strptime(solar.toYmdHms(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=BEIJING_TZ)
        if dt.year == year:
            results[name] = dt
    return results


def validate_dataset_structure(dataset: dict[str, list[dict[str, Any]]]) -> list[str]:
    issues: list[str] = []
    years = sorted(int(year) for year in dataset)
    expected_years = list(range(START_YEAR, END_YEAR + 1))
    if years != expected_years:
        issues.append("年份范围不完整")

    for year, terms in dataset.items():
        if len(terms) != len(SOLAR_TERM_SPECS):
            issues.append(f"{year} 年节气数量异常")
            continue
        names = [item.get("name") for item in terms]
        if names != TERM_ORDER:
            issues.append(f"{year} 年节气顺序异常")
        for item in terms:
            dt = parse_iso_datetime(item["datetime"])
            if dt.tzinfo is None or dt.utcoffset() != timedelta(hours=8):
                issues.append(f"{year} 年 {item.get('name')} 时区异常")
    return issues


def validate_term_intervals(dataset: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    interval_days: list[float] = []
    violations: list[dict[str, Any]] = []
    for year, terms in dataset.items():
        datetimes = [parse_iso_datetime(item["datetime"]) for item in terms]
        for left, right, right_item in zip(datetimes, datetimes[1:], terms[1:]):
            days = (right - left).total_seconds() / 86400
            interval_days.append(days)
            if not 13 <= days <= 17:
                violations.append({"year": year, "term": right_item["name"], "interval_days": round(days, 4)})
    return {
        "count": len(interval_days),
        "average_days": round(mean(interval_days), 4) if interval_days else 0.0,
        "min_days": round(min(interval_days), 4) if interval_days else 0.0,
        "max_days": round(max(interval_days), 4) if interval_days else 0.0,
        "violations": violations,
    }


def compare_with_engine(dataset: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    diffs: list[float] = []
    samples: list[dict[str, Any]] = []
    for year_key in sorted(dataset, key=int):
        year = int(year_key)
        generated = {item["name"]: parse_iso_datetime(item["datetime"]) for item in dataset[year_key]}
        reference = get_engine_reference_terms(year)
        for name in TERM_ORDER:
            delta_minutes = abs((generated[name] - reference[name]).total_seconds()) / 60
            diffs.append(delta_minutes)
            if year in {1900, 1950, 2000, 2024, 2100} and name in {"小寒", "立春", "清明", "立秋", "冬至"}:
                samples.append({"year": year, "term": name, "delta_minutes": round(delta_minutes, 4)})
    return {
        "count": len(diffs),
        "max_delta_minutes": round(max(diffs), 4) if diffs else 0.0,
        "avg_delta_minutes": round(mean(diffs), 4) if diffs else 0.0,
        "samples": samples,
    }


def compare_with_hko_samples(dataset: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    comparisons: list[dict[str, Any]] = []
    for year, refs in HKO_SAMPLE_REFERENCES.items():
        generated = {item["name"]: parse_iso_datetime(item["datetime"]) for item in dataset[str(year)]}
        for name, raw_dt in refs.items():
            reference_dt = parse_iso_datetime(raw_dt)
            delta_minutes = abs((generated[name] - reference_dt).total_seconds()) / 60
            comparisons.append({"year": year, "term": name, "delta_minutes": round(delta_minutes, 4)})
    return {
        "count": len(comparisons),
        "max_delta_minutes": max((item["delta_minutes"] for item in comparisons), default=0.0),
        "comparisons": comparisons,
    }


def build_report(dataset: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    structure_issues = validate_dataset_structure(dataset)
    interval_report = validate_term_intervals(dataset)
    engine_report = compare_with_engine(dataset)
    hko_report = compare_with_hko_samples(dataset)
    return {
        "years": len(dataset),
        "terms_per_year": len(SOLAR_TERM_SPECS),
        "structure_issues": structure_issues,
        "interval_report": interval_report,
        "engine_comparison": engine_report,
        "hko_sample_comparison": hko_report,
        "validation_threshold_minutes": MAX_ENGINE_DELTA_MINUTES,
        "is_valid": not structure_issues
        and not interval_report["violations"]
        and engine_report["max_delta_minutes"] <= MAX_ENGINE_DELTA_MINUTES,
    }


def write_report(report: dict[str, Any], output_path: Path = DEFAULT_REPORT_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def main() -> None:
    dataset = load_dataset()
    report = build_report(dataset)
    output_path = write_report(report)
    print(f"已生成验证报告：{output_path}")
    print(f"结构问题数：{len(report['structure_issues'])}")
    print(f"间隔异常数：{len(report['interval_report']['violations'])}")
    print(f"与排盘基线最大偏差：{report['engine_comparison']['max_delta_minutes']} 分钟")
    print(f"与香港天文台样本最大偏差：{report['hko_sample_comparison']['max_delta_minutes']} 分钟")
    print(f"验证结论：{'通过' if report['is_valid'] else '失败'}")


if __name__ == "__main__":
    main()
