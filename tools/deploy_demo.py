from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path

import httpx

from datapulse.operations.delivery import (
    REPOSITORY_ROOT,
    authenticate_demo,
    build_compose_command,
    seed_demo,
    write_demo_environment,
)


SETUP_CODE_PATTERN = re.compile(r"DataPulse one-time setup code:\s+(\S+)")


def _compose_prefix(environment_path: Path, project_name: str) -> list[str]:
    return [
        "docker",
        "compose",
        "--env-file",
        str(environment_path),
        "--project-name",
        project_name,
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy DataPulse and load repository demo data.")
    parser.add_argument("--env-file", type=Path, default=REPOSITORY_ROOT / ".env.demo")
    parser.add_argument("--project-name", default="datapulse-demo")
    parser.add_argument("--port", type=int, default=8000)
    arguments = parser.parse_args()

    environment_path = arguments.env_file.resolve()
    values = write_demo_environment(environment_path, http_port=arguments.port)
    subprocess.run(
        build_compose_command(environment_path, arguments.project_name),
        cwd=REPOSITORY_ROOT,
        check=True,
    )
    port = int(values["DATAPULSE_HTTP_PORT"])
    origin = f"http://127.0.0.1:{port}"
    prefix = _compose_prefix(environment_path, arguments.project_name)
    setup_code: str | None = None
    with httpx.Client(base_url=origin, timeout=30) as client:
        for _ in range(30):
            try:
                status = client.get("/api/auth/status")
                if status.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("The DataPulse container did not become ready.")
        if status.json().get("initialized") is False:
            logs = subprocess.run(
                [*prefix, "logs", "--no-color", "datapulse"],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            match = SETUP_CODE_PATTERN.search(logs)
            setup_code = match.group(1) if match else None
        authenticate_demo(
            client,
            origin=origin,
            username=values["DATAPULSE_DEMO_ADMIN_USERNAME"],
            password=values["DATAPULSE_DEMO_ADMIN_PASSWORD"],
            setup_code=setup_code,
        )
        identifiers = seed_demo(client, origin=origin)

    print(
        json.dumps(
            {
                "status": "ok",
                "studio_url": f"{origin}/studio",
                "screen_id": identifiers["screen_id"],
                "environment_file": str(environment_path),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
