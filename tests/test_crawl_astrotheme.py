from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "scripts" / "crawl_astrotheme.py"
SPEC = spec_from_file_location("crawl_astrotheme", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["crawl_astrotheme"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


SAMPLE_RESULTS = """
<a href="https://www.astrotheme.com/astrology/Shinzo_Abe">Shinzo Abe Display his detailed birth chart</a>
<a href="https://www.astrotheme.com/celestar/horoscope_celebrity_search_by_filters.php?page=2">Next</a>
"""

SAMPLE_DETAIL = """
<html>
<head><title>Astrological chart of Brad Pitt, born 1963/12/18</title></head>
<body>
<h1>Brad Pitt: Astrological Article and Chart</h1>
<div>Brad Pitt Birth data and astrological dominants</div>
<div>Born: Wednesday, December 18 , 1963, 6:31 AM In: Shawnee (OK) (United States)</div>
<div>A Reliability Source : From memory or autobiography Contributor : Lois Rodden</div>
<div>Biography of Brad Pitt (excerpt) William Bradley "Brad" Pitt is an American actor and producer. He won an Academy Award in 2020. Pitt first gained recognition in 1991. </div>
</body>
</html>
"""


def test_parse_result_page_extracts_links_and_next():
    urls, next_url = MODULE.parse_result_page(SAMPLE_RESULTS)
    assert urls == ["https://www.astrotheme.com/astrology/Shinzo_Abe"]
    assert next_url.endswith("page=2")


def test_parse_person_extracts_core_fields():
    person = MODULE.parse_person(SAMPLE_DETAIL, "https://www.astrotheme.com/astrology/Brad_Pitt", "entertainment")
    assert person is not None
    assert person["name_en"] == "Brad Pitt"
    assert person["birth_date"] == "1963-12-18"
    assert person["birth_time"] == "06:31"
    assert person["birth_country"] == "United States"
    assert person["occupation"] == ["演员", "企业家"]
    assert person["notable_events"][0]["year"] == 2020


def test_crawl_can_resume_from_saved_state(monkeypatch):
    responses = {
        "https://resume.example/page2": """
<a href="https://www.astrotheme.com/astrology/Resume_Person">Resume Person Display his detailed birth chart</a>
<a href="https://www.astrotheme.com/celestar/horoscope_celebrity_search_by_filters.php?page=3">Next</a>
""",
        "https://www.astrotheme.com/astrology/Resume_Person": SAMPLE_DETAIL.replace("Brad Pitt", "Resume Person"),
    }

    def fake_fetch(session, url, *, data=None, request_interval):
        if data is not None:
            raise AssertionError("续抓时不应重新发起分类搜索")
        return responses[url]

    monkeypatch.setattr(MODULE, "fetch", fake_fetch)
    people, errors, runtime_state = MODULE.crawl(
        session=None,
        max_pages_per_category=1,
        max_records=1,
        request_interval=0,
        state={"category_index": 0, "next_url": "https://resume.example/page2"},
    )

    assert not errors
    assert [item["name_en"] for item in people] == ["Resume Person"]
    assert runtime_state["category_index"] == 0
    assert runtime_state["next_url"].endswith("page=3")


def test_load_state_migrates_completed_legacy_layout(tmp_path):
    state_path = tmp_path / "astrotheme_state.json"
    state_path.write_text(
        '{"category_index": 5, "next_url": null, "updated_at": "2026-03-21T22:56:29", "layout_version": 1}',
        encoding="utf-8",
    )

    state = MODULE.load_state(state_path)

    assert state["category_index"] == MODULE.FIRST_NEW_CATEGORY_INDEX
    assert state["layout_version"] == MODULE.STATE_LAYOUT_VERSION


def test_load_state_migrates_legacy_intermediate_layout(tmp_path):
    state_path = tmp_path / "astrotheme_state.json"
    state_path.write_text(
        '{"category_index": 2, "next_url": "https://legacy.example/page3", "updated_at": "2026-03-21T20:00:00", "layout_version": 1}',
        encoding="utf-8",
    )

    state = MODULE.load_state(state_path)

    assert state["category_index"] == MODULE.LEGACY_CATEGORY_INDEX_MAP[2]
    assert state["next_url"] == "https://legacy.example/page3"
    assert state["layout_version"] == MODULE.STATE_LAYOUT_VERSION


def test_crawl_skips_existing_people_by_name_and_birth_date(monkeypatch):
    responses = {
        MODULE.SEARCH_URL: """
<a href="https://www.astrotheme.com/astrology/Brad_Pitt">Brad Pitt Display his detailed birth chart</a>
""",
        "https://www.astrotheme.com/astrology/Brad_Pitt": SAMPLE_DETAIL,
    }

    def fake_fetch(session, url, *, data=None, request_interval):
        if data is not None:
            return responses[MODULE.SEARCH_URL]
        return responses[url]

    monkeypatch.setattr(MODULE, "fetch", fake_fetch)
    people, errors, runtime_state = MODULE.crawl(
        session=None,
        max_pages_per_category=1,
        max_records=5,
        request_interval=0,
        state={"category_index": 0, "next_url": None, "layout_version": MODULE.STATE_LAYOUT_VERSION},
        existing_keys={("Brad Pitt", "1963-12-18")},
    )

    assert not errors
    assert people == []
    assert runtime_state["category_index"] == len(MODULE.CATEGORY_PAYLOADS)


def test_person_identity_normalizes_spaces_and_case():
    item = {"name_en": " Brad   Pitt ", "birth_date": "1963-12-18"}

    assert MODULE.person_identity(item) == ("bradpitt", "1963-12-18")


def test_crawl_logs_parse_errors_for_structure_changes(monkeypatch, tmp_path):
    responses = {
        MODULE.SEARCH_URL: """
<a href="https://www.astrotheme.com/astrology/Broken_Person">Broken Person Display his detailed birth chart</a>
""",
        "https://www.astrotheme.com/astrology/Broken_Person": """
<html>
<head><title>Astrological chart of Broken Person, born 1963/12/18</title></head>
<body>
<div>Broken Person Birth data and astrological dominants</div>
<div>Born: Wednesday, December 18 , 1963 In: Shawnee (OK) (United States)</div>
</body>
</html>
""",
    }

    def fake_fetch(session, url, *, data=None, request_interval):
        if data is not None:
            return responses[MODULE.SEARCH_URL]
        return responses[url]

    monkeypatch.setattr(MODULE, "fetch", fake_fetch)
    monkeypatch.setattr(MODULE, "PARSE_ERROR_LOG", tmp_path / "parse_errors.log")

    people, errors, runtime_state = MODULE.crawl(
        session=None,
        max_pages_per_category=1,
        max_records=5,
        request_interval=0,
        state={"category_index": 0, "next_url": None, "layout_version": MODULE.STATE_LAYOUT_VERSION},
    )

    assert not errors
    assert people == []
    assert runtime_state["category_index"] == len(MODULE.CATEGORY_PAYLOADS)
    log_text = (tmp_path / "parse_errors.log").read_text(encoding="utf-8")
    assert "missing_birth_time" in log_text
    assert "Broken_Person" in log_text


def test_main_syncs_sqlite_snapshot(monkeypatch, tmp_path):
    args = type(
        "Args",
        (),
        {
            "max_pages_per_category": 1,
            "max_records": 1,
            "request_interval": 0,
            "output": tmp_path / "astrotheme.json",
            "errors_output": tmp_path / "errors.json",
            "state_output": tmp_path / "state.json",
            "sqlite_db": tmp_path / "people.db",
            "sqlite_export_unified": tmp_path / "unified.json",
            "sqlite_report_output": tmp_path / "report.json",
        },
    )()
    synced = {}

    monkeypatch.setattr(MODULE, "parse_args", lambda: args)
    monkeypatch.setattr(MODULE, "make_session", lambda: object())
    monkeypatch.setattr(MODULE, "load_json_list", lambda _path: [])
    monkeypatch.setattr(MODULE, "load_state", lambda _path: {})
    monkeypatch.setattr(
        MODULE,
        "crawl",
        lambda *_args, **_kwargs: (
            [{"name_en": "Gamma", "birth_date": "1999-01-01", "birth_time": "08:00", "source_urls": ["g"], "occupation": [], "notable_events": [], "data_quality_score": 0.8}],
            [],
            {"category_index": 1, "next_url": None},
        ),
    )
    monkeypatch.setattr(MODULE, "write_json", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(MODULE, "write_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        MODULE,
        "sync_source_snapshots",
        lambda db_path, source_records, **_kwargs: synced.update({"db": db_path, "sources": source_records}),
    )

    MODULE.main()

    assert synced["db"] == args.sqlite_db
    assert set(synced["sources"]) == {"astrotheme"}
