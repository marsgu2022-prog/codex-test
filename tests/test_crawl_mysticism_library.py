from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from unittest.mock import Mock


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


def test_expand_topic_seeds_from_categories_builds_unique_reference_seeds(monkeypatch):
    monkeypatch.setattr(
        MODULE,
        "fetch_category_titles",
        lambda session, language, category, limit=MODULE.CATEGORY_MEMBER_LIMIT: ["八字", "风水新解"] if language == "zh" else ["Feng shui", "I Ching divination"],
    )

    expanded = MODULE.expand_topic_seeds_from_categories(object(), limit_per_category=3)

    keys = [item["key"] for item in expanded]
    assert "zh_风水新解" in keys
    assert "en_i_ching_divination" in keys
    assert all(item["category"] == "reference" for item in expanded)


def test_expand_topic_seeds_from_categories_records_each_failed_category(monkeypatch):
    def fake_fetch_category_titles(session, language, category, limit=MODULE.CATEGORY_MEMBER_LIMIT):
        if language == "zh":
            raise MODULE.requests.RequestException("429 Too Many Requests")
        return ["Divination"]

    monkeypatch.setattr(MODULE, "fetch_category_titles", fake_fetch_category_titles)

    failures = []
    progress = MODULE.create_progress_report()
    expanded = MODULE.expand_topic_seeds_from_categories(object(), failure_log=failures, progress=progress)

    assert any(item["key"] == "en_divination" for item in expanded)
    assert len(failures) == 4
    assert all(item["stage"] == "category" and item["language"] == "zh" for item in failures)
    assert progress["categories"] == {"requested": 8, "completed": 4, "failed": 4}


def test_build_topic_library_can_include_category_expansion(monkeypatch):
    monkeypatch.setattr(
        MODULE,
        "expand_topic_seeds_from_categories",
        lambda session, limit_per_category=MODULE.CATEGORY_MEMBER_LIMIT, failure_log=None, progress=None: [
            {"key": "zh_sample", "title_zh_hans": "堪舆注解", "title_en": "Kanyu notes", "category": "reference", "tags": ["玄学", "扩展"]}
        ],
    )
    monkeypatch.setattr(
        MODULE,
        "fetch_page_summary",
        lambda session, language, title: {"title": title, "summary": f"{language}:{title}", "source_url": f"https://{language}.example/{title}"},
    )
    monkeypatch.setattr(MODULE, "fetch_page_links", lambda session, language, title, limit=MODULE.LINK_FETCH_LIMIT: [])

    records = MODULE.build_topic_library(object(), seeds=MODULE.TOPIC_SEEDS[:1], include_categories=True, category_limit=3)

    assert [item["key"] for item in records] == ["bazi", "zh_sample"]


def test_expand_topic_seeds_from_categories_skips_failed_category(monkeypatch):
    def fake_fetch_category_titles(session, language, category, limit=MODULE.CATEGORY_MEMBER_LIMIT):
        if category == "Category:道教占卜":
            raise MODULE.requests.RequestException("429 Too Many Requests")
        return ["八字扩展"] if language == "zh" else []

    monkeypatch.setattr(MODULE, "fetch_category_titles", fake_fetch_category_titles)

    failures = []
    expanded = MODULE.expand_topic_seeds_from_categories(object(), failure_log=failures)

    assert any(item["key"] == "zh_八字扩展" for item in expanded)
    assert any(item["stage"] == "category" and item["target"] == "Category:道教占卜" for item in failures)


def test_build_topic_library_keeps_partial_record_when_one_language_fails(monkeypatch):
    def fake_fetch_page_summary(session, language, title):
        if language == "en":
            raise MODULE.requests.RequestException("gateway timeout")
        return {
            "title": title,
            "summary": f"{language}:{title}",
            "source_url": f"https://{language}.example/{title}",
        }

    monkeypatch.setattr(MODULE, "fetch_page_summary", fake_fetch_page_summary)
    monkeypatch.setattr(MODULE, "fetch_page_links", lambda session, language, title, limit=MODULE.LINK_FETCH_LIMIT: [])

    failures = []
    progress = MODULE.create_progress_report()
    records = MODULE.build_topic_library(object(), seeds=MODULE.TOPIC_SEEDS[:1], failure_log=failures, progress=progress)

    assert len(records) == 1
    assert records[0]["summary_zh_hans"] == "zh:八字"
    assert records[0]["summary_en"] == "zh:八字"
    assert any(item["stage"] == "summary" and item["language"] == "en" for item in failures)
    assert progress["topics"] == {"requested": 1, "completed": 0, "partial": 1, "skipped": 0}


def test_build_topic_library_skips_seed_when_both_languages_fail(monkeypatch):
    monkeypatch.setattr(
        MODULE,
        "fetch_page_summary",
        lambda session, language, title: (_ for _ in ()).throw(MODULE.requests.RequestException("down")),
    )

    failures = []
    progress = MODULE.create_progress_report()
    records = MODULE.build_topic_library(object(), seeds=MODULE.TOPIC_SEEDS[:1], failure_log=failures, progress=progress)

    assert records == []
    assert any(item["stage"] == "record" and item["target"] == "bazi" for item in failures)
    assert progress["topics"] == {"requested": 1, "completed": 0, "partial": 0, "skipped": 1}


def test_topic_seeds_include_high_value_books_and_works():
    expected = {
        "yuan_hai_zi_ping": ("book", "渊海子平"),
        "san_ming_tong_hui": ("book", "三命通会"),
        "di_tian_sui": ("book", "滴天髓"),
        "zi_ping_zhen_quan": ("book", "子平真诠"),
        "qiong_tong_bao_jian": ("book", "穷通宝鉴"),
        "ziwei_doushu_quanshu": ("book", "紫微斗数全书"),
        "ziwei_doushu_mingpan": ("work", "紫微斗数命盘"),
        "ni_haixia_tianji": ("work", "倪海厦天纪"),
        "ni_haixia_renji": ("work", "倪海厦人纪"),
    }

    indexed = {item["key"]: item for item in MODULE.TOPIC_SEEDS}

    for key, (category, title) in expected.items():
        assert key in indexed
        assert indexed[key]["category"] == category
        assert indexed[key]["title_zh_hans"] == title


def test_build_topic_library_includes_book_and_work_topics(monkeypatch):
    monkeypatch.setattr(
        MODULE,
        "fetch_page_summary",
        lambda session, language, title: {"title": title, "summary": f"{language}:{title}", "source_url": f"https://{language}.example/{title}"},
    )
    monkeypatch.setattr(MODULE, "fetch_page_links", lambda session, language, title, limit=MODULE.LINK_FETCH_LIMIT: [])

    selected = [
        next(item for item in MODULE.TOPIC_SEEDS if item["key"] == "yuan_hai_zi_ping"),
        next(item for item in MODULE.TOPIC_SEEDS if item["key"] == "ziwei_doushu_quanshu"),
        next(item for item in MODULE.TOPIC_SEEDS if item["key"] == "ni_haixia_tianji"),
    ]
    records = MODULE.build_topic_library(object(), seeds=selected)

    assert [item["key"] for item in records] == [
        "yuan_hai_zi_ping",
        "ziwei_doushu_quanshu",
        "ni_haixia_tianji",
    ]
    assert [item["category"] for item in records] == ["book", "book", "work"]


def test_build_report_counts_categories():
    progress = MODULE.create_progress_report()
    progress["topics"]["requested"] = 3
    progress["topics"]["completed"] = 3
    report = MODULE.build_report(
        [
            {"key": "bazi", "category": "concept"},
            {"key": "feng_shui", "category": "practice"},
            {"key": "ziwei_doushu", "category": "concept"},
        ],
        progress=progress,
        requested_seed_count=4,
        include_categories=True,
        category_limit=5,
    )

    assert report["total_records"] == 3
    assert report["categories"] == {"concept": 2, "practice": 1}
    assert report["requested_seed_count"] == 4
    assert report["succeeded_topics"] == 3
    assert report["skipped_topics"] == 0
    assert report["completed_stats"]["topics"] == {"requested": 3, "completed": 3, "partial": 0, "skipped": 0}
    assert report["completed_stats"]["categories"] == {"requested": 0, "completed": 0, "failed": 0}
    assert report["include_categories"] is True
    assert report["category_limit"] == 5
    assert report["failed_requests"] == 0
    assert report["failure_summary"] == {"by_stage": {}, "by_language": {}}
    assert report["failures"] == []
    assert report["seed_keys"] == ["bazi", "feng_shui", "ziwei_doushu"]


def test_build_report_includes_failure_summary():
    progress = MODULE.create_progress_report()
    progress["topics"]["requested"] = 2
    progress["topics"]["partial"] = 1
    progress["topics"]["skipped"] = 1
    report = MODULE.build_report(
        [{"key": "bazi", "category": "concept"}],
        [
            {"stage": "summary", "language": "zh", "target": "八字", "message": "429"},
            {"stage": "record", "language": "multi", "target": "bad_seed", "message": "skip"},
        ],
        progress=progress,
    )

    assert report["failed_requests"] == 2
    assert report["skipped_topics"] == 1
    assert report["completed_stats"]["topics"] == {"requested": 2, "completed": 0, "partial": 1, "skipped": 1}
    assert report["failure_summary"] == {
        "by_stage": {"summary": 1, "record": 1},
        "by_language": {"zh": 1, "multi": 1},
    }
    assert report["failures"][0]["target"] == "八字"


def test_build_topic_library_marks_link_failure_as_partial(monkeypatch):
    monkeypatch.setattr(
        MODULE,
        "fetch_page_summary",
        lambda session, language, title: {"title": title, "summary": f"{language}:{title}", "source_url": f"https://{language}.example/{title}"},
    )

    def fake_fetch_page_links(session, language, title, limit=MODULE.LINK_FETCH_LIMIT):
        if language == "zh":
            raise MODULE.requests.RequestException("429")
        return ["ok"]

    monkeypatch.setattr(MODULE, "fetch_page_links", fake_fetch_page_links)

    failures = []
    progress = MODULE.create_progress_report()
    records = MODULE.build_topic_library(object(), seeds=MODULE.TOPIC_SEEDS[:1], failure_log=failures, progress=progress)

    assert len(records) == 1
    assert any(item["stage"] == "links" and item["language"] == "zh" for item in failures)
    assert progress["topics"] == {"requested": 1, "completed": 0, "partial": 1, "skipped": 0}


def test_get_json_with_retry_does_not_retry_non_429_client_error(monkeypatch):
    response = Mock(status_code=404, headers={})
    response.raise_for_status.side_effect = MODULE.requests.HTTPError("404", response=response)
    session = Mock()
    session.get.return_value = response

    sleep_calls = []
    monkeypatch.setattr(MODULE.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    try:
        MODULE.get_json_with_retry(session, "https://example.com/missing")
    except MODULE.requests.HTTPError:
        pass
    else:
        raise AssertionError("预期抛出 HTTPError")

    assert session.get.call_count == 1
    assert sleep_calls == []


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
