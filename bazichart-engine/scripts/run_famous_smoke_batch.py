#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def output_suffix_for_mode(mode: str) -> str:
    return "_smoke" if mode == "smoke" else ""


def artifact_paths(data_dir: Path, mode: str) -> dict[str, Path]:
    suffix = output_suffix_for_mode(mode)
    return {
        "people": data_dir / f"famous_people{suffix}.json",
        "index": data_dir / f"day_pillar_index{suffix}.json",
        "report": data_dir / f"famous_people_report{suffix}.json",
    }


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def archive_outputs(data_dir: Path, batch_dir: Path, mode: str, run_index: int) -> dict[str, str]:
    batch_dir.mkdir(parents=True, exist_ok=True)
    run_dir = batch_dir / f"run_{run_index:02d}"
    run_dir.mkdir(parents=True, exist_ok=True)

    archived: dict[str, str] = {}
    for name, source in artifact_paths(data_dir, mode).items():
        if not source.exists():
            continue
        target = run_dir / source.name
        shutil.copy2(source, target)
        archived[name] = str(target)
    return archived


def run_once(mode: str, run_index: int, batch_dir: Path, python_executable: str) -> dict[str, Any]:
    command = [python_executable, "bazichart-engine/scripts/crawl_famous_people.py", "--mode", mode]
    start = time.time()
    completed = subprocess.run(
        command,
        cwd=BASE_DIR.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    duration_seconds = round(time.time() - start, 2)
    run_dir = batch_dir / f"run_{run_index:02d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "stdout.log").write_text(completed.stdout, encoding="utf-8")
    (run_dir / "stderr.log").write_text(completed.stderr, encoding="utf-8")

    report_path = artifact_paths(DATA_DIR, mode)["report"]
    archived = archive_outputs(DATA_DIR, batch_dir, mode, run_index)
    total_people = None
    if report_path.exists():
        total_people = read_json(report_path).get("total_people")

    return {
        "run": run_index,
        "mode": mode,
        "returncode": completed.returncode,
        "duration_seconds": duration_seconds,
        "total_people": total_people,
        "archived_files": archived,
    }


def build_summary(mode: str, runs: list[dict[str, Any]]) -> dict[str, Any]:
    totals = [item["total_people"] for item in runs if isinstance(item.get("total_people"), int)]
    return {
        "mode": mode,
        "runs": len(runs),
        "success_runs": sum(1 for item in runs if item["returncode"] == 0),
        "failed_runs": sum(1 for item in runs if item["returncode"] != 0),
        "max_total_people": max(totals) if totals else None,
        "min_total_people": min(totals) if totals else None,
        "results": runs,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="批量运行名人抓取 smoke 模式并归档结果")
    parser.add_argument("--runs", type=int, default=3, help="连续运行次数")
    parser.add_argument("--mode", choices=["smoke", "full"], default="smoke", help="抓取模式")
    parser.add_argument("--output-dir", type=Path, default=DATA_DIR / "famous_people_batches", help="批跑结果目录")
    parser.add_argument("--python-executable", default=sys.executable, help="运行抓取脚本的 Python")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.runs <= 0:
        print("runs 必须大于 0", file=sys.stderr)
        return 2

    batch_dir = args.output_dir / f"{args.mode}_{time.strftime('%Y%m%d-%H%M%S')}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for run_index in range(1, args.runs + 1):
        print(f"开始第 {run_index}/{args.runs} 轮，模式 {args.mode}", flush=True)
        result = run_once(args.mode, run_index, batch_dir, args.python_executable)
        results.append(result)
        print(
            f"第 {run_index} 轮完成: returncode={result['returncode']} total_people={result['total_people']}",
            flush=True,
        )

    summary = build_summary(args.mode, results)
    summary_path = batch_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"汇总文件: {summary_path}", flush=True)
    print(f"成功轮次: {summary['success_runs']}/{summary['runs']}", flush=True)
    print(f"人数区间: {summary['min_total_people']} - {summary['max_total_people']}", flush=True)
    return 0 if summary["failed_runs"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
