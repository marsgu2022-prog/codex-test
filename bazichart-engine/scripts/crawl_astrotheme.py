#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from people_store import DEFAULT_DB, DEFAULT_REPORT_OUTPUT, DEFAULT_UNIFIED_OUTPUT, PeopleStoreSession, sync_source_snapshots

DATA_DIR = SCRIPT_DIR.parent / "data"
DEFAULT_OUTPUT = DATA_DIR / "famous_people_astrotheme.json"
DEFAULT_ERRORS = DATA_DIR / "crawl_errors_astrotheme.json"
DEFAULT_STATE = DATA_DIR / "astrotheme_crawl_state.json"
PARSE_ERROR_LOG = SCRIPT_DIR.parent.parent / "logs" / "parse_errors.log"

BASE_URL = "https://www.astrotheme.com"
SEARCH_URL = f"{BASE_URL}/celestar/horoscope_celebrity_search_by_filters.php"
USER_AGENT = "bazichart-engine/1.0 (astrotheme crawler)"
REQUEST_INTERVAL_SECONDS = 1.0
REQUEST_MAX_RETRIES = 3

CATEGORY_PAYLOADS = {
    "entertainment_stage": {"categorie[1]": "0|2|7"},
    "music": {"categorie[2]": "4"},
    "politics": {"categorie[3]": "5"},
    "sports": {"categorie[5]": "6"},
    "writers": {"categorie[6]": "8"},
    "science": {"categorie[9]": "11"},
    "media": {"categorie[4]": "1|3"},
    "visual_arts": {"categorie[7]": "9"},
    "spirituality": {"categorie[8]": "10"},
    "world_events": {"categorie[10]": "12"},
}
STATE_LAYOUT_VERSION = 2
LEGACY_COMPLETED_CATEGORY_INDEX = 5
FIRST_NEW_CATEGORY_INDEX = 6
LEGACY_CATEGORY_INDEX_MAP = {
    0: 0,
    1: 2,
    2: 3,
    3: 4,
    4: 5,
    5: FIRST_NEW_CATEGORY_INDEX,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="抓取 Astrotheme 有出生时辰的名人数据")
    parser.add_argument("--max-pages-per-category", type=int, default=3)
    parser.add_argument("--max-records", type=int, default=100)
    parser.add_argument("--request-interval", type=float, default=REQUEST_INTERVAL_SECONDS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--errors-output", type=Path, default=DEFAULT_ERRORS)
    parser.add_argument("--state-output", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--sqlite-db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--sqlite-export-unified", type=Path, default=DEFAULT_UNIFIED_OUTPUT)
    parser.add_argument("--sqlite-report-output", type=Path, default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})
    return session


def fetch(session: requests.Session, url: str, *, data: dict[str, str] | None = None, request_interval: float) -> str:
    last_error: Exception | None = None
    for attempt in range(1, REQUEST_MAX_RETRIES + 1):
        try:
            if data is None:
                response = session.get(url, timeout=30)
            else:
                response = session.post(url, data=data, timeout=30)
            response.raise_for_status()
            time.sleep(request_interval)
            return response.text
        except Exception as exc:
            last_error = exc
            if attempt < REQUEST_MAX_RETRIES:
                time.sleep(min(attempt * 2, 6))
    assert last_error is not None
    raise last_error


def build_search_payload(category_payload: dict[str, str]) -> dict[str, str]:
    payload = {
        "sexe": "M|F",
        "connue": "1",
        "fourchette": "1",
        "annee[0]": "1900",
        "annee[1]": "2026",
        "tri": "1",
    }
    payload.update(category_payload)
    return payload


def parse_result_page(html: str) -> tuple[list[str], str | None]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    for node in soup.select("a[href]"):
        href = node.get("href", "")
        if "/astrology/" not in href:
            continue
        full_url = urljoin(BASE_URL, href)
        if full_url not in urls:
            urls.append(full_url)

    next_url = None
    for node in soup.select("a[href]"):
        if node.get_text(" ", strip=True) == "Next":
            next_url = urljoin(BASE_URL, node.get("href", ""))
            break
    return urls, next_url


def normalize_name(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value)
    normalized = re.sub(r"\s+", "", normalized).casefold()
    return normalized or None


def normalize_birth_date(text: str) -> str | None:
    match = re.search(r"Born:\s+[A-Za-z]+,\s+([A-Za-z]+)\s+(\d{1,2})\s*,\s*(\d{4})", text)
    if not match:
        return None
    month_name, day, year = match.groups()
    months = {
        "January": "01", "February": "02", "March": "03", "April": "04",
        "May": "05", "June": "06", "July": "07", "August": "08",
        "September": "09", "October": "10", "November": "11", "December": "12",
    }
    month = months.get(month_name)
    if month is None:
        return None
    return f"{year}-{month}-{int(day):02d}"


def normalize_birth_time(text: str) -> str | None:
    match = re.search(r"Born:.*?(\d{1,2}:\d{2})\s*(AM|PM)", text, re.S)
    if not match:
        return None
    hour, minute = match.group(1).split(":")
    meridiem = match.group(2)
    hour_value = int(hour)
    if meridiem == "PM" and hour_value != 12:
        hour_value += 12
    if meridiem == "AM" and hour_value == 12:
        hour_value = 0
    return f"{hour_value:02d}:{minute}"


def parse_birth_place(text: str) -> tuple[str | None, str | None]:
    match = re.search(r"In:\s+(.+?)\s+\(([^()]+)\)\s+\(([^()]+)\)", text)
    if match:
        city, region, country = match.groups()
        return f"{city.strip()} ({region.strip()})", country.strip()
    match = re.search(r"In:\s+(.+?)\s+\(([^()]+)\)", text)
    if match:
        city, country = match.groups()
        return city.strip(), country.strip()
    return None, None


def infer_gender(text: str) -> str | None:
    lowered = text.lower()
    if " his detailed birth chart" in lowered or "he is" in lowered or "actor and producer" in lowered:
        return "male"
    if " her detailed birth chart" in lowered or "she is" in lowered:
        return "female"
    return None


def classify_occupation(category_key: str, page_text: str) -> list[str]:
    mapping = {
        "entertainment": ["演员"],
        "entertainment_stage": ["演员"],
        "music": ["音乐家"],
        "politics": ["政治家"],
        "sports": ["运动员"],
        "writers": ["作家"],
        "media": ["媒体人"],
        "visual_arts": ["艺术家"],
        "spirituality": ["占星/神秘学"],
        "science": ["科学家"],
        "world_events": ["社会事件人物"],
    }
    occupations = list(mapping.get(category_key, []))
    lowered = page_text.lower()
    if "producer" in lowered or "business" in lowered or "company" in lowered:
        occupations.append("企业家")
    if "singer" in lowered or "musician" in lowered:
        occupations.append("音乐家")
    return list(dict.fromkeys(occupations))


def parse_source_reliability(text: str) -> tuple[str, str, float]:
    match = re.search(r"Source\s*:\s*(.+?)\s+Contributor\s*:\s*(.+)", text)
    source_text = match.group(1).strip() if match else "astrotheme"
    lowered = source_text.lower()
    if "certificat" in lowered or "registry" in lowered or "birth certificate" in lowered:
        return f"astrotheme:{source_text}", "high", 0.85
    if "memory" in lowered or "autobiography" in lowered or "colleague" in lowered:
        return f"astrotheme:{source_text}", "medium", 0.7
    return f"astrotheme:{source_text}", "medium", 0.65


def extract_bio(text: str) -> str:
    match = re.search(r"Biography of .*?\(excerpt\)\s+(.*?)(?:\s+The\semphasis\sis|\s+In\syour\snatal\schart|\s+Back to Astrotheme)", text, re.S)
    if not match:
        match = re.search(r"Biography of .*?\(excerpt\)\s+(.*)", text, re.S)
    if not match:
        return ""
    bio = re.sub(r"\s+", " ", match.group(1)).strip()
    sentence = re.split(r"(?<=[.!?])\s+", bio)[0].strip()
    return sentence[:120]


def infer_notable_events(text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    match = re.search(r"Biography of .*?\(excerpt\)\s+(.*?)(?:\s+The\semphasis\sis|\s+In\syour\snatal\schart|\s+Back to Astrotheme)", text, re.S)
    if not match:
        match = re.search(r"Biography of .*?\(excerpt\)\s+(.*)", text, re.S)
    if not match:
        return events
    bio = re.sub(r"\s+", " ", match.group(1)).strip()
    for year_match in re.finditer(r"\b((19|20)\d{2})\b", bio):
        year = int(year_match.group(1))
        sentence_match = re.search(rf"([^.!?]*\b{year}\b[^.!?]*[.!?])", bio)
        sentence = sentence_match.group(1).strip() if sentence_match else None
        if not sentence:
            continue
        lowered = sentence.lower()
        if any(token in lowered for token in ("award", "won", "prize", "emmy", "oscar", "golden globe")):
            event_type = "award"
        elif any(token in lowered for token in ("married", "marriage")):
            event_type = "marriage"
        elif any(token in lowered for token in ("died", "death")):
            event_type = "death"
        elif any(token in lowered for token in ("debut", "gained recognition", "first")):
            event_type = "career_start"
        else:
            event_type = "other"
        events.append({"year": year, "event": sentence[:120], "event_type": event_type})
        if len(events) >= 3:
            break
    return events


def log_parse_error(category_key: str, url: str, reason: str, *, detail: str | None = None) -> None:
    PARSE_ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": "astrotheme",
        "category": category_key,
        "url": url,
        "reason": reason,
    }
    if detail:
        payload["detail"] = detail[:300]
    with PARSE_ERROR_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def parse_person_with_reason(html: str, url: str, category_key: str) -> tuple[dict[str, Any] | None, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    if "Astrological chart of" not in title:
        return None, "missing_astrological_title"
    page_text = soup.get_text("\n", strip=True)
    birth_date = normalize_birth_date(page_text)
    birth_time = normalize_birth_time(page_text)
    if birth_date is None:
        return None, "missing_birth_date"
    if birth_time is None:
        return None, "missing_birth_time"
    birth_city, birth_country = parse_birth_place(page_text)
    source_text, reliability, score = parse_source_reliability(page_text)
    name_match = re.search(r"Astrological chart of (.*?), born", title)
    name_en = name_match.group(1).strip() if name_match else None
    if not name_en:
        return None, "missing_name"
    return {
        "name_en": name_en,
        "name_zh": None,
        "birth_date": birth_date,
        "birth_time": birth_time,
        "birth_time_source": source_text,
        "birth_time_reliability": reliability,
        "birth_city": birth_city,
        "birth_country": birth_country,
        "gender": infer_gender(page_text),
        "occupation": classify_occupation(category_key, page_text),
        "bio": extract_bio(page_text),
        "notable_events": infer_notable_events(page_text),
        "source_urls": [url],
        "data_quality_score": score,
    }, None


def parse_person(html: str, url: str, category_key: str) -> dict[str, Any] | None:
    person, _ = parse_person_with_reason(html, url, category_key)
    return person


def merge_people(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str | None, str | None], dict[str, Any]] = {}
    for item in existing + incoming:
        key = person_identity(item)
        current = merged.get(key)
        if current is None or item.get("data_quality_score", 0) >= current.get("data_quality_score", 0):
            merged[key] = item
    return list(merged.values())


def person_identity(item: dict[str, Any]) -> tuple[str | None, str | None]:
    raw_name = item.get("name_en") or item.get("name_zh") or item.get("name")
    return normalize_name(raw_name), item.get("birth_date")


def build_identity_set(people: list[dict[str, Any]]) -> set[tuple[str | None, str | None]]:
    return {person_identity(item) for item in people}


def normalize_identity_keys(keys: set[tuple[str | None, str | None]] | None) -> set[tuple[str | None, str | None]]:
    if not keys:
        return set()
    return {(normalize_name(name), birth_date) for name, birth_date in keys}


def load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, list) else []


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"category_index": 0, "next_url": None, "layout_version": STATE_LAYOUT_VERSION}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        return {"category_index": 0, "next_url": None, "layout_version": STATE_LAYOUT_VERSION}
    state = {
        "category_index": int(payload.get("category_index", 0) or 0),
        "next_url": payload.get("next_url"),
        "updated_at": payload.get("updated_at"),
        "layout_version": int(payload.get("layout_version", 1) or 1),
    }
    if state["layout_version"] < STATE_LAYOUT_VERSION:
        state["category_index"] = LEGACY_CATEGORY_INDEX_MAP.get(
            state["category_index"],
            FIRST_NEW_CATEGORY_INDEX if state["category_index"] >= LEGACY_COMPLETED_CATEGORY_INDEX else 0,
        )
        state["layout_version"] = STATE_LAYOUT_VERSION
    return state


def write_state(path: Path, state: dict[str, Any]) -> None:
    write_json(path, state)


def crawl(
    session: requests.Session,
    max_pages_per_category: int,
    max_records: int,
    request_interval: float,
    state: dict[str, Any] | None = None,
    existing_keys: set[tuple[str | None, str | None]] | None = None,
    batch_callback: Any | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    people: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_people_keys = normalize_identity_keys(existing_keys)
    categories = list(CATEGORY_PAYLOADS.items())
    runtime_state = state or {"category_index": 0, "next_url": None, "layout_version": STATE_LAYOUT_VERSION}
    start_index = max(0, min(int(runtime_state.get("category_index", 0) or 0), len(categories)))

    for category_index in range(start_index, len(categories)):
        if len(people) >= max_records:
            break
        category_key, category_payload = categories[category_index]
        current_html = None
        next_url = runtime_state.get("next_url") if category_index == start_index else None
        try:
            if next_url:
                current_html = fetch(session, next_url, request_interval=request_interval)
            else:
                current_html = fetch(session, SEARCH_URL, data=build_search_payload(category_payload), request_interval=request_interval)
        except Exception as exc:
            errors.append({"source": "astrotheme", "stage": "search", "category": category_key, "url": SEARCH_URL, "error": str(exc)})
            continue

        page_no = 0
        while current_html and page_no < max_pages_per_category and len(people) < max_records:
            page_no += 1
            page_people: list[dict[str, Any]] = []
            links, next_url = parse_result_page(current_html)
            for detail_url in links:
                if len(people) >= max_records:
                    break
                if detail_url in seen_urls:
                    continue
                seen_urls.add(detail_url)
                try:
                    detail_html = fetch(session, detail_url, request_interval=request_interval)
                    person, parse_reason = parse_person_with_reason(detail_html, detail_url, category_key)
                    if person is None:
                        if parse_reason:
                            log_parse_error(category_key, detail_url, parse_reason)
                        continue
                    identity = person_identity(person)
                    if identity in seen_people_keys:
                        continue
                    seen_people_keys.add(identity)
                    people.append(person)
                    page_people.append(person)
                except Exception as exc:
                    errors.append({"source": "astrotheme", "stage": "detail", "category": category_key, "url": detail_url, "error": str(exc)})

            runtime_state = {
                "category_index": category_index,
                "next_url": next_url,
                "layout_version": STATE_LAYOUT_VERSION,
            }
            if batch_callback:
                batch_callback(page_people, runtime_state)
            if not next_url or page_no >= max_pages_per_category:
                break
            try:
                current_html = fetch(session, next_url, request_interval=request_interval)
            except Exception as exc:
                errors.append({"source": "astrotheme", "stage": "page", "category": category_key, "url": next_url, "error": str(exc)})
                break

        if not next_url:
            runtime_state = {
                "category_index": category_index + 1,
                "next_url": None,
                "layout_version": STATE_LAYOUT_VERSION,
            }

    runtime_state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    return people, errors, runtime_state


def main() -> None:
    args = parse_args()
    session = make_session()
    existing = load_json_list(args.output)
    existing_errors = load_json_list(args.errors_output)
    state = load_state(args.state_output)
    store: PeopleStoreSession | None = None
    try:
        store = PeopleStoreSession(
            args.sqlite_db,
            unified_output=args.sqlite_export_unified,
            report_output=args.sqlite_report_output,
            refresh_interval_seconds=20.0,
        )

        def batch_callback(page_people: list[dict[str, Any]], _runtime_state: dict[str, Any]) -> None:
            store.upsert("astrotheme", page_people, refresh_outputs=False)
            if page_people:
                store.refresh_outputs()

        people, errors, runtime_state = crawl(
            session,
            args.max_pages_per_category,
            args.max_records,
            args.request_interval,
            state=state,
            existing_keys=build_identity_set(existing),
            batch_callback=batch_callback,
        )
        merged = merge_people(existing, people)
        write_json(args.output, merged)
        write_json(args.errors_output, existing_errors + errors)
        write_state(args.state_output, runtime_state)
        sync_source_snapshots(
            args.sqlite_db,
            {"astrotheme": merged},
            unified_output=args.sqlite_export_unified,
            report_output=args.sqlite_report_output,
        )
    finally:
        if store is not None:
            store.refresh_outputs(force=True)
            store.close()
    print(f"astrotheme_total={len(merged)}")
    print(f"astrotheme_added={len(people)}")
    print(f"errors_added={len(errors)}")
    print(f"next_category_index={runtime_state.get('category_index')}")
    print(f"next_url={runtime_state.get('next_url')}")


if __name__ == "__main__":
    main()
