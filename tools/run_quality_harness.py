from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.quality_harness import (
    build_comparison,
    build_failure_samples,
    build_trend,
    read_report,
    write_dashboard,
    write_json,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build model comparison, trend, dashboard and regression fixtures."
    )
    parser.add_argument("--report", type=Path, action="append", required=True)
    parser.add_argument("--comparison-output", type=Path, required=True)
    parser.add_argument("--trend-output", type=Path, required=True)
    parser.add_argument("--dashboard-output", type=Path, required=True)
    parser.add_argument("--failures-output", type=Path, required=True)
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    args = parser.parse_args(arguments)
    if len(args.report) < 2:
        parser.error("at least two --report values are required")
    try:
        reports = [read_report(path) for path in args.report]
        comparison = build_comparison(reports)
        trend = build_trend(reports)
        failures = build_failure_samples(reports)
    except ValueError as error:
        parser.error(str(error))
    write_json(comparison, args.comparison_output)
    write_json(trend, args.trend_output)
    write_dashboard(trend, args.dashboard_output)
    write_json(failures, args.failures_output)
    print(json.dumps({"reports": len(reports), "failures": len(failures["samples"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
