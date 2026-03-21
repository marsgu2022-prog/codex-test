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
