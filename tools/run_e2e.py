from __future__ import annotations

import os
import subprocess

from tools.prepare_e2e import REPOSITORY_ROOT, cleanup_run, prepare


def main() -> int:
    config_path = prepare()
    environment = {
        **os.environ,
        "DATAPULSE_E2E_CONFIG": str(config_path),
    }
    try:
        completed = subprocess.run(
            [
                "pnpm",
                "--filter",
                "@datapulse/web",
                "exec",
                "playwright",
                "test",
                "--config",
                "playwright.config.ts",
            ],
            cwd=REPOSITORY_ROOT,
            env=environment,
            check=False,
        )
        return completed.returncode
    finally:
        cleanup_run(config_path)


if __name__ == "__main__":
    raise SystemExit(main())
