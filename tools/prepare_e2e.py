from __future__ import annotations

import base64
import json
import shutil
import socket
import sqlite3
import tempfile
from pathlib import Path
from uuid import uuid4

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
E2E_ROOT = REPOSITORY_ROOT / ".e2e"
FIXTURE_PATH = REPOSITORY_ROOT / "apps" / "web" / "e2e" / "fixtures" / "sales.sql"
TEMP_PREFIX = "datapulse-e2e-"
CONFIG_PREFIX = "config-"


def safe_remove_data_dir(path: Path) -> None:
    resolved = path.resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if resolved.parent != temp_root or not resolved.name.startswith(TEMP_PREFIX):
        raise RuntimeError(f"Refusing to remove unsafe E2E directory: {resolved}")
    shutil.rmtree(resolved, ignore_errors=True)


def cleanup_run(config_path: Path, runtime_root: Path = E2E_ROOT) -> None:
    resolved_root = runtime_root.resolve()
    resolved_config = config_path.resolve()
    if (
        resolved_config.parent != resolved_root
        or not resolved_config.name.startswith(CONFIG_PREFIX)
        or resolved_config.suffix != ".json"
    ):
        raise RuntimeError(f"Refusing to clean unsafe E2E config: {resolved_config}")
    if not resolved_config.exists():
        return
    config = json.loads(resolved_config.read_text(encoding="utf-8"))
    safe_remove_data_dir(Path(config["dataDir"]))
    resolved_config.unlink()
    try:
        resolved_root.rmdir()
    except OSError:
        pass


def reserve_ports() -> tuple[int, int]:
    probes: list[socket.socket] = []
    try:
        for _ in range(2):
            probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            probe.bind(("127.0.0.1", 0))
            probes.append(probe)
        return probes[0].getsockname()[1], probes[1].getsockname()[1]
    finally:
        for probe in probes:
            probe.close()


def prepare(runtime_root: Path = E2E_ROOT) -> Path:
    backend_port, frontend_port = reserve_ports()
    data_dir = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX)).resolve()
    config_path = runtime_root / f"{CONFIG_PREFIX}{uuid4().hex}.json"
    signing_key = base64.urlsafe_b64encode(
        b"e2e-signing-key-material-32-byte"
    ).decode()
    try:
        sources_dir = data_dir / "sources"
        sources_dir.mkdir()
        with sqlite3.connect(sources_dir / "sales.db") as connection:
            connection.executescript(FIXTURE_PATH.read_text(encoding="utf-8"))
        static_dir = data_dir / "static"
        static_dir.mkdir()
        (static_dir / "index.html").write_text(
            "<!doctype html><title>DataPulse E2E player</title>",
            encoding="utf-8",
        )

        runtime_root.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(
                {
                    "backendPort": backend_port,
                    "frontendPort": frontend_port,
                    "dataDir": str(data_dir),
                    "staticDir": str(static_dir),
                    "setupCode": "e2e-setup-code",
                    "signingKey": signing_key,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception:
        safe_remove_data_dir(data_dir)
        raise
    return config_path


if __name__ == "__main__":
    print(prepare())
