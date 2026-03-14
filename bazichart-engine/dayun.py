from __future__ import annotations

from datetime import datetime, timedelta


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


def _ganzhi_for_year(year: int) -> tuple[str, str]:
    base_year = 1984
    offset = year - base_year
    return TIANGAN[offset % 10], DIZHI[offset % 12]


def _month_pillar(month: int) -> tuple[str, str]:
    return TIANGAN[month % 10], DIZHI[month % 12]


def _round_trip_days(birth_time: datetime, forward: bool) -> float:
    current = birth_time
    if forward:
        candidates = []
        for day in (6, 21):
            candidate = datetime(current.year, current.month, day)
            if candidate > current:
                candidates.append(candidate)
        if not candidates:
            year = current.year + (1 if current.month == 12 else 0)
            month = 1 if current.month == 12 else current.month + 1
            target = datetime(year, month, 6)
        else:
            target = min(candidates)
        return (target - current).total_seconds() / 86400

    candidates = []
    for day in (6, 21):
        candidate = datetime(current.year, current.month, day)
        if candidate < current:
            candidates.append(candidate)
    if not candidates:
        year = current.year - (1 if current.month == 1 else 0)
        month = 12 if current.month == 1 else current.month - 1
        target = datetime(year, month, 21)
    else:
        target = max(candidates)
    return (current - target).total_seconds() / 86400


def _start_age(year: int, month: int, day: int, hour: int, forward: bool) -> int:
    birth_time = datetime(year, month, day, hour)
    days_delta = _round_trip_days(birth_time, forward=forward)
    return max(1, round(days_delta / 3.0))


def _direction(year_stem: str, gender: str) -> int:
    normalized_gender = gender.lower()
    is_male = normalized_gender in {"male", "男"}
    is_yang_year = year_stem in YANG_STEMS
    return 1 if (is_yang_year and is_male) or (not is_yang_year and not is_male) else -1


def _wuxing(gan: str, zhi: str) -> str:
    return f"{WUXING_MAP[gan]}{WUXING_MAP[zhi]}"


def calculate_dayun(year, month, day, hour, gender) -> list:
    year_stem, _year_branch = _ganzhi_for_year(int(year))
    month_stem, month_branch = _month_pillar(int(month))
    direction = _direction(year_stem, str(gender))
    start_age = _start_age(int(year), int(month), int(day), int(hour), forward=direction == 1)

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
