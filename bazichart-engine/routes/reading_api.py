"""解读API路由"""
from __future__ import annotations
import json
import uuid
import sqlite3
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "users.db"

router = APIRouter()


class FreeReadingRequest(BaseModel):
    gender: str
    calendar: str = "solar"
    year: int
    month: int
    day: int
    hour: Optional[float] = None
    country: str = "CN"
    province: str = ""
    city: str = ""
    county: str = ""
    early_zi: bool = False
    dst: bool = False


@router.post("/reading/free")
async def free_reading(payload: FreeReadingRequest, request: Request):
    """免费解读接口——不需要登录"""
    try:
        # 动态加载模块
        import sys
        if str(BASE_DIR) not in sys.path:
            sys.path.insert(0, str(BASE_DIR))
        if str(BASE_DIR / "src") not in sys.path:
            sys.path.insert(0, str(BASE_DIR / "src"))

        # 城市经纬度查询
        try:
            from city_lookup import lookup_location
        except ImportError:
            raise HTTPException(status_code=503, detail="SERVICE_UNAVAILABLE")
        location = lookup_location(payload.province, payload.city, payload.county)
        latitude = location["lat"] if location else 39.9
        longitude = location["lng"] if location else 116.4

        # 真太阳时校正
        try:
            from solar_time_enhanced import calculate_true_solar_time, hour_float_to_dizhi
        except ImportError:
            raise HTTPException(status_code=503, detail="SERVICE_UNAVAILABLE")
        true_solar_info = None
        actual_hour = payload.hour
        if payload.hour is not None:
            true_solar_info = calculate_true_solar_time(
                payload.year, payload.month, payload.day,
                payload.hour, longitude, check_dst=True
            )
            # 转换为真太阳时小时数
            tst = true_solar_info["true_solar_time"]
            h, m, s = tst.split(":")
            actual_hour = int(h) + int(m) / 60 + int(s) / 3600

        # 调用现有解读引擎
        try:
            from ai_interpreter import get_full_reading
        except ImportError:
            raise HTTPException(status_code=503, detail="SERVICE_UNAVAILABLE")
        reading_result = get_full_reading(
            year=payload.year,
            month=payload.month,
            day=payload.day,
            hour=actual_hour,
            gender=payload.gender,
            longitude=longitude,
            latitude=latitude,
            calendar=payload.calendar,
        )

        # 生成reading_id
        reading_id = str(uuid.uuid4())[:8]

        # 保存到数据库
        try:
            from auth import init_users_db
            init_users_db()
            conn = sqlite3.connect(str(DB_FILE))
            conn.execute(
                "INSERT INTO readings (id, input_data, bazi_result, reading_text) VALUES (?,?,?,?)",
                (reading_id, json.dumps(payload.dict()), json.dumps(reading_result.get("bazi", {})),
                 reading_result.get("reading_text", ""))
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

        return {
            "bazi": reading_result.get("bazi", {}),
            "ziwei_used": reading_result.get("ziwei_used", False),
            "huangji_used": reading_result.get("huangji_used", False),
            "cross_used": reading_result.get("cross_used", False),
            "confidence": reading_result.get("confidence", 0.8),
            "true_solar_time": true_solar_info["true_solar_time"] if true_solar_info else None,
            "latitude": latitude,
            "longitude": longitude,
            "reading_text": reading_result.get("reading_text", ""),
            "reading_id": reading_id,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/cities/{country}")
async def get_provinces(country: str):
    """获取省份列表"""
    if country != "CN":
        return []
    import sys
    if str(BASE_DIR / "src") not in sys.path:
        sys.path.insert(0, str(BASE_DIR / "src"))
    try:
        from city_lookup import get_provinces
    except ImportError:
        raise HTTPException(status_code=503, detail="SERVICE_UNAVAILABLE")
    try:
        return get_provinces()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cities/{country}/{province}")
async def get_cities(country: str, province: str):
    """获取城市列表"""
    import sys
    if str(BASE_DIR / "src") not in sys.path:
        sys.path.insert(0, str(BASE_DIR / "src"))
    try:
        from city_lookup import get_cities
    except ImportError:
        raise HTTPException(status_code=503, detail="SERVICE_UNAVAILABLE")
    try:
        return get_cities(province)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cities/{country}/{province}/{city}")
async def get_counties(country: str, province: str, city: str):
    """获取区县列表并返回经纬度"""
    import sys
    if str(BASE_DIR / "src") not in sys.path:
        sys.path.insert(0, str(BASE_DIR / "src"))
    try:
        from city_lookup import get_counties, lookup_location
    except ImportError:
        raise HTTPException(status_code=503, detail="SERVICE_UNAVAILABLE")
    try:
        counties = get_counties(province, city)
        location = lookup_location(province, city)
        return {
            "counties": counties,
            "location": location
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
