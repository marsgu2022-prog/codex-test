from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "scripts" / "crawl_mysticism_library.py"
SPEC = spec_from_file_location("crawl_mysticism_library", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["crawl_mysticism_library"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_build_library_record_contains_required_fields():
    seed = {
        "key": "bazi",
        "title_zh_hans": "八字",
        "title_en": "Four Pillars of Destiny",
        "category": "concept",
        "tags": ["八字", "四柱"],
    }
    record = MODULE.build_library_record(
        seed,
        {"title": "八字", "summary": "四柱命理系统", "source_url": "https://zh.wikipedia.org/wiki/八字"},
        {"title": "Four Pillars of Destiny", "summary": "A Chinese astrological system", "source_url": "https://en.wikipedia.org/wiki/Four_Pillars_of_Destiny"},
        ["干支", "十神", "命理学"],
        ["Sexagenary cycle", "Chinese astrology"],
    )

    assert record["title_zh_hans"] == "八字"
    assert record["title_zh_hant"] == "八字"
    assert record["title_en"] == "Four Pillars of Destiny"
    assert record["summary_zh_hans"] == "四柱命理系统"
    assert record["summary_zh_hant"] == "四柱命理系統"
    assert record["summary_en"] == "A Chinese astrological system"
    assert record["category"] == "concept"
    assert record["tags"] == ["八字", "四柱"]
    assert record["source_type"] == "wikipedia"
    assert record["source_priority"] == 1
    assert record["quality_tier"] == "A"
    assert record["source_url"] == "https://zh.wikipedia.org/wiki/八字"
    assert record["related_titles"] == ["干支", "十神", "命理学", "Sexagenary cycle", "Chinese astrology"]


def test_dedupe_titles_respects_order_and_limit():
    values = ["八字", "八字", "风水", "紫微斗数"]
    assert MODULE.dedupe_titles(values, limit=2) == ["八字", "风水"]


def test_build_topic_library_uses_seed_topics(monkeypatch):
    calls = []

    def fake_fetch_page_summary(session, language, title):
        calls.append(("summary", language, title))
        return {
            "title": title,
            "summary": f"{language}:{title}",
            "source_url": f"https://{language}.example/{title}",
        }

    def fake_fetch_page_links(session, language, title, limit=MODULE.LINK_FETCH_LIMIT):
        calls.append(("links", language, title, limit))
        return [f"{title}-link-a", f"{title}-link-b"]

    monkeypatch.setattr(MODULE, "fetch_page_summary", fake_fetch_page_summary)
    monkeypatch.setattr(MODULE, "fetch_page_links", fake_fetch_page_links)

    records = MODULE.build_topic_library(object(), seeds=MODULE.TOPIC_SEEDS[:2])

    assert len(records) == 2
    assert records[0]["key"] == "bazi"
    assert records[1]["key"] == "feng_shui"
    assert records[0]["related_titles"] == [
        "八字-link-a",
        "八字-link-b",
        "Four Pillars of Destiny-link-a",
        "Four Pillars of Destiny-link-b",
    ]
    assert calls[0] == ("summary", "zh", "八字")
    assert calls[1] == ("summary", "en", "Four Pillars of Destiny")


def test_build_report_counts_categories():
    report = MODULE.build_report(
        [
            {"key": "bazi", "category": "concept"},
            {"key": "feng_shui", "category": "practice"},
            {"key": "ziwei_doushu", "category": "concept"},
        ]
    )

    assert report["total_records"] == 3
    assert report["categories"] == {"concept": 2, "practice": 1}
    assert report["seed_keys"] == ["bazi", "feng_shui", "ziwei_doushu"]


def test_build_case_record_for_bazi_contains_required_fields():
    record = MODULE.build_case_record(MODULE.CASE_SEEDS[0])

    assert record["case_id"] == "bazi-sample-001"
    assert record["case_type"] == "bazi"
    assert record["title_zh_hans"] == "八字案例占位样本"
    assert record["title_zh_hant"] == "八字案例佔位樣本"
    assert record["title_en"] == "Bazi sample case"
    assert record["source_priority"] == 1
    assert record["quality_tier"] == "A"
    assert "birth_date" in record
    assert "pillars" in record
    assert "major_structure" in record
    assert "property_type" not in record


def test_build_case_record_for_fengshui_contains_layout_fields():
    record = MODULE.build_case_record(MODULE.CASE_SEEDS[2])

    assert record["case_type"] == "fengshui"
    assert record["property_type"] is None
    assert record["layout_features"] == []
    assert record["issue"] is None
    assert record["adjustment"] is None
    assert record["outcome"] is None
    assert "birth_date" not in record


def test_build_case_library_returns_three_case_types():
    cases = MODULE.build_case_library()

    assert [item["case_type"] for item in cases] == ["bazi", "ziwei", "fengshui"]
