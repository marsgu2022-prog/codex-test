from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "scripts" / "run_famous_smoke_batch.py"
SPEC = importlib.util.spec_from_file_location("run_famous_smoke_batch", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_output_suffix_for_mode():
    assert MODULE.output_suffix_for_mode("smoke") == "_smoke"
    assert MODULE.output_suffix_for_mode("full") == ""


def test_archive_outputs_copies_artifacts(tmp_path):
    data_dir = tmp_path / "data"
    batch_dir = tmp_path / "batch"
    data_dir.mkdir()

    for path in MODULE.artifact_paths(data_dir, "smoke").values():
        path.write_text("{}", encoding="utf-8")

    archived = MODULE.archive_outputs(data_dir, batch_dir, "smoke", 2)

    assert set(archived) == {"people", "index", "report"}
    assert (batch_dir / "run_02" / "famous_people_smoke.json").exists()
    assert (batch_dir / "run_02" / "day_pillar_index_smoke.json").exists()
    assert (batch_dir / "run_02" / "famous_people_report_smoke.json").exists()


def test_build_summary_collects_run_statistics():
    summary = MODULE.build_summary(
        "smoke",
        [
            {"run": 1, "returncode": 0, "total_people": 23},
            {"run": 2, "returncode": 1, "total_people": 0},
            {"run": 3, "returncode": 0, "total_people": 25},
        ],
    )

    assert summary["mode"] == "smoke"
    assert summary["runs"] == 3
    assert summary["success_runs"] == 2
    assert summary["failed_runs"] == 1
    assert summary["min_total_people"] == 0
    assert summary["max_total_people"] == 25
