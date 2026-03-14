from __future__ import annotations

import importlib.util
import json
import sys
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENRICH_PATH = ROOT / "bazichart-engine" / "scripts" / "enrich_cities.py"
VALIDATE_PATH = ROOT / "bazichart-engine" / "scripts" / "validate_cities.py"

ENRICH_SPEC = importlib.util.spec_from_file_location("enrich_cities", ENRICH_PATH)
ENRICH_MODULE = importlib.util.module_from_spec(ENRICH_SPEC)
assert ENRICH_SPEC.loader is not None
sys.modules[ENRICH_SPEC.name] = ENRICH_MODULE
ENRICH_SPEC.loader.exec_module(ENRICH_MODULE)

VALIDATE_SPEC = importlib.util.spec_from_file_location("validate_cities", VALIDATE_PATH)
VALIDATE_MODULE = importlib.util.module_from_spec(VALIDATE_SPEC)
assert VALIDATE_SPEC.loader is not None
sys.modules[VALIDATE_SPEC.name] = VALIDATE_MODULE
VALIDATE_SPEC.loader.exec_module(VALIDATE_MODULE)


class DummyFinder:
    def timezone_at(self, *, lat, lng):
        return "Asia/Shanghai" if lat > 30 else None

    def closest_timezone_at(self, *, lat, lng):
        return "UTC"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")


def test_enrich_countries_prefers_geonames_match_and_writes_country_files(tmp_path, monkeypatch):
    source_dir = tmp_path / "cities_data"
    output_dir = tmp_path / "enriched_cities"
    geonames_path = tmp_path / "cities1000.txt"
    source_dir.mkdir(parents=True, exist_ok=True)

    (source_dir / "cn.json").write_text(
        json.dumps(
            {
                "country_code": "CN",
                "country_name": "中国",
                "cities": [
                    {"name": "上海", "name_en": "Shanghai", "province": "上海市"},
                    {"name": "杭州", "name_en": "Hangzhou", "province": "浙江省"},
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_text(
        geonames_path,
        """
        1796236	Hangzhou	Hangzhou	杭州,杭州市	30.2936	120.1614	P	PPLA2	CN		ZJ		00		7642147	10	8	Asia/Shanghai	2024-01-01
        1796231	Shanghai	Shanghai	上海	31.2222	121.4581	P	PPLA	CN		SH		00		24183300	10	8	Asia/Shanghai	2024-01-01
        """,
    )

    monkeypatch.setattr(ENRICH_MODULE, "get_timezonefinder", lambda: DummyFinder())
    summary = ENRICH_MODULE.enrich_countries(source_dir, output_dir, tmp_path / ".cache", geonames_path)

    assert summary["countries"] == 1
    assert summary["total_cities"] == 2
    assert summary["completed_cities"] == 2

    payload = json.loads((output_dir / "cn.json").read_text(encoding="utf-8"))
    assert payload["country_code"] == "CN"
    assert payload["cities"][0]["latitude"] == 31.2222
    assert payload["cities"][0]["longitude"] == 121.4581
    assert payload["cities"][0]["timezone"] == "Asia/Shanghai"
    assert payload["cities"][1]["latitude"] == 30.2936


def test_normalize_country_payload_splits_continent_city_list_by_country():
    payload = [
        {
            "nameZh": "上海",
            "nameEn": "Shanghai",
            "country": "CN",
            "countryZh": "中国",
            "admin1Zh": "上海市",
            "lat": 31.2304,
            "lng": 121.4737,
            "timezone": "Asia/Shanghai",
        },
        {
            "nameZh": "东京",
            "nameEn": "Tokyo",
            "country": "JP",
            "countryZh": "日本",
            "admin1Zh": "东京都",
            "lat": 35.6764,
            "lng": 139.6500,
            "timezone": "Asia/Tokyo",
        },
    ]

    countries = ENRICH_MODULE.normalize_country_payload(payload, "cities-asia.json")
    assert len(countries) == 2
    codes = sorted(item["country_code"] for item in countries)
    assert codes == ["CN", "JP"]


def test_enrich_city_uses_timezonefinder_when_timezone_missing(monkeypatch):
    monkeypatch.setattr(ENRICH_MODULE, "get_timezonefinder", lambda: DummyFinder())
    city = {
        "name": "测试城",
        "name_en": "Test City",
        "province": "测试省",
        "latitude": 31.2304,
        "longitude": 121.4737,
        "timezone": "",
    }

    enriched = ENRICH_MODULE.enrich_city(city, "CN", {}, DummyFinder())
    assert enriched["latitude"] == 31.2304
    assert enriched["longitude"] == 121.4737
    assert enriched["timezone"] == "Asia/Shanghai"


def test_validate_directory_reports_invalid_timezone(tmp_path):
    source_dir = tmp_path / "enriched_cities"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "cn.json").write_text(
        json.dumps(
            {
                "country_code": "CN",
                "country_name": "中国",
                "cities": [
                    {
                        "name": "上海",
                        "name_en": "Shanghai",
                        "province": "上海市",
                        "latitude": 31.2304,
                        "longitude": 121.4737,
                        "timezone": "Asia/Shanghai",
                    },
                    {
                        "name": "测试城",
                        "name_en": "Test City",
                        "province": "测试省",
                        "latitude": 999,
                        "longitude": 121.0,
                        "timezone": "Bad/Timezone",
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = VALIDATE_MODULE.validate_directory(source_dir)
    assert summary["countries"] == 1
    assert summary["total_cities"] == 2
    assert summary["complete_cities"] == 1
    assert summary["invalid_cities"] == 1
    assert summary["reports"][0]["invalid_samples"][0]["issues"] == ["latitude", "timezone"]
