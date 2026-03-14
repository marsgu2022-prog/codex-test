#!/usr/bin/env python3
from __future__ import annotations

import json
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 20
REQUEST_DELAY_RANGE = (1.0, 2.0)
MAX_BAZI_LAB_PAGES = 25

TARGET_SITES = [
    {"name": "BaZi Lab", "url": "https://www.bazi-lab.com", "focus": True, "lang": "en"},
    {"name": "Master Tsai", "url": "https://www.mastertsai.com", "focus": False, "lang": "en"},
    {"name": "SkillOn", "url": "https://www.skillon.com/bazi-calculator.cfm", "focus": False, "lang": "en"},
    {"name": "Master Sean Chan", "url": "https://www.masterseanchan.com/bazi-calculator/", "focus": False, "lang": "en"},
    {"name": "FS In Motion", "url": "https://fsinmotion.com/bazi-calculator/", "focus": False, "lang": "en"},
    {"name": "Feng Shui Xin Yu", "url": "https://fengshuixinyu.com/bazi-calculator/", "focus": False, "lang": "en"},
    {"name": "Marlyna Consulting", "url": "https://marlynaconsulting.com/ba-zi-calculator/", "focus": False, "lang": "en"},
    {"name": "MingLi", "url": "https://www.mingli.info/bazi", "focus": False, "lang": "en"},
    {"name": "算准网", "url": "https://www.suanzhun.net", "focus": False, "lang": "zh"},
    {"name": "卜易居", "url": "https://pp.buyiju.com", "focus": False, "lang": "zh"},
    {"name": "华易网手机版", "url": "https://m.life.httpcn.com/bzpaipan/", "focus": False, "lang": "zh"},
    {"name": "易算网", "url": "https://yisuan.net/app/paipan", "focus": False, "lang": "zh"},
    {"name": "天兔黄历", "url": "https://pan.tthuangli.com", "focus": False, "lang": "zh"},
    {"name": "问真八字排盘", "url": "https://pcbz.iwzwh.com", "focus": False, "lang": "zh"},
]

FEATURE_RULES = [
    ("免费排盘", [r"免费排盘", r"免费八字", r"free bazi", r"free chart", r"free calculator"]),
    ("付费解读", [r"付费", r"咨询", r"解读服务", r"purchase", r"pricing", r"\$\d+", r"usd"]),
    ("AI分析", [r"\bai\b", r"人工智能", r"智能解读", r"gpt", r"chatgpt"]),
    ("真太阳时", [r"真太阳时", r"solar time", r"true solar"]),
    ("大运流年", [r"大运", r"流年", r"luck pillar", r"annual luck", r"10-year luck"]),
    ("神煞", [r"神煞", r"shen sha", r"stars?"]),
    ("合婚", [r"合婚", r"compatibility", r"matchmaking", r"relationship"]),
    ("PDF报告", [r"pdf", r"report download", r"下载报告"]),
]
PRICE_PATTERNS = [
    r"\$\s?\d+(?:\.\d{1,2})?",
    r"usd\s?\d+(?:\.\d{1,2})?",
    r"￥\s?\d+(?:\.\d{1,2})?",
    r"rmb\s?\d+(?:\.\d{1,2})?",
    r"\d+\s?元",
]
SOCIAL_DOMAINS = [
    "facebook.com",
    "instagram.com",
    "x.com",
    "twitter.com",
    "youtube.com",
    "linkedin.com",
    "tiktok.com",
    "wechat",
    "weibo.com",
    "xiaohongshu.com",
]
SCHEMA_TYPES = [
    "FAQPage",
    "Organization",
    "WebSite",
    "SoftwareApplication",
    "Product",
    "Article",
    "BreadcrumbList",
]


@dataclass
class SiteResult:
    name: str
    url: str
    status: str
    data: dict[str, Any]


def sleep_between_requests() -> None:
    time.sleep(random.uniform(*REQUEST_DELAY_RANGE))


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})
    return session


def fetch_url(session: requests.Session, url: str) -> requests.Response | None:
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        if response.apparent_encoding:
            response.encoding = response.apparent_encoding
        sleep_between_requests()
        return response
    except requests.RequestException:
        return None


def normalized_text(soup: BeautifulSoup) -> str:
    return " ".join(soup.stripped_strings)


def get_meta_content(soup: BeautifulSoup, name: str) -> str:
    node = soup.find("meta", attrs={"name": re.compile(f"^{re.escape(name)}$", re.I)})
    if not node:
        node = soup.find("meta", attrs={"property": re.compile(f"^{re.escape(name)}$", re.I)})
    return node.get("content", "").strip() if node else ""


def collect_features(text: str) -> list[str]:
    lower_text = text.lower()
    found = []
    for feature, patterns in FEATURE_RULES:
        if any(re.search(pattern, lower_text, re.I) for pattern in patterns):
            found.append(feature)
    return found


def collect_pricing(text: str) -> list[str]:
    hits = set()
    for pattern in PRICE_PATTERNS:
        for match in re.findall(pattern, text, re.I):
            normalized = re.sub(r"\s+", "", match).strip()
            if normalized.lower().startswith("usd"):
                normalized = f"${normalized[3:]}"
            hits.add(normalized)
    if "免费" in text or "free" in text.lower():
        hits.add("免费")
    return sorted(hits)


def detect_tech_stack(html: str, scripts: list[str], stylesheets: list[str]) -> list[str]:
    signals: list[str] = []
    html_lower = html.lower()
    joined_scripts = " ".join(scripts).lower()
    joined_styles = " ".join(stylesheets).lower()
    if "__next" in html_lower or "_next/" in joined_scripts:
        signals.append("Next.js/React")
    elif "react" in html_lower or "react" in joined_scripts:
        signals.append("React")
    if "vue" in html_lower or "vue" in joined_scripts:
        signals.append("Vue")
    if "jquery" in html_lower or "jquery" in joined_scripts:
        signals.append("jQuery")
    if "wp-content" in html_lower or "wp-includes" in joined_scripts or "wp-content" in joined_styles:
        signals.append("WordPress")
    if "cloudflare" in joined_scripts:
        signals.append("Cloudflare")
    if "gtag" in html_lower or "google-analytics" in joined_scripts:
        signals.append("Google Analytics")
    if "googletagmanager" in html_lower or "googletagmanager" in joined_scripts:
        signals.append("Google Tag Manager")
    if "clarity.ms" in html_lower:
        signals.append("Microsoft Clarity")
    if "stripe" in joined_scripts:
        signals.append("Stripe")
    if not signals:
        signals.append("静态HTML或未识别")
    return list(dict.fromkeys(signals))


def collect_resources(soup: BeautifulSoup, base_url: str) -> tuple[list[str], list[str]]:
    scripts = []
    for node in soup.find_all("script", src=True):
        scripts.append(urljoin(base_url, node["src"]))
    stylesheets = []
    for node in soup.find_all("link", href=True):
        rel = " ".join(node.get("rel", [])).lower()
        if "stylesheet" in rel:
            stylesheets.append(urljoin(base_url, node["href"]))
    return scripts, stylesheets


def collect_social_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    results = []
    for node in soup.find_all("a", href=True):
        href = urljoin(base_url, node["href"])
        if any(domain in href for domain in SOCIAL_DOMAINS):
            results.append(href)
    return sorted(set(results))


def collect_h1(soup: BeautifulSoup) -> list[str]:
    return [node.get_text(" ", strip=True) for node in soup.find_all("h1")]


def collect_structured_data(soup: BeautifulSoup) -> list[str]:
    found = []
    for node in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
        content = node.string or node.get_text(" ", strip=True)
        for schema_type in SCHEMA_TYPES:
            if schema_type.lower() in content.lower():
                found.append(schema_type)
    return sorted(set(found))


def detect_js_rendering(text: str, features: list[str], scripts: list[str]) -> bool:
    very_short = len(text) < 400
    framework_heavy = any(tag in script.lower() for script in scripts for tag in ("react", "vue", "_next", "nuxt"))
    return very_short and framework_heavy and not features


def extract_internal_links(soup: BeautifulSoup, root_url: str) -> list[str]:
    root_host = urlparse(root_url).netloc
    links = set()
    for node in soup.find_all("a", href=True):
        href = urljoin(root_url, node["href"])
        parsed = urlparse(href)
        if parsed.scheme in {"http", "https"} and parsed.netloc == root_host:
            cleaned = href.split("#", 1)[0]
            links.add(cleaned.rstrip("/"))
    return sorted(links)


def extract_api_clues(html: str, scripts: list[str], base_url: str) -> list[str]:
    matches = set()
    patterns = [
        r"""fetch\(\s*['"]([^'"]+)['"]""",
        r"""axios\.(?:get|post|request)\(\s*['"]([^'"]+)['"]""",
        r"""url:\s*['"]([^'"]+)['"]""",
        r"""['"](/api/[^'"]+)['"]""",
        r"""['"](https?://[^'"]*/api/[^'"]*)['"]""",
    ]
    for pattern in patterns:
        for found in re.findall(pattern, html, re.I):
            candidate = urljoin(base_url, found)
            if "localhost" not in candidate and "127.0.0.1" not in candidate:
                matches.add(candidate)
    for script_url in scripts:
        if any(token in script_url.lower() for token in ("api", "trpc", "graphql")):
            if "localhost" not in script_url and "127.0.0.1" not in script_url:
                matches.add(script_url)
    return sorted(matches)


def extract_api_clues_from_scripts(session: requests.Session, scripts: list[str], base_url: str, limit: int = 8) -> list[str]:
    matches = set()
    for script_url in scripts[:limit]:
        response = fetch_url(session, script_url)
        if response is None:
            continue
        matches.update(extract_api_clues(response.text, [], base_url))
    return sorted(matches)


def analyze_page(base_url: str, response: requests.Response) -> dict[str, Any]:
    soup = BeautifulSoup(response.text, "html.parser")
    page_text = normalized_text(soup)
    scripts, stylesheets = collect_resources(soup, base_url)
    features = collect_features(page_text)
    return {
        "finalUrl": response.url,
        "title": soup.title.get_text(strip=True) if soup.title else "",
        "metaDescription": get_meta_content(soup, "description"),
        "metaKeywords": get_meta_content(soup, "keywords"),
        "features": features,
        "pricing": collect_pricing(page_text),
        "techStack": detect_tech_stack(response.text, scripts, stylesheets),
        "seo": {
            "h1": collect_h1(soup),
            "canonical": next(
                (
                    urljoin(base_url, node["href"])
                    for node in soup.find_all("link", href=True)
                    if "canonical" in " ".join(node.get("rel", [])).lower()
                ),
                "",
            ),
            "structuredDataTypes": collect_structured_data(soup),
        },
        "socialLinks": collect_social_links(soup, base_url),
        "externalResources": {
            "scripts": scripts,
            "stylesheets": stylesheets,
        },
        "jsRenderingRequired": detect_js_rendering(page_text, features, scripts),
        "internalLinks": extract_internal_links(soup, response.url),
        "apiClues": extract_api_clues(response.text, scripts, response.url),
        "contentSample": page_text[:500],
    }


def crawl_site(session: requests.Session, name: str, url: str) -> SiteResult:
    response = fetch_url(session, url)
    if response is None:
        return SiteResult(name=name, url=url, status="skipped", data={"reason": "请求失败"})
    data = analyze_page(url, response)
    return SiteResult(name=name, url=url, status="ok", data=data)


def crawl_bazi_lab_subpages(session: requests.Session, site_data: dict[str, Any]) -> dict[str, Any]:
    root_url = site_data["finalUrl"]
    queue = list(site_data.get("internalLinks", []))
    seen = {root_url.rstrip("/")}
    pages = []
    api_clues = set(site_data.get("apiClues", []))
    api_clues.update(
        extract_api_clues_from_scripts(
            session,
            site_data.get("externalResources", {}).get("scripts", []),
            root_url,
        )
    )

    while queue and len(pages) < MAX_BAZI_LAB_PAGES:
        url = queue.pop(0)
        normalized = url.rstrip("/")
        if normalized in seen:
            continue
        seen.add(normalized)
        response = fetch_url(session, url)
        if response is None:
            continue
        page = analyze_page(url, response)
        pages.append(
            {
                "url": response.url,
                "title": page["title"],
                "features": page["features"],
                "h1": page["seo"]["h1"],
                "pricing": page["pricing"],
                "jsRenderingRequired": page["jsRenderingRequired"],
            }
        )
        api_clues.update(page.get("apiClues", []))
        api_clues.update(
            extract_api_clues_from_scripts(
                session,
                page.get("externalResources", {}).get("scripts", []),
                response.url,
                limit=4,
            )
        )
        for child in page.get("internalLinks", []):
            if child.rstrip("/") not in seen:
                queue.append(child)

    return {
        "subpages": pages,
        "subpageCount": len(pages),
        "apiClues": sorted(api_clues),
    }


def feature_matrix_entry(site: dict[str, Any]) -> dict[str, Any]:
    features = set(site.get("features", []))
    pricing = site.get("pricing", [])
    return {
        "网站": site["name"],
        "免费排盘": "是" if "免费排盘" in features else "否",
        "AI解读": "是" if "AI分析" in features else "否",
        "真太阳时": "是" if "真太阳时" in features else "否",
        "大运流年": "是" if "大运流年" in features else "否",
        "神煞": "是" if "神煞" in features else "否",
        "合婚": "是" if "合婚" in features else "否",
        "PDF": "是" if "PDF报告" in features else "否",
        "付费模式": "、".join(pricing) if pricing else "未见公开定价",
        "技术栈": " / ".join(site.get("techStack", [])),
    }


def our_feature_set() -> set[str]:
    return {"真太阳时", "大运流年", "神煞", "合婚", "PDF报告"}


def calculate_gap_analysis(sites: list[dict[str, Any]]) -> dict[str, list[str]]:
    competitor_features = set()
    for site in sites:
        competitor_features.update(site.get("features", []))
    ours = our_feature_set()
    return {
        "oursOnly": sorted(ours - competitor_features),
        "competitorOnly": sorted(competitor_features - ours),
    }


def seo_opportunities(sites: list[dict[str, Any]]) -> list[str]:
    opportunities = []
    missing_keywords = [site["name"] for site in sites if not site.get("metaKeywords")]
    if missing_keywords:
        opportunities.append(f"部分竞品未设置 meta keywords，可优先围绕八字排盘、真太阳时、AI 解读建立更聚焦的关键词簇。")
    if any(not site.get("seo", {}).get("structuredDataTypes") for site in sites):
        opportunities.append("多个竞品未明显使用结构化数据，可补充 FAQPage、WebSite、SoftwareApplication 提升富结果机会。")
    if any(len(site.get("seo", {}).get("h1", [])) == 0 for site in sites):
        opportunities.append("部分竞品 H1 结构较弱，可围绕主关键词与长尾词设计更清晰的标题层级。")
    if any(site.get("jsRenderingRequired") for site in sites):
        opportunities.append("存在依赖 JS 渲染的竞品，可用服务端渲染或静态化内容抢占可抓取性优势。")
    return opportunities


def render_markdown_report(sites: list[dict[str, Any]], bazi_lab_deep: dict[str, Any], gaps: dict[str, list[str]]) -> str:
    overview_rows = []
    for site in sites:
        row = feature_matrix_entry(site)
        overview_rows.append(
            f"| {row['网站']} | {row['免费排盘']} | {row['AI解读']} | {row['真太阳时']} | {row['大运流年']} | "
            f"{row['神煞']} | {row['合婚']} | {row['PDF']} | {row['付费模式']} | {row['技术栈']} |"
        )

    bazi_lab = next((site for site in sites if site["name"] == "BaZi Lab"), {})
    api_lines = "\n".join(f"- {item}" for item in bazi_lab_deep.get("apiClues", [])[:20]) or "- 未发现明显 API 线索"
    subpage_lines = "\n".join(
        f"- {item['title'] or '无标题'}: {item['url']}" for item in bazi_lab_deep.get("subpages", [])[:20]
    ) or "- 未抓到额外子页面"

    keyword_lines = "\n".join(
        f"- {site['name']}: {site.get('metaKeywords') or '未设置'}"
        for site in sites
    )
    seo_lines = "\n".join(f"- {item}" for item in seo_opportunities(sites))
    ours_only = "\n".join(f"- {item}" for item in gaps["oursOnly"]) or "- 暂无明显独有功能"
    competitor_only = "\n".join(f"- {item}" for item in gaps["competitorOnly"]) or "- 暂无明显竞品独有功能"

    return (
        "# 八字排盘竞品分析报告\n\n"
        "## 一、竞品概览表\n"
        "| 网站 | 免费排盘 | AI解读 | 真太阳时 | 大运流年 | 神煞 | 合婚 | PDF | 付费模式 | 技术栈 |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        f"{chr(10).join(overview_rows)}\n\n"
        "## 二、重点竞品深度分析\n"
        "### BaZi Lab (bazi-lab.com)\n"
        f"- 标题：{bazi_lab.get('title', '') or '未获取'}\n"
        f"- 描述：{bazi_lab.get('metaDescription', '') or '未获取'}\n"
        f"- 主要功能：{('、'.join(bazi_lab.get('features', []))) or '未明显识别'}\n"
        f"- 定价信息：{('、'.join(bazi_lab.get('pricing', []))) or '未见公开定价'}\n"
        f"- 技术栈线索：{(' / '.join(bazi_lab.get('techStack', []))) or '未识别'}\n"
        f"- H1：{('；'.join(bazi_lab.get('seo', {}).get('h1', []))) or '未获取'}\n"
        f"- Canonical：{bazi_lab.get('seo', {}).get('canonical') or '未设置'}\n"
        f"- 结构化数据：{('、'.join(bazi_lab.get('seo', {}).get('structuredDataTypes', []))) or '未发现'}\n"
        f"- 需 JS 渲染：{'是' if bazi_lab.get('jsRenderingRequired') else '否'}\n"
        "- 子页面样本：\n"
        f"{subpage_lines}\n"
        "- API 线索：\n"
        f"{api_lines}\n\n"
        "## 三、功能差距分析\n"
        "- 我们有而竞品没有的\n"
        f"{ours_only}\n"
        "- 竞品有而我们没有的\n"
        f"{competitor_only}\n\n"
        "## 四、SEO策略分析\n"
        "- 各竞品的关键词策略\n"
        f"{keyword_lines}\n"
        "- 我们的SEO机会\n"
        f"{seo_lines}\n"
    )


def to_serializable(site_result: SiteResult) -> dict[str, Any]:
    payload = {"name": site_result.name, "url": site_result.url, "status": site_result.status}
    payload.update(site_result.data)
    return payload


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent
    output_dir = root_dir / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    session = make_session()
    results: list[SiteResult] = []
    print("开始抓取竞品页面...")
    for site in TARGET_SITES:
        print(f"- 抓取 {site['name']}: {site['url']}")
        result = crawl_site(session, site["name"], site["url"])
        results.append(result)

    successful_sites = [to_serializable(item) for item in results if item.status == "ok"]
    bazi_lab_site = next((item for item in results if item.name == "BaZi Lab" and item.status == "ok"), None)
    bazi_lab_deep = {"subpages": [], "subpageCount": 0, "apiClues": []}
    if bazi_lab_site is not None:
        print("- 深度分析 BaZi Lab 子页面")
        bazi_lab_deep = crawl_bazi_lab_subpages(session, bazi_lab_site.data)

    gaps = calculate_gap_analysis(successful_sites)
    markdown = render_markdown_report(successful_sites, bazi_lab_deep, gaps)
    payload = {
        "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sites": successful_sites,
        "skippedSites": [to_serializable(item) for item in results if item.status != "ok"],
        "baziLabDeepDive": bazi_lab_deep,
        "featureMatrix": [feature_matrix_entry(site) for site in successful_sites],
        "gapAnalysis": gaps,
        "seoOpportunities": seo_opportunities(successful_sites),
    }

    (output_dir / "competitor_analysis.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "competitor_report.md").write_text(markdown, encoding="utf-8")
    print(f"输出完成：{output_dir / 'competitor_analysis.json'}")
    print(f"输出完成：{output_dir / 'competitor_report.md'}")
    print(f"成功站点数: {len(successful_sites)}，跳过站点数: {len(results) - len(successful_sites)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
