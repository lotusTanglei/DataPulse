from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from datapulse.operations.delivery import run_clean_delivery_rehearsal


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the DataPulse delivery demo end to end.")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()

    with TemporaryDirectory(prefix="datapulse-delivery-") as temporary_dir:
        report = run_clean_delivery_rehearsal(Path(temporary_dir))
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
