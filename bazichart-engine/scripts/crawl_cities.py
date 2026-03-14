#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

try:
    from opencc import OpenCC
except ImportError:  # pragma: no cover
    OpenCC = None


GEONAMES_BASE = "https://download.geonames.org/export/dump"
DATASET_URLS = {
    "cities5000.txt": f"{GEONAMES_BASE}/cities5000.zip",
    "admin1CodesASCII.txt": f"{GEONAMES_BASE}/admin1CodesASCII.txt",
    "countryInfo.txt": f"{GEONAMES_BASE}/countryInfo.txt",
    "alternateNamesV2.txt": f"{GEONAMES_BASE}/alternateNamesV2.zip",
}
CHINESE_LANGS = {"zh", "zh-cn", "zh-hans", "zh-sg", "zh-tw", "zh-hk", "zh-hant", "zht"}
SIMPLIFIED_PRIORITY = {
    "zh-cn": 0,
    "zh-hans": 1,
    "zh-sg": 2,
    "zh": 3,
    "zh-tw": 4,
    "zh-hk": 5,
    "zh-hant": 6,
    "zht": 7,
}
CONTINENT_GROUPS = {
    "AS": "asia",
    "EU": "europe",
    "NA": "americas",
    "SA": "americas",
}
SPECIAL_ADMIN1 = {
    "HK": ("HK", "香港特别行政区", "Hong Kong"),
    "MO": ("MO", "澳门特别行政区", "Macau"),
    "TW": ("TW", "台湾省", "Taiwan"),
}


@dataclass
class CityRecord:
    geonameid: str
    name: str
    asciiname: str
    alternatenames: str
    country_code: str
    admin1_code: str
    population: int
    timezone: str
    latitude: float
    longitude: float


class IdentityConverter:
    def convert(self, text: str) -> str:
        return text


def get_converter():
    if OpenCC is None:
        print("警告：未安装 opencc，繁体转简体将跳过。可安装 opencc-python-reimplemented。", file=sys.stderr)
        return IdentityConverter()
    return OpenCC("t2s")


def ensure_dataset(filename: str, cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / filename
    if target.exists():
        return target

    url = DATASET_URLS[filename]
    download_target = cache_dir / Path(url).name
    print(f"下载数据：{url}")
    urllib.request.urlretrieve(url, download_target)

    if download_target.suffix == ".zip":
        with zipfile.ZipFile(download_target) as archive:
            archive.extract(filename, cache_dir)
    elif download_target.name != filename:
        download_target.rename(target)

    return target


def safe_split(line: str, expected_parts: int) -> list[str]:
    parts = line.rstrip("\n").split("\t")
    if len(parts) < expected_parts:
        parts.extend([""] * (expected_parts - len(parts)))
    return parts


def load_cities(path: Path) -> list[CityRecord]:
    records: list[CityRecord] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue
            parts = safe_split(raw_line, 19)
            records.append(
                CityRecord(
                    geonameid=parts[0],
                    name=parts[1],
                    asciiname=parts[2],
                    alternatenames=parts[3],
                    latitude=float(parts[4]),
                    longitude=float(parts[5]),
                    country_code=parts[8],
                    admin1_code=parts[10],
                    population=int(parts[14] or 0),
                    timezone=parts[17],
                )
            )
    return records


def load_admin1(path: Path) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue
            parts = safe_split(raw_line, 4)
            full_code = parts[0]
            country_code, _, admin1_code = full_code.partition(".")
            mapping[full_code] = {
                "country": country_code,
                "code": admin1_code,
                "nameEn": parts[1],
                "nameAscii": parts[2],
                "geonameid": parts[3],
            }
    return mapping


def load_countries(path: Path) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    countries: dict[str, dict[str, str]] = {}
    geoname_to_country: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            if not raw_line.strip() or raw_line.startswith("#"):
                continue
            parts = safe_split(raw_line, 19)
            country_code = parts[0]
            geonameid = parts[16]
            countries[country_code] = {
                "code": country_code,
                "nameEn": parts[4],
                "continent": parts[8],
                "geonameid": geonameid,
            }
            if geonameid:
                geoname_to_country[geonameid] = country_code
    return countries, geoname_to_country


def candidate_score(iso_language: str, is_preferred: str, is_short: str, name: str) -> tuple[int, int, int, int]:
    return (
        SIMPLIFIED_PRIORITY.get(iso_language, 99),
        0 if is_preferred == "1" else 1,
        0 if is_short != "1" else 1,
        len(name),
    )


def load_alternate_names(path: Path, target_ids: set[str], converter) -> dict[str, str]:
    best_names: dict[str, tuple[tuple[int, int, int, int], str]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue
            parts = safe_split(raw_line, 10)
            geonameid = parts[1]
            iso_language = parts[2].lower()
            if geonameid not in target_ids or iso_language not in CHINESE_LANGS:
                continue
            name = converter.convert(parts[3].strip())
            if not name:
                continue
            score = candidate_score(iso_language, parts[4], parts[5], name)
            current = best_names.get(geonameid)
            if current is None or score < current[0]:
                best_names[geonameid] = (score, name)
    return {key: value for key, (_, value) in best_names.items()}


def choose_city_name(city: CityRecord, alternate_names: dict[str, str], converter) -> str:
    if city.geonameid in alternate_names:
        return alternate_names[city.geonameid]

    chinese_candidates = []
    for item in city.alternatenames.split(","):
        item = item.strip()
        if not item:
            continue
        converted = converter.convert(item)
        if any("\u4e00" <= char <= "\u9fff" for char in converted):
            chinese_candidates.append(converted)
    return chinese_candidates[0] if chinese_candidates else ""


def normalize_country_code(country_code: str) -> str:
    return "CN" if country_code in SPECIAL_ADMIN1 else country_code


def build_country_outputs(countries: dict[str, dict[str, str]], alternate_names: dict[str, str]) -> dict[str, dict[str, str]]:
    outputs: dict[str, dict[str, str]] = {}
    for code, country in countries.items():
        normalized = normalize_country_code(code)
        if normalized in outputs:
            continue
        name_zh = alternate_names.get(country["geonameid"], "")
        if normalized == "CN":
            name_zh = "中国"
        outputs[normalized] = {
            "code": normalized,
            "nameZh": name_zh,
            "nameEn": "China" if normalized == "CN" else country["nameEn"],
            "continent": countries["CN"]["continent"] if normalized == "CN" else country["continent"],
        }
    return outputs


def build_admin1_outputs(
    admin1_map: dict[str, dict[str, str]],
    alternate_names: dict[str, str],
    converter,
) -> dict[str, dict[str, str]]:
    outputs: dict[str, dict[str, str]] = {}
    for full_code, admin1 in admin1_map.items():
        country_code = normalize_country_code(admin1["country"])
        key = f"{country_code}.{admin1['code']}"
        name_zh = alternate_names.get(admin1["geonameid"], "")
        if not name_zh:
            name_zh = converter.convert(admin1["nameEn"])
        outputs[key] = {
            "country": country_code,
            "code": admin1["code"],
            "nameZh": name_zh,
            "nameEn": admin1["nameEn"],
        }

    for country_code, (admin1_code, name_zh, name_en) in SPECIAL_ADMIN1.items():
        outputs[f"CN.{admin1_code}"] = {
            "country": "CN",
            "code": admin1_code,
            "nameZh": name_zh,
            "nameEn": name_en,
        }
    return outputs


def continent_bucket(country_code: str, countries: dict[str, dict[str, str]]) -> str:
    normalized_country = normalize_country_code(country_code)
    if normalized_country == "CN":
        return "china"
    source_country = countries.get(country_code) or countries.get("CN")
    continent = source_country["continent"] if source_country else ""
    return CONTINENT_GROUPS.get(continent, "others")


def serialize_city(
    city: CityRecord,
    countries_out: dict[str, dict[str, str]],
    admin1_out: dict[str, dict[str, str]],
    city_name_zh: str,
) -> dict[str, object]:
    normalized_country = normalize_country_code(city.country_code)

    if city.country_code in SPECIAL_ADMIN1:
        admin1_code, admin1_zh, admin1_en = SPECIAL_ADMIN1[city.country_code]
    else:
        admin1_key = f"{normalized_country}.{city.admin1_code}"
        admin1_entry = admin1_out.get(admin1_key, {"code": city.admin1_code, "nameZh": "", "nameEn": ""})
        admin1_code = admin1_entry["code"]
        admin1_zh = admin1_entry["nameZh"]
        admin1_en = admin1_entry["nameEn"]

    country = countries_out[normalized_country]
    return {
        "id": city.geonameid,
        "nameZh": city_name_zh,
        "nameEn": city.name,
        "country": normalized_country,
        "countryZh": country["nameZh"],
        "admin1": admin1_code,
        "admin1Zh": admin1_zh,
        "admin1En": admin1_en,
        "timezone": city.timezone,
        "lat": city.latitude,
        "lng": city.longitude,
        "population": city.population,
    }


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def generate_outputs(source_dir: Path, output_dir: Path, cache_dir: Path | None = None) -> dict[str, float]:
    cache_base = cache_dir or source_dir / ".cache"
    converter = get_converter()

    cities_path = ensure_dataset("cities5000.txt", cache_base) if not (source_dir / "cities5000.txt").exists() else source_dir / "cities5000.txt"
    admin1_path = ensure_dataset("admin1CodesASCII.txt", cache_base) if not (source_dir / "admin1CodesASCII.txt").exists() else source_dir / "admin1CodesASCII.txt"
    country_path = ensure_dataset("countryInfo.txt", cache_base) if not (source_dir / "countryInfo.txt").exists() else source_dir / "countryInfo.txt"
    alternate_path = ensure_dataset("alternateNamesV2.txt", cache_base) if not (source_dir / "alternateNamesV2.txt").exists() else source_dir / "alternateNamesV2.txt"

    cities = load_cities(cities_path)
    admin1_map = load_admin1(admin1_path)
    countries, country_geonames = load_countries(country_path)

    target_ids = {city.geonameid for city in cities}
    target_ids.update(country_geonames.keys())
    target_ids.update(admin1["geonameid"] for admin1 in admin1_map.values() if admin1["geonameid"])
    alternate_names = load_alternate_names(alternate_path, target_ids, converter)

    countries_out = build_country_outputs(countries, alternate_names)
    admin1_out = build_admin1_outputs(admin1_map, alternate_names, converter)

    bucketed_cities: dict[str, list[dict[str, object]]] = defaultdict(list)
    chinese_name_count = 0
    china_city_count = 0

    for city in cities:
        city_name_zh = choose_city_name(city, alternate_names, converter)
        serialized = serialize_city(city, countries_out, admin1_out, city_name_zh)
        bucket = continent_bucket(city.country_code, countries)
        bucketed_cities[bucket].append(serialized)
        if city_name_zh:
            chinese_name_count += 1
        if serialized["country"] == "CN":
            china_city_count += 1

    for records in bucketed_cities.values():
        records.sort(key=lambda item: (-int(item["population"]), item["nameEn"]))

    countries_payload = sorted(
        (
            {
                "code": item["code"],
                "nameZh": item["nameZh"],
                "nameEn": item["nameEn"],
            }
            for item in countries_out.values()
        ),
        key=lambda item: item["code"],
    )
    admin1_payload = sorted(admin1_out.values(), key=lambda item: (item["country"], item["code"]))

    write_json(output_dir / "cities-china.json", bucketed_cities.get("china", []))
    write_json(output_dir / "cities-asia.json", bucketed_cities.get("asia", []))
    write_json(output_dir / "cities-europe.json", bucketed_cities.get("europe", []))
    write_json(output_dir / "cities-americas.json", bucketed_cities.get("americas", []))
    write_json(output_dir / "cities-others.json", bucketed_cities.get("others", []))
    write_json(output_dir / "countries.json", countries_payload)
    write_json(output_dir / "admin1.json", admin1_payload)

    total_cities = len(cities)
    summary = {
        "total_countries": len(countries_payload),
        "total_cities": total_cities,
        "china_cities": china_city_count,
        "chinese_name_ratio": (chinese_name_count / total_cities) if total_cities else 0.0,
    }
    return summary


def build_parser() -> argparse.ArgumentParser:
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent
    parser = argparse.ArgumentParser(description="从 GeoNames 数据生成城市数据库")
    parser.add_argument("--source-dir", type=Path, default=root_dir / "downloads", help="原始数据目录")
    parser.add_argument("--output-dir", type=Path, default=root_dir / "data", help="输出目录")
    parser.add_argument("--cache-dir", type=Path, default=root_dir / ".cache" / "geonames", help="下载缓存目录")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = generate_outputs(args.source_dir, args.output_dir, args.cache_dir)
    print(f"总国家数: {summary['total_countries']}")
    print(f"总城市数: {summary['total_cities']}")
    print(f"中国城市数: {summary['china_cities']}")
    print(f"有中文名的比例: {summary['chinese_name_ratio']:.2%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
