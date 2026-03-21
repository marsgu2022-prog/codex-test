"""城市查询模块——基于现有 data/cities-china.json 构建三级联动"""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
CHINA_CITIES_FILE = BASE_DIR / "data" / "cities-china.json"


@lru_cache(maxsize=1)
def _load_china_cities() -> list[dict]:
    return json.loads(CHINA_CITIES_FILE.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _build_index() -> dict:
    """构建省→市→城市列表的三级索引"""
    cities = _load_china_cities()
    index = {}
    for c in cities:
        province = c.get("admin1Zh", "")
        city_name = c.get("nameZh", "")
        if not province or not city_name:
            continue
        if province not in index:
            index[province] = {}
        # 将城市同时作为市和县（因为数据是市级）
        if city_name not in index[province]:
            index[province][city_name] = {
                "lat": c.get("lat"),
                "lng": c.get("lng"),
                "timezone": c.get("timezone", "Asia/Shanghai"),
            }
    return index


def get_provinces() -> list[str]:
    """返回省份列表"""
    index = _build_index()
    # 排序：直辖市优先，然后按拼音
    priority = ["北京市", "上海市", "天津市", "重庆市"]
    provinces = list(index.keys())
    result = [p for p in priority if p in provinces]
    result += sorted([p for p in provinces if p not in priority])
    return result


def get_cities(province: str) -> list[str]:
    """返回某省的城市列表"""
    index = _build_index()
    if province not in index:
        return []
    return sorted(index[province].keys())


def get_counties(province: str, city: str) -> list[dict]:
    """
    返回某市的区县列表（当前数据粒度到市级）
    返回格式：[{"name": "...", "lat": ..., "lng": ...}]
    """
    index = _build_index()
    if province not in index or city not in index[province]:
        return []
    info = index[province][city]
    # 如果没有更细的区县数据，返回城市本身作为选项
    return [{"name": city, "lat": info["lat"], "lng": info["lng"]}]


def lookup_location(province: str, city: str, county: Optional[str] = None) -> Optional[dict]:
    """查询经纬度"""
    index = _build_index()
    if province in index and city in index[province]:
        info = index[province][city]
        return {
            "lat": info["lat"],
            "lng": info["lng"],
            "timezone": info["timezone"],
            "province": province,
            "city": city,
            "county": county or city,
        }
    return None
