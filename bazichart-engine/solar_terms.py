from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "solar_terms_1900_2100.json"
JIE_MONTH_STARTS = [
    ("立春", 1),
    ("惊蛰", 2),
    ("清明", 3),
    ("立夏", 4),
    ("芒种", 5),
    ("小暑", 6),
    ("立秋", 7),
    ("白露", 8),
    ("寒露", 9),
    ("立冬", 10),
    ("大雪", 11),
    ("小寒", 12),
]


@lru_cache(maxsize=1)
def load_solar_terms() -> dict[str, list[dict[str, str]]]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def get_term_datetime(year: int, name: str) -> datetime:
    data = load_solar_terms()
    terms = data.get(str(year))
    if terms is None:
        raise KeyError(f"缺少 {year} 年节气数据")
    for item in terms:
        if item["name"] == name:
            return datetime.fromisoformat(item["datetime"])
    raise KeyError(f"{year} 年缺少节气 {name}")


def _normalize_local_datetime(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.replace(tzinfo=None)


def resolve_bazi_year(dt: datetime) -> int:
    dt = _normalize_local_datetime(dt)
    lichun = _normalize_local_datetime(get_term_datetime(dt.year, "立春"))
    return dt.year if dt >= lichun else dt.year - 1


def resolve_bazi_month_order(dt: datetime) -> int:
    dt = _normalize_local_datetime(dt)
    candidates: list[tuple[datetime, int]] = []
    for year in (dt.year - 1, dt.year, dt.year + 1):
        try:
            for name, order in JIE_MONTH_STARTS:
                candidates.append((_normalize_local_datetime(get_term_datetime(year, name)), order))
        except KeyError:
            continue
    candidates.sort(key=lambda item: item[0])

    latest_order: int | None = None
    for start_dt, order in candidates:
        if start_dt <= dt:
            latest_order = order
        else:
            break
    if latest_order is not None:
        return latest_order

    # 仅覆盖 1900 年初极小边界。
    return 11


def list_jie_datetimes(year: int) -> list[tuple[str, datetime]]:
    return [(name, _normalize_local_datetime(get_term_datetime(year, name))) for name, _order in JIE_MONTH_STARTS]


def get_prev_jie(dt: datetime) -> tuple[str, datetime]:
    dt = _normalize_local_datetime(dt)
    candidates: list[tuple[str, datetime]] = []
    for year in (dt.year - 1, dt.year):
        candidates.extend(list_jie_datetimes(year))
    eligible = [item for item in candidates if item[1] <= dt]
    if not eligible:
        raise KeyError(f"缺少 {dt.year} 附近的上一节数据")
    return max(eligible, key=lambda item: item[1])


def get_next_jie(dt: datetime) -> tuple[str, datetime]:
    dt = _normalize_local_datetime(dt)
    candidates: list[tuple[str, datetime]] = []
    for year in (dt.year, dt.year + 1):
        candidates.extend(list_jie_datetimes(year))
    eligible = [item for item in candidates if item[1] > dt]
    if not eligible:
        raise KeyError(f"缺少 {dt.year} 附近的下一节数据")
    return min(eligible, key=lambda item: item[1])
