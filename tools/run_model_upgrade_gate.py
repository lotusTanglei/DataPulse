from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.quality_harness import evaluate_upgrade, read_report, write_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Block a default model upgrade when any controlled metric regresses."
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    args = parser.parse_args(arguments)
    decision = evaluate_upgrade(read_report(args.baseline), read_report(args.candidate))
    write_json(decision, args.output)
    print(json.dumps(decision, ensure_ascii=False, sort_keys=True))
    return 0 if decision["allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
