"""Entry point: datapulse-operations backup create|verify|inspect|restore."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from datapulse.operations.backup import (
    BackupError,
    create_backup,
    inspect_backup,
    restore_backup,
    verify_backup,
)
from datapulse.settings import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DataPulse offline maintenance operations")
    groups = parser.add_subparsers(dest="operation", required=True)
    backup = groups.add_parser("backup", help="Create, verify, inspect or restore a backup")
    actions = backup.add_subparsers(dest="action", required=True)
    for name in ("create", "verify", "inspect", "restore"):
        action = actions.add_parser(name)
        action.add_argument("--archive", type=Path, required=True)
        if name in ("create", "restore"):
            action.add_argument(
                "--maintenance",
                action="store_true",
                help="Confirm API, workers and external file writers are stopped",
            )
        if name == "create":
            action.add_argument(
                "--include-external-paths",
                action="store_true",
                help="Include configured metadata/assets/sources outside DATA_DIR",
            )
        if name == "restore":
            action.add_argument(
                "--target",
                type=Path,
                required=True,
                help="Empty or nonexistent data directory; never overwritten",
            )
    args = parser.parse_args(argv)
    try:
        settings = Settings()
        if args.action == "create":
            manifest = create_backup(
                settings,
                args.archive,
                maintenance=args.maintenance,
                include_external_paths=args.include_external_paths,
            )
        elif args.action == "restore":
            manifest = restore_backup(
                args.archive,
                args.target,
                maintenance=args.maintenance,
                master_key=settings.master_key,
                app_version=settings.app_version,
            )
        else:
            operation = inspect_backup if args.action == "inspect" else verify_backup
            manifest = operation(args.archive, app_version=settings.app_version)
    except ValidationError:
        # Settings validation can include input values, including deployment secrets.
        print(
            "BACKUP_FAILED: Invalid deployment settings; check configured value types.",
            file=sys.stderr,
        )
        return 1
    except BackupError as error:
        print(f"BACKUP_FAILED: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {"status": "ok", "action": args.action, "manifest": manifest.model_dump(mode="json")},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
