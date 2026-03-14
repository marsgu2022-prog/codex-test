#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import ephem


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = BASE_DIR / "data" / "solar_terms_1900_2100.json"
BEIJING_TZ = timezone(timedelta(hours=8))
UTC = timezone.utc
START_YEAR = 1900
END_YEAR = 2100


@dataclass(frozen=True)
class SolarTermSpec:
    name: str
    name_en: str
    solar_longitude: int
    approx_month: int
    approx_day: int


SOLAR_TERM_SPECS = [
    SolarTermSpec("小寒", "Minor Cold", 285, 1, 6),
    SolarTermSpec("大寒", "Major Cold", 300, 1, 20),
    SolarTermSpec("立春", "Start of Spring", 315, 2, 4),
    SolarTermSpec("雨水", "Rain Water", 330, 2, 19),
    SolarTermSpec("惊蛰", "Awakening of Insects", 345, 3, 5),
    SolarTermSpec("春分", "Spring Equinox", 0, 3, 20),
    SolarTermSpec("清明", "Pure Brightness", 15, 4, 4),
    SolarTermSpec("谷雨", "Grain Rain", 30, 4, 20),
    SolarTermSpec("立夏", "Start of Summer", 45, 5, 5),
    SolarTermSpec("小满", "Grain Full", 60, 5, 21),
    SolarTermSpec("芒种", "Grain in Ear", 75, 6, 5),
    SolarTermSpec("夏至", "Summer Solstice", 90, 6, 21),
    SolarTermSpec("小暑", "Minor Heat", 105, 7, 7),
    SolarTermSpec("大暑", "Major Heat", 120, 7, 23),
    SolarTermSpec("立秋", "Start of Autumn", 135, 8, 7),
    SolarTermSpec("处暑", "Limit of Heat", 150, 8, 23),
    SolarTermSpec("白露", "White Dew", 165, 9, 7),
    SolarTermSpec("秋分", "Autumn Equinox", 180, 9, 23),
    SolarTermSpec("寒露", "Cold Dew", 195, 10, 8),
    SolarTermSpec("霜降", "Frost Descent", 210, 10, 23),
    SolarTermSpec("立冬", "Start of Winter", 225, 11, 7),
    SolarTermSpec("小雪", "Minor Snow", 240, 11, 22),
    SolarTermSpec("大雪", "Major Snow", 255, 12, 7),
    SolarTermSpec("冬至", "Winter Solstice", 270, 12, 21),
]


def compute_solar_longitude(dt_utc: datetime) -> float:
    if dt_utc.tzinfo is None:
        raise ValueError("dt_utc 必须带时区")
    dt_utc = dt_utc.astimezone(UTC)
    date = ephem.Date(dt_utc)
    sun = ephem.Sun(date)
    # 节气以太阳几何黄经划分，使用 date-of-date 坐标系避免 J2000 偏移。
    equatorial = ephem.Equatorial(sun.g_ra, sun.g_dec, epoch=date)
    ecliptic = ephem.Ecliptic(equatorial)
    return float(ecliptic.lon) * 180.0 / ephem.pi % 360.0


def signed_angle_diff(current: float, target: float) -> float:
    return ((current - target + 180.0) % 360.0) - 180.0


def round_to_minute(dt: datetime) -> datetime:
    if dt.second >= 30 or dt.microsecond >= 500_000:
        dt = dt + timedelta(minutes=1)
    return dt.replace(second=0, microsecond=0)


def build_search_center(year: int, spec: SolarTermSpec, previous_dt_utc: datetime | None = None) -> datetime:
    if previous_dt_utc is not None:
        return previous_dt_utc + timedelta(days=15.22)
    return datetime(year, spec.approx_month, spec.approx_day, 12, 0, tzinfo=BEIJING_TZ).astimezone(UTC)


def locate_solar_term_utc(year: int, spec: SolarTermSpec, previous_dt_utc: datetime | None = None) -> datetime:
    center = build_search_center(year, spec, previous_dt_utc)
    window_start = center - timedelta(days=4)
    window_end = center + timedelta(days=4)
    step = timedelta(hours=6)

    left = window_start
    left_diff = signed_angle_diff(compute_solar_longitude(left), spec.solar_longitude)
    cursor = left + step

    while cursor <= window_end:
        right_diff = signed_angle_diff(compute_solar_longitude(cursor), spec.solar_longitude)
        if left_diff == 0 or right_diff == 0 or (left_diff < 0 <= right_diff) or (left_diff > 0 >= right_diff):
            right = cursor
            while (right - left).total_seconds() > 1:
                middle = left + (right - left) / 2
                middle_diff = signed_angle_diff(compute_solar_longitude(middle), spec.solar_longitude)
                if left_diff == 0 or (left_diff < 0 <= middle_diff) or (left_diff > 0 >= middle_diff):
                    right = middle
                else:
                    left = middle
                    left_diff = middle_diff
            return right.astimezone(UTC)
        left = cursor
        left_diff = right_diff
        cursor += step

    raise RuntimeError(f"未找到 {year} 年 {spec.name} 的节气时刻")


def build_year_terms(year: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    previous_dt_utc: datetime | None = None
    for spec in SOLAR_TERM_SPECS:
        exact_utc = locate_solar_term_utc(year, spec, previous_dt_utc=previous_dt_utc)
        previous_dt_utc = exact_utc
        local_dt = round_to_minute(exact_utc.astimezone(BEIJING_TZ))
        results.append(
            {
                "name": spec.name,
                "name_en": spec.name_en,
                "datetime": local_dt.isoformat(),
                "solar_longitude": spec.solar_longitude,
            }
        )
    return results


def build_dataset(start_year: int = START_YEAR, end_year: int = END_YEAR) -> dict[str, list[dict[str, Any]]]:
    return {str(year): build_year_terms(year) for year in range(start_year, end_year + 1)}


def write_dataset(dataset: dict[str, list[dict[str, Any]]], output_path: Path = DEFAULT_OUTPUT_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def main() -> None:
    dataset = build_dataset()
    output_path = write_dataset(dataset)
    print(f"已生成节气数据：{output_path}")
    print(f"年份范围：{START_YEAR}-{END_YEAR}")
    print(f"总年份数：{len(dataset)}")
    print(f"每年节气数：{len(SOLAR_TERM_SPECS)}")


if __name__ == "__main__":
    main()
