from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


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
