from __future__ import annotations

from datetime import datetime, timedelta
import math


SHICHEN_RANGES = [
    ("子时", 23, 1),
    ("丑时", 1, 3),
    ("寅时", 3, 5),
    ("卯时", 5, 7),
    ("辰时", 7, 9),
    ("巳时", 9, 11),
    ("午时", 11, 13),
    ("未时", 13, 15),
    ("申时", 15, 17),
    ("酉时", 17, 19),
    ("戌时", 19, 21),
    ("亥时", 21, 23),
]


def _format_time(target: datetime) -> str:
    return target.strftime("%H:%M")


def _resolve_shichen(target: datetime) -> str:
    hour_value = target.hour + target.minute / 60.0
    for name, start, end in SHICHEN_RANGES:
        if start > end:
            if hour_value >= start or hour_value < end:
                return name
        elif start <= hour_value < end:
            return name
    return "子时"


def calculate_true_solar_time(year, month, day, hour, minute, longitude) -> dict:
    base_time = datetime(int(year), int(month), int(day), int(hour), int(minute))
    day_of_year = base_time.timetuple().tm_yday
    b_value = math.radians((360 / 365.0) * (day_of_year - 81))
    equation_of_time = 9.87 * math.sin(2 * b_value) - 7.53 * math.cos(b_value) - 1.5 * math.sin(b_value)
    longitude_correction = (float(longitude) - 120.0) * 4.0
    corrected_time = base_time + timedelta(minutes=equation_of_time + longitude_correction)

    original_shichen = _resolve_shichen(base_time)
    corrected_shichen = _resolve_shichen(corrected_time)

    return {
        "beijing_time": _format_time(base_time),
        "longitude": round(float(longitude), 2),
        "equation_of_time": round(equation_of_time, 2),
        "longitude_correction": round(longitude_correction, 2),
        "true_solar_time": _format_time(corrected_time),
        "corrected_datetime": corrected_time.isoformat(timespec="minutes"),
        "original_shichen": original_shichen,
        "corrected_shichen": corrected_shichen,
        "shichen_changed": original_shichen != corrected_shichen,
    }
