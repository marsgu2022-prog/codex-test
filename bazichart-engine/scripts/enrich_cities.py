#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from timezonefinder import TimezoneFinder
except ImportError:  # pragma: no cover
    TimezoneFinder = None


GEONAMES_BASE = "https://download.geonames.org/export/dump"
DATASET_URLS = {
    "cities1000.txt": f"{GEONAMES_BASE}/cities1000.zip",
    "cities500.txt": f"{GEONAMES_BASE}/cities500.zip",
}
DEFAULT_SOURCE_DIR_NAMES = ("cities_data", "data")


def safe_split(line: str, expected_parts: int) -> list[str]:
    parts = line.rstrip("\n").split("\t")
    if len(parts) < expected_parts:
        parts.extend([""] * (expected_parts - len(parts)))
    return parts


def ensure_dataset(filename: str, cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / filename
    if target.exists():
        return target

    url = DATASET_URLS[filename]
    archive_path = cache_dir / Path(url).name
    print(f"下载 GeoNames 数据：{url}")
    urllib.request.urlretrieve(url, archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extract(filename, cache_dir)
    return target


def round_coord(value: Any) -> float | None:
    if value in ("", None):
        return None
    return round(float(value), 4)


def normalize_text(value: str) -> str:
    return "".join(char.lower() for char in value.strip() if char.isalnum() or "\u4e00" <= char <= "\u9fff")


def choose_input_dir(root_dir: Path, preferred: Path | None = None) -> Path:
    if preferred is not None:
        return preferred
    for name in DEFAULT_SOURCE_DIR_NAMES:
        candidate = root_dir / name
        if candidate.exists():
            return candidate
    return root_dir / "cities_data"


def iter_source_files(source_dir: Path) -> list[Path]:
    candidates = []
    for path in sorted(source_dir.glob("*.json")):
        if path.name in {"countries.json", "admin1.json", "enrichment_report.json", "validation_report.json"}:
            continue
        if path.name.startswith("cities-"):
            candidates.append(path)
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict) and "cities" in payload:
            candidates.append(path)
    return candidates


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_country_payload(payload: list[dict[str, Any]] | dict[str, Any], source_name: str) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and "cities" in payload:
        return [
            {
                "country_code": payload.get("country_code", ""),
                "country_name": payload.get("country_name", ""),
                "cities": list(payload.get("cities", [])),
                "_source_name": source_name,
            }
        ]

    if isinstance(payload, list):
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for item in payload:
            if not isinstance(item, dict):
                continue
            country_code = item.get("country") or ""
            country_name = item.get("countryZh") or ""
            grouped[(country_code, country_name)].append(
                {
                    "name": item.get("nameZh") or item.get("name") or "",
                    "name_en": item.get("nameEn") or item.get("name_en") or "",
                    "province": item.get("admin1Zh") or item.get("province") or "",
                    "province_en": item.get("admin1En") or item.get("province_en") or "",
                    "latitude": item.get("lat") if "lat" in item else item.get("latitude"),
                    "longitude": item.get("lng") if "lng" in item else item.get("longitude"),
                    "timezone": item.get("timezone") or "",
                }
            )
        return [
            {
                "country_code": country_code,
                "country_name": country_name,
                "cities": cities,
                "_source_name": source_name,
            }
            for (country_code, country_name), cities in grouped.items()
            if cities
        ]

    raise ValueError(f"不支持的 JSON 结构: {source_name}")


def load_source_countries(source_dir: Path) -> list[dict[str, Any]]:
    countries = []
    for path in iter_source_files(source_dir):
        payload = load_json(path)
        normalized_items = normalize_country_payload(payload, path.name)
        for normalized in normalized_items:
            if normalized["cities"]:
                countries.append(normalized)
    return countries


def build_geonames_index(cities_path: Path) -> dict[tuple[str, str], list[dict[str, Any]]]:
    index: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    with cities_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue
            parts = safe_split(raw_line, 19)
            record = {
                "name": parts[1],
                "asciiname": parts[2],
                "alternatenames": parts[3].split(",") if parts[3] else [],
                "latitude": round(float(parts[4]), 4),
                "longitude": round(float(parts[5]), 4),
                "country_code": parts[8],
                "admin1_code": parts[10],
                "population": int(parts[14] or 0),
                "timezone": parts[17],
            }
            keys = {
                normalize_text(parts[1]),
                normalize_text(parts[2]),
                *(normalize_text(item) for item in record["alternatenames"] if item),
            }
            for key in keys:
                if key:
                    index[(record["country_code"], key)].append(record)
    return index


def score_candidate(city: dict[str, Any], candidate: dict[str, Any]) -> tuple[int, int, int]:
    province = normalize_text(city.get("province_en") or city.get("province") or "")
    penalty = 1
    if province:
        admin1_match = province in normalize_text(candidate.get("admin1_code", "")) or province in normalize_text(city.get("province_en", ""))
        penalty = 0 if admin1_match else 1
    return (penalty, -candidate["population"], len(candidate["name"]))


def find_best_match(city: dict[str, Any], country_code: str, geonames_index: dict[tuple[str, str], list[dict[str, Any]]]) -> dict[str, Any] | None:
    keys = [
        normalize_text(city.get("name", "")),
        normalize_text(city.get("name_en", "")),
    ]
    candidates = []
    for key in keys:
        if not key:
            continue
        candidates.extend(geonames_index.get((country_code, key), []))
    if not candidates:
        return None
    unique_candidates = {(item["name"], item["latitude"], item["longitude"], item["timezone"]): item for item in candidates}
    return min(unique_candidates.values(), key=lambda item: score_candidate(city, item))


def get_timezonefinder():
    if TimezoneFinder is None:
        return None
    return TimezoneFinder()


def infer_timezone(latitude: float | None, longitude: float | None, finder) -> str:
    if latitude is None or longitude is None or finder is None:
        return ""
    return finder.timezone_at(lat=latitude, lng=longitude) or finder.closest_timezone_at(lat=latitude, lng=longitude) or ""


def enrich_city(city: dict[str, Any], country_code: str, geonames_index: dict[tuple[str, str], list[dict[str, Any]]], finder) -> dict[str, Any]:
    result = {
        "name": city.get("name", ""),
        "name_en": city.get("name_en") or city.get("nameEn") or "",
        "province": city.get("province") or city.get("admin1Zh") or "",
        "latitude": round_coord(city.get("latitude")),
        "longitude": round_coord(city.get("longitude")),
        "timezone": city.get("timezone") or "",
    }
    if not result["name_en"]:
        result["name_en"] = city.get("name", "")

    matched = find_best_match(city, country_code, geonames_index)
    if matched is not None:
        result["latitude"] = matched["latitude"]
        result["longitude"] = matched["longitude"]
        result["timezone"] = matched["timezone"] or result["timezone"]

    if not result["timezone"]:
        result["timezone"] = infer_timezone(result["latitude"], result["longitude"], finder)
    return result


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def enrich_countries(source_dir: Path, output_dir: Path, cache_dir: Path, geonames_file: Path | None = None) -> dict[str, Any]:
    countries = load_source_countries(source_dir)
    finder = get_timezonefinder()
    geonames_path = geonames_file
    if geonames_path is None:
        try:
            geonames_path = ensure_dataset("cities1000.txt", cache_dir)
        except Exception:
            geonames_path = ensure_dataset("cities500.txt", cache_dir)
    geonames_index = build_geonames_index(geonames_path)

    total_cities = 0
    completed_cities = 0
    per_country_reports = []

    for country in countries:
        country_code = country["country_code"]
        enriched_cities = []
        for city in country["cities"]:
            total_cities += 1
            enriched = enrich_city(city, country_code, geonames_index, finder)
            if enriched["latitude"] is not None and enriched["longitude"] is not None and enriched["timezone"]:
                completed_cities += 1
            enriched_cities.append(enriched)

        enriched_payload = {
            "country_code": country_code,
            "country_name": country["country_name"],
            "cities": enriched_cities,
        }
        output_name = f"{country_code.lower() or Path(country['_source_name']).stem}.json"
        write_json(output_dir / output_name, enriched_payload)
        per_country_reports.append(
            {
                "country_code": country_code,
                "country_name": country["country_name"],
                "city_count": len(enriched_cities),
                "completed_count": sum(
                    1
                    for item in enriched_cities
                    if item["latitude"] is not None and item["longitude"] is not None and item["timezone"]
                ),
                "output_file": output_name,
            }
        )

    summary = {
        "source_dir": str(source_dir),
        "output_dir": str(output_dir),
        "countries": len(per_country_reports),
        "total_cities": total_cities,
        "completed_cities": completed_cities,
        "coverage_ratio": (completed_cities / total_cities) if total_cities else 0.0,
        "reports": per_country_reports,
    }
    write_json(output_dir / "enrichment_report.json", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    root_dir = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="为城市数据补全经纬度和时区")
    parser.add_argument("--source-dir", type=Path, default=None, help="输入目录，默认优先 cities_data/，其次 data/")
    parser.add_argument("--output-dir", type=Path, default=root_dir / "enriched_cities", help="输出目录")
    parser.add_argument("--cache-dir", type=Path, default=root_dir / ".cache" / "geonames", help="GeoNames 缓存目录")
    parser.add_argument("--geonames-file", type=Path, default=None, help="本地 GeoNames 文件路径")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root_dir = Path(__file__).resolve().parent.parent
    source_dir = choose_input_dir(root_dir, args.source_dir)
    if not source_dir.exists():
        print(f"输入目录不存在：{source_dir}", file=sys.stderr)
        return 1

    summary = enrich_countries(source_dir, args.output_dir, args.cache_dir, args.geonames_file)
    print(f"国家文件数: {summary['countries']}")
    print(f"城市总数: {summary['total_cities']}")
    print(f"补全成功: {summary['completed_cities']}")
    print(f"覆盖率: {summary['coverage_ratio']:.2%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
