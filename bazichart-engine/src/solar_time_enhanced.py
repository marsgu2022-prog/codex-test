"""增强版真太阳时计算模块"""
from __future__ import annotations
import json
import math
from datetime import date, datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DST_FILE = BASE_DIR / "data" / "dst_china.json"


def _load_dst() -> dict:
    try:
        return json.loads(DST_FILE.read_text(encoding="utf-8"))["years"]
    except Exception:
        return {}


def is_dst(year: int, month: int, day: int) -> bool:
    """判断该日期是否在中国夏令时期间（1986-1991）"""
    dst_data = _load_dst()
    key = str(year)
    if key not in dst_data:
        return False
    info = dst_data[key]
    d = date(year, month, day)
    start = date.fromisoformat(info["start"])
    end = date.fromisoformat(info["end"])
    return start <= d < end


def calculate_equation_of_time(year: int, month: int, day: int) -> float:
    """计算均时差（equation of time），单位：分钟，精度约±30秒"""
    # 计算儒略日
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    # 以2000年1月1日为基准的天数
    n = jdn - 2451545.0
    # 几何平均经度（度）
    L0 = (280.46646 + 36000.76983 * n / 36525) % 360
    # 平均近点角（度）
    M = (357.52911 + 35999.05029 * n / 36525) % 360
    M_rad = math.radians(M)
    # 黄道倾角（度）
    e = 0.016708634 - 0.000042037 * n / 36525
    # 方程中心（度）
    C = (1.914602 - 0.004817 * n / 36525) * math.sin(M_rad) + \
        0.019993 * math.sin(2 * M_rad) + 0.000289 * math.sin(3 * M_rad)
    # 太阳真经度
    sun_lon = L0 + C
    # 升交点经度
    omega = (125.04 - 1934.136 * n / 36525) % 360
    omega_rad = math.radians(omega)
    # 视黄经
    lambda_ = sun_lon - 0.00569 - 0.00478 * math.sin(omega_rad)
    lambda_rad = math.radians(lambda_)
    # 黄道倾角
    epsilon0 = 23.439291111 - 0.013004167 * n / 36525
    epsilon = epsilon0 + 0.00256 * math.cos(omega_rad)
    epsilon_rad = math.radians(epsilon)
    # 赤经
    y_val = math.tan(epsilon_rad / 2) ** 2
    # 均时差（分钟）
    eot = 4 * math.degrees(
        y_val * math.sin(2 * math.radians(L0))
        - 2 * e * math.sin(M_rad)
        + 4 * e * y_val * math.sin(M_rad) * math.cos(2 * math.radians(L0))
        - 0.5 * y_val ** 2 * math.sin(4 * math.radians(L0))
        - 1.25 * e ** 2 * math.sin(2 * M_rad)
    )
    return eot


def calculate_true_solar_time(
    year: int,
    month: int,
    day: int,
    hour_float: float,
    longitude: float,
    check_dst: bool = True,
) -> dict:
    """
    计算真太阳时

    参数：
    - year/month/day: 公历日期
    - hour_float: 浮点小时（14.5 = 14:30）
    - longitude: 出生地经度
    - check_dst: 是否检查夏令时

    返回：{
        original_time, true_solar_time,
        longitude_offset_minutes, equation_of_time_minutes,
        dst_applied, total_offset_minutes
    }
    """
    # 1. 经度时差（分钟）
    lng_offset = (longitude - 120.0) * 4.0

    # 2. 均时差
    eot = calculate_equation_of_time(year, month, day)

    # 3. 夏令时
    dst_applied = False
    dst_offset = 0.0
    if check_dst and is_dst(year, month, day):
        dst_offset = -60.0
        dst_applied = True

    # 4. 总校正（分钟）
    total_offset = lng_offset + eot + dst_offset

    # 5. 计算真太阳时
    total_minutes = hour_float * 60 + total_offset
    # 处理跨天
    total_minutes = total_minutes % (24 * 60)
    true_h = int(total_minutes // 60)
    true_m = int(total_minutes % 60)
    true_s = int((total_minutes * 60) % 60)

    orig_h = int(hour_float)
    orig_m = int((hour_float * 60) % 60)

    return {
        "original_time": f"{orig_h:02d}:{orig_m:02d}:00",
        "true_solar_time": f"{true_h:02d}:{true_m:02d}:{true_s:02d}",
        "longitude_offset_minutes": round(lng_offset, 2),
        "equation_of_time_minutes": round(eot, 2),
        "dst_applied": dst_applied,
        "total_offset_minutes": round(total_offset, 2),
    }


def hour_float_to_dizhi(hour_float: float, early_zi: bool = False) -> str:
    """浮点小时转地支时辰"""
    DIZHI_HOURS = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    h = int(hour_float)
    if early_zi:
        # 早子时：23:00-00:00 为子时（当天）
        if h == 23:
            return "子"
    # 标准时辰
    idx = ((h + 1) // 2) % 12
    return DIZHI_HOURS[idx]
