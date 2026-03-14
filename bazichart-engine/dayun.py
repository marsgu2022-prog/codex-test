from __future__ import annotations

from datetime import datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


TIANGAN = "甲乙丙丁戊己庚辛壬癸"
DIZHI = "子丑寅卯辰巳午未申酉戌亥"
YANG_STEMS = {"甲", "丙", "戊", "庚", "壬"}
WUXING_MAP = {
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
    "子": "水",
    "丑": "土",
    "寅": "木",
    "卯": "木",
    "辰": "土",
    "巳": "火",
    "午": "火",
    "未": "土",
    "申": "金",
    "酉": "金",
    "戌": "土",
    "亥": "水",
}
YEAR_BASE = 1984
MONTH_START_STEM_MAP = {
    "甲": "丙",
    "己": "丙",
    "乙": "戊",
    "庚": "戊",
    "丙": "庚",
    "辛": "庚",
    "丁": "壬",
    "壬": "壬",
    "戊": "甲",
    "癸": "甲",
}
MONTH_BRANCHES = "寅卯辰巳午未申酉戌亥子丑"


def _load_local_module(module_name: str, file_path: Path):
    spec = spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块: {file_path}")
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


BASE_DIR = Path(__file__).resolve().parent
SOLAR_TERMS_MODULE = _load_local_module("bazichart_engine_dayun_solar_terms", BASE_DIR / "solar_terms.py")


def _ganzhi_for_year(year: int) -> tuple[str, str]:
    offset = year - YEAR_BASE
    return TIANGAN[offset % 10], DIZHI[offset % 12]


def _month_pillar(dt: datetime) -> tuple[str, str]:
    bazi_year = SOLAR_TERMS_MODULE.resolve_bazi_year(dt)
    year_stem, _year_branch = _ganzhi_for_year(bazi_year)
    month_order = SOLAR_TERMS_MODULE.resolve_bazi_month_order(dt)
    start_stem = MONTH_START_STEM_MAP[year_stem]
    stem = TIANGAN[(TIANGAN.index(start_stem) + month_order - 1) % 10]
    branch = MONTH_BRANCHES[month_order - 1]
    return stem, branch


def _round_trip_days(birth_time: datetime, forward: bool) -> float:
    if forward:
        _name, target = SOLAR_TERMS_MODULE.get_next_jie(birth_time)
        return (target - birth_time).total_seconds() / 86400
    _name, target = SOLAR_TERMS_MODULE.get_prev_jie(birth_time)
    return (birth_time - target).total_seconds() / 86400


def _start_age(birth_time: datetime, forward: bool) -> int:
    days_delta = _round_trip_days(birth_time, forward=forward)
    return max(1, round(days_delta / 3.0))


def _direction(year_stem: str, gender: str) -> int:
    normalized_gender = gender.lower()
    is_male = normalized_gender in {"male", "男"}
    is_yang_year = year_stem in YANG_STEMS
    return 1 if (is_yang_year and is_male) or (not is_yang_year and not is_male) else -1


def _wuxing(gan: str, zhi: str) -> str:
    return f"{WUXING_MAP[gan]}{WUXING_MAP[zhi]}"


def calculate_dayun(year, month, day, hour, gender, minute=0, solar_time_info=None) -> list:
    if solar_time_info and solar_time_info.get("corrected_datetime"):
        birth_time = datetime.fromisoformat(solar_time_info["corrected_datetime"])
    else:
        birth_time = datetime(int(year), int(month), int(day), int(hour), int(minute))

    bazi_year = SOLAR_TERMS_MODULE.resolve_bazi_year(birth_time)
    year_stem, _year_branch = _ganzhi_for_year(bazi_year)
    month_stem, month_branch = _month_pillar(birth_time)
    direction = _direction(year_stem, str(gender))
    start_age = _start_age(birth_time, forward=direction == 1)

    gan_index = TIANGAN.index(month_stem)
    zhi_index = DIZHI.index(month_branch)
    result = []
    for step in range(8):
        gan = TIANGAN[(gan_index + direction * (step + 1)) % 10]
        zhi = DIZHI[(zhi_index + direction * (step + 1)) % 12]
        current_start_age = start_age + step * 10
        result.append(
            {
                "start_age": current_start_age,
                "end_age": current_start_age + 9,
                "tiangan": gan,
                "dizhi": zhi,
                "wuxing": _wuxing(gan, zhi),
            }
        )
    return result


def calculate_liunian(birth_year, start_year, count=10) -> list:
    result = []
    for target_year in range(int(start_year), int(start_year) + int(count)):
        gan, zhi = _ganzhi_for_year(target_year)
        result.append(
            {
                "year": target_year,
                "tiangan": gan,
                "dizhi": zhi,
                "wuxing": _wuxing(gan, zhi),
            }
        )
    return result
