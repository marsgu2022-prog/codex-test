#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "data"
DEFAULT_OUTPUT = DATA_DIR / "famous_people_astrotheme.json"
DEFAULT_ERRORS = DATA_DIR / "crawl_errors_astrotheme.json"

BASE_URL = "https://www.astrotheme.com"
SEARCH_URL = f"{BASE_URL}/celestar/horoscope_celebrity_search_by_filters.php"
USER_AGENT = "bazichart-engine/1.0 (astrotheme crawler)"
REQUEST_INTERVAL_SECONDS = 1.0
REQUEST_MAX_RETRIES = 3

CATEGORY_PAYLOADS = {
    "entertainment": {"categorie[1]": "0|2|7", "categorie[2]": "4"},
    "politics": {"categorie[3]": "5"},
    "sports": {"categorie[5]": "6"},
    "writers": {"categorie[6]": "8"},
    "science": {"categorie[9]": "11"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="抓取 Astrotheme 有出生时辰的名人数据")
    parser.add_argument("--max-pages-per-category", type=int, default=3)
    parser.add_argument("--max-records", type=int, default=100)
    parser.add_argument("--request-interval", type=float, default=REQUEST_INTERVAL_SECONDS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--errors-output", type=Path, default=DEFAULT_ERRORS)
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
        "politics": ["政治家"],
        "sports": ["运动员"],
        "writers": ["作家"],
        "science": ["科学家"],
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


def parse_person(html: str, url: str, category_key: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    if "Astrological chart of" not in title:
        return None
    page_text = soup.get_text("\n", strip=True)
    birth_date = normalize_birth_date(page_text)
    birth_time = normalize_birth_time(page_text)
    if birth_date is None or birth_time is None:
        return None
    birth_city, birth_country = parse_birth_place(page_text)
    source_text, reliability, score = parse_source_reliability(page_text)
    name_match = re.search(r"Astrological chart of (.*?), born", title)
    name_en = name_match.group(1).strip() if name_match else None
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
    }


def merge_people(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str | None, str | None], dict[str, Any]] = {}
    for item in existing + incoming:
        key = (item.get("name_en"), item.get("birth_date"))
        current = merged.get(key)
        if current is None or item.get("data_quality_score", 0) >= current.get("data_quality_score", 0):
            merged[key] = item
    return list(merged.values())


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


def crawl(session: requests.Session, max_pages_per_category: int, max_records: int, request_interval: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    people: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for category_key, category_payload in CATEGORY_PAYLOADS.items():
        if len(people) >= max_records:
            break
        current_html = None
        next_url = None
        try:
            current_html = fetch(session, SEARCH_URL, data=build_search_payload(category_payload), request_interval=request_interval)
        except Exception as exc:
            errors.append({"source": "astrotheme", "stage": "search", "category": category_key, "url": SEARCH_URL, "error": str(exc)})
            continue

        page_no = 0
        while current_html and page_no < max_pages_per_category and len(people) < max_records:
            page_no += 1
            links, next_url = parse_result_page(current_html)
            for detail_url in links:
                if len(people) >= max_records:
                    break
                if detail_url in seen_urls:
                    continue
                seen_urls.add(detail_url)
                try:
                    detail_html = fetch(session, detail_url, request_interval=request_interval)
                    person = parse_person(detail_html, detail_url, category_key)
                    if person is None:
                        continue
                    people.append(person)
                except Exception as exc:
                    errors.append({"source": "astrotheme", "stage": "detail", "category": category_key, "url": detail_url, "error": str(exc)})

            if not next_url or page_no >= max_pages_per_category:
                break
            try:
                current_html = fetch(session, next_url, request_interval=request_interval)
            except Exception as exc:
                errors.append({"source": "astrotheme", "stage": "page", "category": category_key, "url": next_url, "error": str(exc)})
                break

    return people, errors


def main() -> None:
    args = parse_args()
    session = make_session()
    existing = load_json_list(args.output)
    existing_errors = load_json_list(args.errors_output)
    people, errors = crawl(session, args.max_pages_per_category, args.max_records, args.request_interval)
    merged = merge_people(existing, people)
    write_json(args.output, merged)
    write_json(args.errors_output, existing_errors + errors)
    print(f"astrotheme_total={len(merged)}")
    print(f"astrotheme_added={len(people)}")
    print(f"errors_added={len(errors)}")


if __name__ == "__main__":
    main()
