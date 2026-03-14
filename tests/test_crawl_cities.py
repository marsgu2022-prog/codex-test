from __future__ import annotations

import importlib.util
import json
import sys
import textwrap
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent.parent / "bazichart-engine" / "scripts" / "crawl_cities.py"
SPEC = importlib.util.spec_from_file_location("crawl_cities", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")


def test_generate_outputs_with_local_sample_data(tmp_path):
    source_dir = tmp_path / "downloads"
    output_dir = tmp_path / "data"

    write_file(
        source_dir / "cities5000.txt",
        """
        1796236	Hangzhou	Hangzhou	杭州,杭州市	30.2936	120.1614	P	PPLA2	CN		02				7642147	10	8	Asia/Shanghai	2024-01-01
        1816670	Hong Kong	Hong Kong	香港	22.2783	114.1747	P	PPLC	HK						7482500	24	44	Asia/Hong_Kong	2024-01-01
        1668341	Taipei	Taipei	臺北,台北	25.0478	121.5319	P	PPLC	TW						2646204	20	9	Asia/Taipei	2024-01-01
        5128581	New York City	New York City	纽约	40.7143	-74.0060	P	PPLA	US		NY				8804190	10	33	America/New_York	2024-01-01
        """,
    )
    write_file(
        source_dir / "admin1CodesASCII.txt",
        """
        CN.02	Zhejiang	Zhejiang	1784766
        US.NY	New York	New York	5128638
        """,
    )
    write_file(
        source_dir / "countryInfo.txt",
        """
        #ISO	ISO3	ISO-Numeric	fips	Country	Capital	Area(in sq km)	Population	Continent	tld	CurrencyCode	CurrencyName	Phone	Postal Code Format	Postal Code Regex	Languages	geonameid	neighbours	EquivalentFipsCode
        CN	CHN	156	CH	China	Beijing	0	0	AS	.cn	CNY	Yuan	86				1814991		
        HK	HKG	344	HK	Hong Kong	Hong Kong	0	0	AS	.hk	HKD	Dollar	852				1819730		
        TW	TWN	158	TW	Taipei	Taipei	0	0	AS	.tw	TWD	Dollar	886				1668284		
        US	USA	840	US	United States	Washington	0	0	NA	.us	USD	Dollar	1				6252001		
        """,
    )
    write_file(
        source_dir / "alternateNamesV2.txt",
        """
        1	1796236	zh	杭州	1	0	0	0		
        2	1816670	zh-hant	香港	1	0	0	0		
        3	1668341	zh-hant	臺北	1	0	0	0		
        4	5128581	zh	纽约	1	0	0	0		
        5	1814991	zh	中国	1	0	0	0		
        6	6252001	zh	美国	1	0	0	0		
        7	1784766	zh	浙江省	1	0	0	0		
        8	5128638	zh	纽约州	1	0	0	0		
        """,
    )

    summary = MODULE.generate_outputs(source_dir, output_dir)

    china = json.loads((output_dir / "cities-china.json").read_text(encoding="utf-8"))
    asia = json.loads((output_dir / "cities-asia.json").read_text(encoding="utf-8"))
    americas = json.loads((output_dir / "cities-americas.json").read_text(encoding="utf-8"))
    countries = json.loads((output_dir / "countries.json").read_text(encoding="utf-8"))
    admin1 = json.loads((output_dir / "admin1.json").read_text(encoding="utf-8"))

    assert summary["total_countries"] == 2
    assert summary["total_cities"] == 4
    assert summary["china_cities"] == 3
    assert summary["chinese_name_ratio"] == 1.0

    assert [city["nameEn"] for city in china] == ["Hangzhou", "Hong Kong", "Taipei"]
    assert china[0]["countryZh"] == "中国"
    assert china[0]["admin1Zh"] == "浙江省"
    assert china[1]["admin1Zh"] == "香港特别行政区"
    assert china[2]["admin1Zh"] == "台湾省"

    assert asia == []
    assert americas[0]["country"] == "US"
    assert americas[0]["admin1Zh"] == "纽约州"

    assert countries == [
        {"code": "CN", "nameZh": "中国", "nameEn": "China"},
        {"code": "US", "nameZh": "美国", "nameEn": "United States"},
    ]
    assert {"country": "CN", "code": "HK", "nameZh": "香港特别行政区", "nameEn": "Hong Kong"} in admin1
