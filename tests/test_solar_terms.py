from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATE_PATH = ROOT / "bazichart-engine" / "scripts" / "generate_solar_terms.py"
VALIDATE_PATH = ROOT / "bazichart-engine" / "scripts" / "validate_solar_terms.py"

GENERATE_SPEC = importlib.util.spec_from_file_location("generate_solar_terms", GENERATE_PATH)
GENERATE_MODULE = importlib.util.module_from_spec(GENERATE_SPEC)
assert GENERATE_SPEC.loader is not None
sys.modules[GENERATE_SPEC.name] = GENERATE_MODULE
GENERATE_SPEC.loader.exec_module(GENERATE_MODULE)

VALIDATE_SPEC = importlib.util.spec_from_file_location("validate_solar_terms", VALIDATE_PATH)
VALIDATE_MODULE = importlib.util.module_from_spec(VALIDATE_SPEC)
assert VALIDATE_SPEC.loader is not None
sys.modules[VALIDATE_SPEC.name] = VALIDATE_MODULE
VALIDATE_SPEC.loader.exec_module(VALIDATE_MODULE)


def test_compute_solar_longitude_matches_lichun_threshold():
    dt = VALIDATE_MODULE.parse_iso_datetime("2024-02-04T16:27:00+08:00")
    longitude = GENERATE_MODULE.compute_solar_longitude(dt)
    assert abs(longitude - 315) < 0.01


def test_build_year_terms_returns_24_ordered_terms():
    terms = GENERATE_MODULE.build_year_terms(2024)

    assert len(terms) == 24
    assert terms[0]["name"] == "小寒"
    assert terms[-1]["name"] == "冬至"
    assert terms[2]["datetime"] == "2024-02-04T16:27:00+08:00"


def test_engine_comparison_stays_within_one_minute():
    dataset = {"2024": GENERATE_MODULE.build_year_terms(2024)}
    report = VALIDATE_MODULE.compare_with_engine(dataset)

    assert report["count"] == 24
    assert report["max_delta_minutes"] <= 1.0


def test_write_report_persists_interval_check_result(tmp_path):
    dataset = GENERATE_MODULE.build_dataset(start_year=2024, end_year=2024)
    output_path = tmp_path / "solar_terms.json"
    report_path = tmp_path / "solar_terms_report.json"

    GENERATE_MODULE.write_dataset(dataset, output_path)
    loaded = json.loads(output_path.read_text(encoding="utf-8"))
    report = {
        "interval_report": VALIDATE_MODULE.validate_term_intervals(loaded),
        "engine_comparison": VALIDATE_MODULE.compare_with_engine(loaded),
    }
    VALIDATE_MODULE.write_report(report, report_path)

    assert report["interval_report"]["violations"] == []
    assert report["engine_comparison"]["max_delta_minutes"] <= 1.0
    assert report_path.exists()
