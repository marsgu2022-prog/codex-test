from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from unittest.mock import Mock

import requests


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "scripts" / "crawl_astro_databank.py"
SPEC = spec_from_file_location("crawl_astro_databank", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["crawl_astro_databank"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


SAMPLE_ALLPAGES = """
<div class="mw-allpages-nav"><a href="/wiki/astro-databank/index.php?title=Special:AllPages&amp;from=Ab">Next page (Ab)</a></div>
<div class="mw-allpages-body">
  <ul>
    <li><a href="/astro-databank/Aaliyah">Aaliyah</a></li>
    <li><a href="/astro-databank/Abagnale,_Frank">Abagnale, Frank</a></li>
  </ul>
</div>
"""

SAMPLE_RAW = """
{{ASTRODATABANK_dma
|Name=Jobs, Steve
|sflname=Steve Jobs
|sbdate=1955/02/24
|sbtime=19:15
|Place=San Francisco
|BirthCountry=California
|sctr=CA (US)
|sroddenrating=AA
|Gender=M
}}
==Categories==
{{ASTRODATABANK_cat
|CodeID=1
|scat=Vocation : Business : Executive
|CategoryNotes=
}}
{{ASTRODATABANK_cat
|CodeID=2
|scat=Vocation : Science : Computer science
|CategoryNotes=
}}
"""

SAMPLE_HTML = """
<div class="mw-parser-output">
  <h2>Biography</h2>
  <p>American business executive and Apple co-founder who shaped personal technology.</p>
</div>
"""


def test_parse_allpages_extracts_links_and_next_page():
    links, next_url = MODULE.parse_allpages(SAMPLE_ALLPAGES)

    assert len(links) == 2
    assert links[0]["title"] == "Aaliyah"
    assert next_url.endswith("from=Ab")


def test_parse_person_builds_expected_record():
    country_map = {"US": "United States"}

    person = MODULE.parse_person(
        raw_text=SAMPLE_RAW,
        html_text=SAMPLE_HTML,
        source_url="https://www.astro.com/wiki/astro-databank/index.php?title=Jobs,_Steve",
        country_map=country_map,
    )

    assert person is not None
    assert person["name_en"] == "Steve Jobs"
    assert person["birth_date"] == "1955-02-24"
    assert person["birth_time"] == "19:15"
    assert person["birth_country"] == "United States"
    assert person["birth_time_source"] == "astrodatabank_AA"
    assert person["occupation"] == ["企业家", "科技", "科学家"]


def test_is_target_page_filters_accident_pages():
    assert MODULE.is_target_page({"title": "2023 Plane crash Nepal", "href": "x"}) is False
    assert MODULE.is_target_page({"title": "Jobs, Steve", "href": "x"}) is True


def test_fetch_text_retries_until_success():
    response = Mock()
    response.raise_for_status.return_value = None
    response.text = "ok"

    session = Mock()
    session.get.side_effect = [
        requests.exceptions.ConnectTimeout("timeout"),
        response,
    ]

    original_sleep = MODULE.time.sleep
    MODULE.time.sleep = lambda *_args, **_kwargs: None
    try:
        text = MODULE.fetch_text(session, "https://example.com", 0)
    finally:
        MODULE.time.sleep = original_sleep

    assert text == "ok"
    assert session.get.call_count == 2


def test_load_state_backfills_new_resume_fields(tmp_path):
    state_path = tmp_path / "astro_state.json"
    state_path.write_text('{"last_next_url":"https://example.com/page","last_title":"Jobs,_Steve"}', encoding="utf-8")

    state = MODULE.load_state(state_path)

    assert state["current_url"] is None
    assert state["last_next_url"] == "https://example.com/page"
    assert state["last_title"] == "Jobs,_Steve"
    assert state["last_processed_index"] == 0


def test_crawl_resumes_from_saved_link_index():
    session = Mock()
    country_map = {"US": "United States"}
    detail_response = f"{SAMPLE_RAW}\n|sflname=Resume Person\n"
    session.get.side_effect = [
        Mock(text=SAMPLE_ALLPAGES, raise_for_status=Mock()),
        Mock(text=detail_response, raise_for_status=Mock()),
        Mock(text=SAMPLE_HTML, raise_for_status=Mock()),
    ]

    original_sleep = MODULE.time.sleep
    MODULE.time.sleep = lambda *_args, **_kwargs: None
    try:
        high_confidence, medium_confidence, errors, runtime_state = MODULE.crawl(
            session=session,
            start_url="https://example.com/page",
            max_pages=1,
            max_records=5,
            country_map=country_map,
            request_interval=0,
            state={
                "current_url": "https://example.com/page",
                "last_next_url": "https://example.com/page",
                "last_title": "Aaliyah",
                "last_processed_index": 1,
                "updated_at": None,
            },
        )
    finally:
        MODULE.time.sleep = original_sleep

    assert len(high_confidence) == 1
    assert medium_confidence == []
    assert errors == []
    assert high_confidence[0]["name_en"] == "Resume Person"
    assert runtime_state["current_url"].endswith("from=Ab")
    assert runtime_state["last_processed_index"] == 0
    assert session.get.call_count == 3


def test_main_syncs_sqlite_snapshot(monkeypatch, tmp_path):
    args = type(
        "Args",
        (),
        {
            "start_url": MODULE.ALL_PAGES_URL,
            "start_from": None,
            "max_pages": 1,
            "max_records": 1,
            "request_interval": 0,
            "output_a": tmp_path / "astro_a.json",
            "output_b": tmp_path / "astro_b.json",
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
    monkeypatch.setattr(MODULE, "load_state", lambda _path: {})
    monkeypatch.setattr(MODULE, "load_json_list", lambda _path: [])
    monkeypatch.setattr(
        MODULE,
        "crawl",
        lambda **_kwargs: (
            [{"name_en": "Alpha", "birth_date": "2000-01-01", "birth_time": "10:00", "source_urls": ["a"], "occupation": [], "notable_events": [], "data_quality_score": 0.9, "rodden_rating": "AA"}],
            [{"name_en": "Beta", "birth_date": "2000-01-02", "birth_time": "11:00", "source_urls": ["b"], "occupation": [], "notable_events": [], "data_quality_score": 0.7, "rodden_rating": "B"}],
            [],
            {"last_next_url": "next"},
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
    assert set(synced["sources"]) == {"astrodatabank_a", "astrodatabank_b"}
