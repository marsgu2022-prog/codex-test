#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "data"
COUNTRIES_PATH = DATA_DIR / "countries.json"
DEFAULT_OUTPUT_A = DATA_DIR / "famous_people_astro.json"
DEFAULT_OUTPUT_B = DATA_DIR / "famous_people_astro_b.json"
DEFAULT_ERRORS = DATA_DIR / "crawl_errors.json"

BASE_URL = "https://www.astro.com"
ALL_PAGES_URL = f"{BASE_URL}/wiki/astro-databank/index.php?title=Special:AllPages&from=A"
USER_AGENT = "bazichart-engine/1.0 (astro databank crawler)"
REQUEST_INTERVAL_SECONDS = 1.05

ALLOWED_RATINGS = {"AA", "A", "B"}
HIGH_CONFIDENCE_RATINGS = {"AA", "A"}
TARGET_OCCUPATION_KEYS = {"企业家", "政治家", "演员", "运动员", "科学家", "作家"}
EXCLUDED_CATEGORY_KEYWORDS = [
    "Accident",
    "earthquake",
    "fire",
    "explosion",
    "attack",
    "derailment",
    "crash",
    "murder",
    "earthquakes",
    "wildfire",
]
OCCUPATION_KEYWORDS = {
    "企业家": ["Vocation : Business", "Vocation : Finance", "Vocation : Industry", "Vocation : Management", "executive", "entrepreneur", "business"],
    "政治家": ["Vocation : Politics", "statesman", "politic"],
    "演员": ["Vocation : Entertainment", "actor", "actress", "comedian", "film", "television", "director"],
    "运动员": ["Vocation : Sports", "athlete", "soccer", "football", "baseball", "basketball", "olympic", "tennis"],
    "科学家": ["Vocation : Science", "scientist", "physicist", "chemist", "psychologist", "mathematician", "astronomer", "inventor"],
    "作家": ["Vocation : Writers", "writer", "author", "poet", "novelist", "journalist"],
}
TECH_KEYWORDS = ["technology", "computer", "software", "internet", "apple", "microsoft", "tesla"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="抓取 Astro-Databank 高质量有时辰名人数据")
    parser.add_argument("--start-url", default=ALL_PAGES_URL)
    parser.add_argument("--max-pages", type=int, default=3)
    parser.add_argument("--max-records", type=int, default=30)
    parser.add_argument("--output-a", type=Path, default=DEFAULT_OUTPUT_A)
    parser.add_argument("--output-b", type=Path, default=DEFAULT_OUTPUT_B)
    parser.add_argument("--errors-output", type=Path, default=DEFAULT_ERRORS)
    return parser.parse_args()


def load_country_map(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return {item["code"]: item["nameEn"] for item in payload}


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})
    return session


def fetch_text(session: requests.Session, url: str) -> str:
    response = session.get(url, timeout=30)
    response.raise_for_status()
    time.sleep(REQUEST_INTERVAL_SECONDS)
    return response.text


def normalize_title_from_href(href: str) -> str:
    parsed = urlparse(href)
    path = unquote(parsed.path)
    if "/astro-databank/" in path:
        return path.split("/astro-databank/", 1)[1].replace("/", "").replace(" ", "_")
    query = parse_qs(parsed.query)
    title = query.get("title", [""])[0]
    return title.replace(" ", "_")


def build_raw_url(title: str) -> str:
    return f"{BASE_URL}/wiki/astro-databank/index.php?title={quote(title, safe=':_,-()')}&action=raw"


def build_html_url(title: str) -> str:
    return f"{BASE_URL}/wiki/astro-databank/index.php?title={quote(title, safe=':_,-()')}"


def parse_allpages(html: str) -> tuple[list[dict[str, str]], str | None]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for node in soup.select(".mw-allpages-body a[href]"):
        text = node.get_text(" ", strip=True)
        href = node.get("href", "")
        if not text or not href:
            continue
        links.append({"title": text, "href": urljoin(BASE_URL, href)})

    next_href = None
    for node in soup.select(".mw-allpages-nav a[href]"):
        if node.get_text(" ", strip=True).startswith("Next page"):
            next_href = urljoin(BASE_URL, node.get("href", ""))
            break
    return links, next_href


def parse_raw_fields(raw_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in raw_text.splitlines():
        if not line.startswith("|") or "=" not in line:
            continue
        key, value = line[1:].split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


def extract_scat_categories(raw_text: str) -> list[str]:
    return [match.strip() for match in re.findall(r"^\|scat=(.*)$", raw_text, re.M) if match.strip()]


def normalize_birth_date(value: str) -> str | None:
    match = re.fullmatch(r"(\d{4})/(\d{2})/(\d{2})", value.strip())
    if not match:
        return None
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"


def normalize_birth_time(value: str) -> str | None:
    match = re.search(r"(\d{2}):(\d{2})", value or "")
    if not match:
        return None
    return f"{match.group(1)}:{match.group(2)}"


def normalize_gender(value: str) -> str | None:
    mapping = {"M": "male", "F": "female", "m": "male", "f": "female"}
    return mapping.get((value or "").strip())


def infer_country(fields: dict[str, str], country_map: dict[str, str]) -> str | None:
    region = fields.get("BirthCountry", "").strip()
    sctr = fields.get("sctr", "").strip()
    code_match = re.search(r"\(([A-Z]{2})\)", sctr)
    if code_match:
        country_name = country_map.get(code_match.group(1))
        if country_name:
            return country_name
    if len(region) > 2:
        return region
    return country_map.get(region)


def classify_occupations(categories: list[str], bio: str) -> list[str]:
    haystack = " | ".join(categories + [bio]).lower()
    results: list[str] = []
    for occupation, keywords in OCCUPATION_KEYWORDS.items():
        if any(keyword.lower() in haystack for keyword in keywords):
            results.append(occupation)
    if "企业家" in results and any(token in haystack for token in TECH_KEYWORDS):
        insert_at = results.index("企业家") + 1
        results.insert(insert_at, "科技")
    return list(dict.fromkeys(results))


def is_target_page(link: dict[str, str]) -> bool:
    text = link["title"]
    if any(keyword.lower() in text.lower() for keyword in EXCLUDED_CATEGORY_KEYWORDS):
        return False
    if text.startswith("Category:") or text.startswith("Special:"):
        return False
    return True


def extract_biography(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one(".mw-parser-output")
    if content is None:
        return ""

    biography_node: Tag | None = None
    for heading in content.select("h2, h3"):
        title = heading.get_text(" ", strip=True).lower()
        if "biography" in title:
            biography_node = heading
            break
    if biography_node is None:
        paragraph = content.find("p")
        return paragraph.get_text(" ", strip=True)[:400] if paragraph else ""

    parts: list[str] = []
    for sibling in biography_node.find_next_siblings():
        if sibling.name in {"h2", "h3"}:
            break
        text = sibling.get_text(" ", strip=True)
        if text:
            parts.append(text)
        if len(" ".join(parts)) >= 600:
            break
    return " ".join(parts)[:600]


def short_bio(text: str) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= 80:
        return clean
    sentence = re.split(r"(?<=[.!?])\s+", clean)[0].strip()
    return sentence[:80]


def rating_metadata(rating: str) -> tuple[str, str, float]:
    if rating == "AA":
        return "astrodatabank_AA", "high", 0.95
    if rating == "A":
        return "astrodatabank_A", "high", 0.88
    if rating == "B":
        return "astrodatabank_B", "medium", 0.72
    return "unknown", "unknown", 0.0


def parse_person(raw_text: str, html_text: str, source_url: str, country_map: dict[str, str]) -> dict[str, Any] | None:
    fields = parse_raw_fields(raw_text)
    categories = extract_scat_categories(raw_text)
    rating = fields.get("sroddenrating", "").strip()
    if rating not in ALLOWED_RATINGS:
        return None

    birth_date = normalize_birth_date(fields.get("sbdate", ""))
    birth_time = normalize_birth_time(fields.get("sbtime", ""))
    if birth_date is None or birth_time is None:
        return None

    biography = extract_biography(html_text)
    occupations = classify_occupations(categories, biography)
    if not any(item in TARGET_OCCUPATION_KEYS for item in occupations):
        return None

    birth_city = fields.get("Place", "").strip() or None
    birth_country = infer_country(fields, country_map)
    gender = normalize_gender(fields.get("Gender", ""))
    birth_time_source, reliability, score = rating_metadata(rating)
    return {
        "name_en": fields.get("sflname") or fields.get("Name") or None,
        "name_zh": None,
        "birth_date": birth_date,
        "birth_time": birth_time,
        "birth_time_source": birth_time_source,
        "birth_time_reliability": reliability,
        "birth_city": birth_city,
        "birth_country": birth_country,
        "gender": gender,
        "occupation": occupations,
        "bio": short_bio(biography),
        "notable_events": [],
        "source_urls": [source_url],
        "data_quality_score": score,
        "rodden_rating": rating,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def crawl(session: requests.Session, start_url: str, max_pages: int, max_records: int, country_map: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    current_url = start_url
    page_count = 0
    high_confidence: list[dict[str, Any]] = []
    medium_confidence: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen_titles: set[str] = set()

    while current_url and page_count < max_pages and len(high_confidence) < max_records:
        try:
            index_html = fetch_text(session, current_url)
            links, next_url = parse_allpages(index_html)
        except Exception as exc:
            errors.append({"url": current_url, "stage": "index", "error": str(exc)})
            break

        page_count += 1
        for link in links:
            if len(high_confidence) >= max_records:
                break
            if not is_target_page(link):
                continue

            title = normalize_title_from_href(link["href"])
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)

            raw_url = build_raw_url(title)
            html_url = build_html_url(title)
            try:
                raw_text = fetch_text(session, raw_url)
                html_text = fetch_text(session, html_url)
                person = parse_person(raw_text, html_text, html_url, country_map)
                if person is None:
                    continue
                if person["rodden_rating"] in HIGH_CONFIDENCE_RATINGS:
                    high_confidence.append(person)
                else:
                    medium_confidence.append(person)
            except Exception as exc:
                errors.append({"url": html_url, "stage": "detail", "error": str(exc)})

        current_url = next_url

    return high_confidence, medium_confidence, errors


def main() -> None:
    args = parse_args()
    country_map = load_country_map(COUNTRIES_PATH)
    session = make_session()
    high_confidence, medium_confidence, errors = crawl(
        session=session,
        start_url=args.start_url,
        max_pages=args.max_pages,
        max_records=args.max_records,
        country_map=country_map,
    )
    write_json(args.output_a, high_confidence)
    write_json(args.output_b, medium_confidence)
    write_json(args.errors_output, errors)
    print(f"astro_AA_A={len(high_confidence)}")
    print(f"astro_B={len(medium_confidence)}")
    print(f"errors={len(errors)}")


if __name__ == "__main__":
    main()
