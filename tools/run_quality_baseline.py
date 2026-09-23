from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.quality_baseline import (
    default_run_date,
    environment_defaults,
    repository_root,
    run_baseline,
    write_report,
)


def main(argv: list[str] | None = None) -> int:
    defaults = environment_defaults()
    root = repository_root()
    parser = argparse.ArgumentParser(description="Run the reproducible DataPulse quality baseline.")
    parser.add_argument("--provider", choices=("fixture", "openai"), default="fixture")
    parser.add_argument("--fixture-root", type=Path, default=root / "fixtures" / "golden")
    parser.add_argument("--model", default=defaults["model"])
    parser.add_argument("--base-url", default=defaults["base_url"])
    parser.add_argument("--api-key", default=defaults["api_key"])
    parser.add_argument("--date", default=default_run_date())
    parser.add_argument("--output", type=Path)
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    args = parser.parse_args(arguments)
    try:
        report = run_baseline(
            provider_name=args.provider,
            fixture_root=args.fixture_root,
            model=args.model,
            run_date=args.date,
            base_url=args.base_url,
            api_key=args.api_key,
        )
    except ValueError as error:
        parser.error(str(error))
    output = args.output or (
        root / "test-evidence" / "quality-baseline" / f"baseline-{args.date}.json"
    )
    write_report(report, output)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
