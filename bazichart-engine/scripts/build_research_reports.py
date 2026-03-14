#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path


OURS = {"真太阳时", "大运流年", "神煞", "合婚", "PDF报告", "AI解读"}


def load_data() -> list[dict]:
    path = Path(__file__).resolve().parent.parent / "data" / "deep_site_research.json"
    return json.loads(path.read_text(encoding="utf-8"))


def has_feature(site: dict, feature: str) -> bool:
    return feature in site["summary"]["mainFeatures"]


def infer_model(site: dict) -> str:
    features = set(site["summary"]["mainFeatures"])
    nav = " ".join(site["summary"]["topNavigation"]).lower()
    cta = " ".join(site["summary"]["topCTA"]).lower()
    if "课程或会员" in features and "咨询或解读" in features and "电商/商店" in features:
        return "平台化商业闭环"
    if "课程或会员" in features and "咨询或解读" in features:
        return "课程+咨询转化"
    if "免费排盘" in features and "咨询或解读" in features:
        return "免费工具获客"
    if "academy" in nav or "membership" in nav or "membership" in cta:
        return "会员/课程导向"
    return "内容导向"


def lead_magnets(site: dict) -> list[str]:
    texts = site["summary"]["topCTA"] + site["summary"]["topNavigation"]
    found = []
    for text in texts:
        lower = text.lower()
        if "free e-book" in lower or "ebook" in lower:
            found.append("免费电子书")
        if "sample" in lower:
            found.append("报告样本")
        if "membership" in lower:
            found.append("会员入口")
        if "sign up" in lower:
            found.append("注册订阅")
        if "book consultation" in lower or "consultation" in lower or "consulting" in lower:
            found.append("咨询预约")
        if "course" in lower or "academy" in lower:
            found.append("课程招生")
        if "event" in lower:
            found.append("活动引流")
        if "shop" in lower or "bookstore" in lower or "store" in lower:
            found.append("商店导流")
    return list(dict.fromkeys(found))


def seo_signals(site: dict) -> list[str]:
    signals = []
    for page in site["pages"]:
        if page["metaKeywords"]:
            signals.append("有 meta keywords")
            break
    if site["summary"]["structuredDataTypes"]:
        signals.append("有结构化数据")
    if any(page["canonical"] for page in site["pages"]):
        signals.append("有 canonical")
    if any(page["headings"]["h1"] for page in site["pages"]):
        signals.append("有明确 H1")
    if any("FAQPage" == item for item in site["summary"]["structuredDataTypes"]):
        signals.append("有 FAQ 结构化数据")
    return signals


def traffic_strategy(site: dict) -> str:
    nav = " ".join(site["summary"]["topNavigation"]).lower()
    cta = " ".join(site["summary"]["topCTA"]).lower()
    features = set(site["summary"]["mainFeatures"])
    if "event" in nav or "event" in cta:
        return "内容/活动驱动"
    if "academy" in nav or "course" in nav or "课程或会员" in features:
        return "课程漏斗驱动"
    if "consult" in cta or "consultation" in cta:
        return "咨询转化驱动"
    if "免费排盘" in features:
        return "工具 SEO 驱动"
    return "品牌内容驱动"


def compare_markdown(sites: list[dict]) -> str:
    rows = []
    for site in sites:
        summary = site["summary"]
        rows.append(
            "| {name} | {free_chart} | {solar} | {luck} | {ten_gods} | {stars} | {consult} | {course} | {shop} | {pricing} | {tech} | {cta} |".format(
                name=site["name"],
                free_chart="是" if has_feature(site, "免费排盘") else "否",
                solar="是" if has_feature(site, "真太阳时") else "否",
                luck="是" if has_feature(site, "大运流年") else "否",
                ten_gods="是" if has_feature(site, "十神") else "否",
                stars="是" if has_feature(site, "神煞") else "否",
                consult="是" if has_feature(site, "咨询或解读") else "否",
                course="是" if has_feature(site, "课程或会员") else "否",
                shop="是" if has_feature(site, "电商/商店") else "否",
                pricing="、".join(summary["pricing"]) or "未见",
                tech=" / ".join(summary["techStack"][:4]),
                cta="、".join(summary["topCTA"][:3]) or "未识别",
            )
        )

    return (
        "# 高价值字段对比表\n\n"
        f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "| 网站 | 免费排盘 | 真太阳时 | 大运流年 | 十神 | 神煞 | 咨询 | 课程/会员 | 商店 | 定价线索 | 技术栈 | 主要CTA |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        + "\n".join(rows)
        + "\n"
    )


def business_markdown(sites: list[dict]) -> str:
    parts = ["# 商业分析版报告", "", f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
    competitor_features = set()
    for site in sites:
        competitor_features.update(site["summary"]["mainFeatures"])

    for site in sites:
        summary = site["summary"]
        parts.append(f"## {site['name']}")
        parts.append("")
        parts.append(f"- 商业模式：{infer_model(site)}")
        parts.append(f"- 流量策略：{traffic_strategy(site)}")
        parts.append(f"- Lead Magnet：{('、'.join(lead_magnets(site))) or '未明显识别'}")
        parts.append(f"- 主要功能：{('、'.join(summary['mainFeatures'])) or '未识别'}")
        parts.append(f"- 主要 CTA：{('、'.join(summary['topCTA'][:6])) or '未识别'}")
        parts.append(f"- 主要导航：{('、'.join(summary['topNavigation'][:10])) or '未识别'}")
        parts.append(f"- SEO 信号：{('、'.join(seo_signals(site))) or '较弱'}")
        parts.append(f"- 社媒布局：{len(summary['socialLinks'])} 个公开入口")
        parts.append("")

    parts.append("## 横向结论")
    parts.append("")
    parts.append("- 最强工具深度：MingLi、Master Sean Chan。")
    parts.append("- 最强品牌/课程体系：Joey Yap、Marlyna Consulting。")
    parts.append("- 最明显免费引流漏斗：Janet Yung、Marlyna Consulting、Master Sean Chan。")
    parts.append("- 最完整商业闭环：Joey Yap、Marlyna Consulting、MingLi。")
    parts.append("")
    parts.append("## 对我们的启发")
    parts.append("")
    parts.append(f"- 我们已有：{('、'.join(sorted(OURS)))}。")
    parts.append(f"- 竞品高频出现而我们应重点关注：{('、'.join(sorted(competitor_features - OURS)))}。")
    parts.append("- 值得优先补的商业化抓手：免费样本报告、咨询预约入口、课程/会员承接、活动/内容漏斗。")
    parts.append("- 值得优先补的 SEO 抓手：FAQ 结构化数据、工具页长尾词、结果页关键词、下载样本页。")
    parts.append("")
    return "\n".join(parts)


def comparison_json(sites: list[dict]) -> list[dict]:
    rows = []
    for site in sites:
        summary = site["summary"]
        rows.append(
            {
                "site": site["name"],
                "freeChart": has_feature(site, "免费排盘"),
                "trueSolarTime": has_feature(site, "真太阳时"),
                "luckPillars": has_feature(site, "大运流年"),
                "tenGods": has_feature(site, "十神"),
                "shenSha": has_feature(site, "神煞"),
                "consulting": has_feature(site, "咨询或解读"),
                "coursesOrMembership": has_feature(site, "课程或会员"),
                "shop": has_feature(site, "电商/商店"),
                "pricing": summary["pricing"],
                "techStack": summary["techStack"],
                "leadMagnets": lead_magnets(site),
                "businessModel": infer_model(site),
                "trafficStrategy": traffic_strategy(site),
                "seoSignals": seo_signals(site),
            }
        )
    return rows


def main() -> int:
    sites = load_data()
    data_dir = Path(__file__).resolve().parent.parent / "data"

    compare_md = data_dir / "research_comparison_table.md"
    compare_json = data_dir / "research_comparison_table.json"
    business_md = data_dir / "research_business_analysis.md"

    compare_md.write_text(compare_markdown(sites), encoding="utf-8")
    compare_json.write_text(json.dumps(comparison_json(sites), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    business_md.write_text(business_markdown(sites), encoding="utf-8")

    print(compare_md)
    print(compare_json)
    print(business_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
