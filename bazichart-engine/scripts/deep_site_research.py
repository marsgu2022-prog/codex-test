#!/usr/bin/env python3
from __future__ import annotations

import json
import random
import re
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
TIMEOUT = 20
DELAY_RANGE = (1.0, 1.8)
MAX_INTERNAL_LINKS = 30
MAX_RESOURCES = 50

TARGETS = [
    {
        "name": "Master Sean Chan",
        "pages": [
            "https://www.masterseanchan.com/",
            "https://www.masterseanchan.com/bazi-calculator/",
        ],
    },
    {
        "name": "MingLi",
        "pages": [
            "https://www.mingli.info/",
            "https://www.mingli.info/bazi",
        ],
    },
    {
        "name": "Joey Yap",
        "pages": [
            "https://home.joeyyap.com/",
        ],
    },
    {
        "name": "Marlyna Consulting",
        "pages": [
            "https://marlynaconsulting.com/",
            "https://marlynaconsulting.com/ba-zi-calculator/",
        ],
    },
    {
        "name": "Janet Yung BaZi Calculator",
        "pages": [
            "https://bazicalculator.janetyung.com/",
        ],
    },
]

FEATURE_RULES = [
    ("免费排盘", [r"free bazi", r"free chart", r"free calculator", r"免费排盘", r"八字排盘"]),
    ("八字", [r"\bbazi\b", r"four pillars", r"four pillar", r"八字"]),
    ("真太阳时", [r"solar time", r"true solar", r"真太阳时"]),
    ("大运流年", [r"luck pillar", r"luck pillars", r"annual luck", r"大运", r"流年"]),
    ("十神", [r"10 gods", r"ten gods", r"十神"]),
    ("神煞", [r"symbolic stars", r"auxiliary stars", r"shen sha", r"神煞"]),
    ("合婚", [r"compatibility", r"love match", r"relationship", r"合婚"]),
    ("风水", [r"feng shui", r"风水"]),
    ("奇门", [r"qi men", r"qimen", r"奇门"]),
    ("课程或会员", [r"academy", r"course", r"courses", r"membership", r"program", r"课程", r"会员"]),
    ("咨询或解读", [r"consult", r"consultation", r"reading", r"analysis", r"interpretation", r"咨询", r"解读"]),
    ("电商/商店", [r"\bshop\b", r"\bstore\b", r"购物", r"商店"]),
]
CTA_PATTERNS = re.compile(
    r"(book|get|start|explore|download|join|sign up|register|consult|buy|shop|view event|learn more|"
    r"立即|开始|获取|下载|加入|咨询|购买|报名)",
    re.I,
)
PRICE_PATTERNS = [
    r"\$\s?\d+(?:\.\d{1,2})?",
    r"usd\s?\d+(?:\.\d{1,2})?",
    r"\d+\s?usd",
    r"￥\s?\d+(?:\.\d{1,2})?",
    r"\d+\s?元",
]
SOCIAL_HOSTS = [
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "linkedin.com",
    "x.com",
    "twitter.com",
    "tiktok.com",
    "telegram.me",
    "t.me",
    "vk.com",
    "rutube.ru",
]
SCHEMA_TYPES = [
    "FAQPage",
    "Organization",
    "WebSite",
    "Course",
    "Product",
    "Article",
    "BreadcrumbList",
    "Event",
]


def sleep_a_bit() -> None:
    time.sleep(random.uniform(*DELAY_RANGE))


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})
    return session


def fetch(session: requests.Session, url: str) -> requests.Response:
    response = session.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    if response.apparent_encoding:
        response.encoding = response.apparent_encoding
    sleep_a_bit()
    return response


def meta_content(soup: BeautifulSoup, name: str) -> str:
    node = soup.find("meta", attrs={"name": re.compile(f"^{re.escape(name)}$", re.I)})
    if not node:
        node = soup.find("meta", attrs={"property": re.compile(f"^{re.escape(name)}$", re.I)})
    return node.get("content", "").strip() if node else ""


def full_text(soup: BeautifulSoup) -> str:
    return " ".join(soup.stripped_strings)


def detect_features(text: str) -> list[str]:
    lower = text.lower()
    found = []
    for name, patterns in FEATURE_RULES:
        if any(re.search(pattern, lower, re.I) for pattern in patterns):
            found.append(name)
    return found


def extract_pricing(text: str) -> list[str]:
    hits = set()
    for pattern in PRICE_PATTERNS:
        for match in re.findall(pattern, text, re.I):
            cleaned = re.sub(r"\s+", "", match).strip()
            if cleaned.lower().startswith("usd"):
                cleaned = f"${cleaned[3:]}"
            hits.add(cleaned)
    if "free" in text.lower() or "免费" in text:
        hits.add("免费")
    return sorted(hits)


def collect_headings(soup: BeautifulSoup) -> dict[str, list[str]]:
    return {
        "h1": [node.get_text(" ", strip=True) for node in soup.find_all("h1")[:10]],
        "h2": [node.get_text(" ", strip=True) for node in soup.find_all("h2")[:15]],
        "h3": [node.get_text(" ", strip=True) for node in soup.find_all("h3")[:20]],
    }


def collect_navigation(soup: BeautifulSoup, base_url: str) -> list[dict[str, str]]:
    items = []
    for node in soup.select("nav a[href], header a[href]"):
        text = node.get_text(" ", strip=True)
        href = urljoin(base_url, node["href"])
        if text:
            items.append({"text": text, "url": href})
    unique = []
    seen = set()
    for item in items:
        key = (item["text"], item["url"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique[:30]


def collect_cta(soup: BeautifulSoup, base_url: str) -> list[dict[str, str]]:
    items = []
    for node in soup.find_all(["a", "button"]):
        text = node.get_text(" ", strip=True)
        if not text or not CTA_PATTERNS.search(text):
            continue
        href = ""
        if node.name == "a" and node.get("href"):
            href = urljoin(base_url, node["href"])
        items.append({"text": text, "url": href})
    unique = []
    seen = set()
    for item in items:
        key = (item["text"], item["url"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique[:20]


def collect_forms(soup: BeautifulSoup, base_url: str) -> list[dict[str, object]]:
    forms = []
    for node in soup.find_all("form"):
        inputs = [item.get("name") or item.get("type") or item.get("id") or "" for item in node.find_all(["input", "select", "textarea"])[:15]]
        forms.append(
            {
                "action": urljoin(base_url, node.get("action", "")),
                "method": (node.get("method") or "get").lower(),
                "fields": [field for field in inputs if field],
            }
        )
    return forms[:10]


def collect_resources(soup: BeautifulSoup, base_url: str) -> tuple[list[str], list[str], list[str]]:
    scripts = [urljoin(base_url, node["src"]) for node in soup.find_all("script", src=True)]
    stylesheets = [
        urljoin(base_url, node["href"])
        for node in soup.find_all("link", href=True)
        if "stylesheet" in " ".join(node.get("rel", [])).lower()
    ]
    images = [urljoin(base_url, node["src"]) for node in soup.find_all("img", src=True)]
    return scripts[:MAX_RESOURCES], stylesheets[:MAX_RESOURCES], images[:MAX_RESOURCES]


def detect_tech_stack(html: str, scripts: list[str], stylesheets: list[str]) -> list[str]:
    html_lower = html.lower()
    joined_scripts = " ".join(scripts).lower()
    joined_styles = " ".join(stylesheets).lower()
    found = []
    if "__next" in html_lower or "_next/" in joined_scripts:
        found.append("Next.js/React")
    elif "react" in html_lower or "react" in joined_scripts:
        found.append("React")
    if "vue" in html_lower or "vue" in joined_scripts:
        found.append("Vue")
    if "jquery" in html_lower or "jquery" in joined_scripts:
        found.append("jQuery")
    if "wp-content" in html_lower or "wp-includes" in joined_scripts or "wp-content" in joined_styles:
        found.append("WordPress")
    if "elementor" in html_lower or "elementor" in joined_scripts:
        found.append("Elementor")
    if "googletagmanager" in html_lower or "googletagmanager" in joined_scripts:
        found.append("Google Tag Manager")
    if "google-analytics" in joined_scripts or "gtag(" in html_lower:
        found.append("Google Analytics")
    if "clarity.ms" in html_lower or "clarity.ms" in joined_scripts:
        found.append("Microsoft Clarity")
    if "stripe" in joined_scripts:
        found.append("Stripe")
    if "cloudflare" in joined_scripts:
        found.append("Cloudflare")
    return found or ["静态HTML或未识别"]


def collect_social_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    links = []
    for node in soup.find_all("a", href=True):
        href = urljoin(base_url, node["href"])
        if any(host in href for host in SOCIAL_HOSTS):
            links.append(href)
    return sorted(set(links))


def collect_internal_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    host = urlparse(base_url).netloc
    links = []
    for node in soup.find_all("a", href=True):
        href = urljoin(base_url, node["href"]).split("#", 1)[0]
        parsed = urlparse(href)
        if parsed.scheme in {"http", "https"} and parsed.netloc == host:
            links.append(href.rstrip("/"))
    return sorted(set(links))[:MAX_INTERNAL_LINKS]


def resource_domains(resources: list[str]) -> list[str]:
    return sorted({urlparse(url).netloc for url in resources if urlparse(url).netloc})


def collect_schema_types(soup: BeautifulSoup) -> list[str]:
    found = set()
    for node in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
        content = node.string or node.get_text(" ", strip=True)
        for schema_type in SCHEMA_TYPES:
            if schema_type.lower() in content.lower():
                found.add(schema_type)
    return sorted(found)


def collect_meta_open_graph(soup: BeautifulSoup) -> dict[str, str]:
    return {
        "og:title": meta_content(soup, "og:title"),
        "og:description": meta_content(soup, "og:description"),
        "og:type": meta_content(soup, "og:type"),
        "og:image": meta_content(soup, "og:image"),
    }


def analyze_page(session: requests.Session, url: str) -> dict[str, object]:
    response = fetch(session, url)
    soup = BeautifulSoup(response.text, "html.parser")
    text = full_text(soup)
    scripts, stylesheets, images = collect_resources(soup, response.url)
    return {
        "url": url,
        "finalUrl": response.url,
        "title": soup.title.get_text(strip=True) if soup.title else "",
        "metaDescription": meta_content(soup, "description"),
        "metaKeywords": meta_content(soup, "keywords"),
        "canonical": next(
            (
                urljoin(response.url, node["href"])
                for node in soup.find_all("link", href=True)
                if "canonical" in " ".join(node.get("rel", [])).lower()
            ),
            "",
        ),
        "openGraph": collect_meta_open_graph(soup),
        "headings": collect_headings(soup),
        "features": detect_features(text),
        "pricing": extract_pricing(text),
        "navigation": collect_navigation(soup, response.url),
        "cta": collect_cta(soup, response.url),
        "forms": collect_forms(soup, response.url),
        "socialLinks": collect_social_links(soup, response.url),
        "internalLinks": collect_internal_links(soup, response.url),
        "structuredDataTypes": collect_schema_types(soup),
        "techStack": detect_tech_stack(response.text, scripts, stylesheets),
        "resources": {
            "scripts": scripts,
            "stylesheets": stylesheets,
            "images": images,
            "scriptDomains": resource_domains(scripts),
            "stylesheetDomains": resource_domains(stylesheets),
        },
        "contentSample": text[:1500],
        "wordCountApprox": len(text.split()),
    }


def summarize_site(pages: list[dict[str, object]]) -> dict[str, object]:
    feature_counter = Counter()
    cta_counter = Counter()
    nav_counter = Counter()
    tech_stack = set()
    pricing = set()
    social = set()
    schema = set()
    domains = set()

    for page in pages:
        feature_counter.update(page["features"])
        cta_counter.update(item["text"] for item in page["cta"])
        nav_counter.update(item["text"] for item in page["navigation"])
        tech_stack.update(page["techStack"])
        pricing.update(page["pricing"])
        social.update(page["socialLinks"])
        schema.update(page["structuredDataTypes"])
        domains.update(page["resources"]["scriptDomains"])
        domains.update(page["resources"]["stylesheetDomains"])

    return {
        "mainFeatures": [item for item, _ in feature_counter.most_common()],
        "pricing": sorted(pricing),
        "techStack": sorted(tech_stack),
        "socialLinks": sorted(social),
        "structuredDataTypes": sorted(schema),
        "topCTA": [item for item, _ in cta_counter.most_common(10)],
        "topNavigation": [item for item, _ in nav_counter.most_common(15)],
        "resourceDomains": sorted(domains),
    }


def render_markdown(results: list[dict[str, object]]) -> str:
    parts = ["# 深度站点信息抽取报告", "", f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
    for site in results:
        summary = site["summary"]
        parts.append(f"## {site['name']}")
        parts.append("")
        parts.append(f"- 抽取页面数：{len(site['pages'])}")
        parts.append(f"- 主要功能：{('、'.join(summary['mainFeatures'])) or '未识别'}")
        parts.append(f"- 定价线索：{('、'.join(summary['pricing'])) or '未见公开价格'}")
        parts.append(f"- 技术栈：{('、'.join(summary['techStack'])) or '未识别'}")
        parts.append(f"- 结构化数据：{('、'.join(summary['structuredDataTypes'])) or '未发现'}")
        parts.append(f"- 社媒：{('、'.join(summary['socialLinks'][:6])) or '未抓到'}")
        parts.append(f"- 主要 CTA：{('、'.join(summary['topCTA'][:8])) or '未明显识别'}")
        parts.append(f"- 主要导航：{('、'.join(summary['topNavigation'][:10])) or '未明显识别'}")
        parts.append("")
        for page in site["pages"]:
            parts.append(f"### {page['title'] or page['finalUrl']}")
            parts.append("")
            parts.append(f"- URL：`{page['finalUrl']}`")
            parts.append(f"- Canonical：`{page['canonical'] or '未设置'}`")
            parts.append(f"- Meta Description：{page['metaDescription'] or '未设置'}")
            parts.append(f"- Meta Keywords：{page['metaKeywords'] or '未设置'}")
            parts.append(f"- H1：{('、'.join(page['headings']['h1'])) or '未抓到'}")
            parts.append(f"- H2：{('、'.join(page['headings']['h2'][:8])) or '未抓到'}")
            parts.append(f"- 功能线索：{('、'.join(page['features'])) or '未识别'}")
            parts.append(f"- 定价线索：{('、'.join(page['pricing'])) or '未见'}")
            parts.append(f"- 表单数：{len(page['forms'])}")
            parts.append(f"- 站内链接样本：{len(page['internalLinks'])} 个")
            parts.append(f"- 资源域名：{('、'.join(page['resources']['scriptDomains'][:8])) or '未抓到'}")
            parts.append("")
        parts.append("")
    return "\n".join(parts).strip() + "\n"


def main() -> int:
    session = make_session()
    results = []
    for target in TARGETS:
        print(f"抓取 {target['name']}")
        pages = [analyze_page(session, url) for url in target["pages"]]
        results.append({"name": target["name"], "pages": pages, "summary": summarize_site(pages)})

    base_dir = Path(__file__).resolve().parent.parent / "data"
    base_dir.mkdir(parents=True, exist_ok=True)
    json_path = base_dir / "deep_site_research.json"
    md_path = base_dir / "deep_site_research.md"
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(results), encoding="utf-8")
    print(json_path)
    print(md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
