"""Isolated Docker startup, 50-client query and offline recovery rehearsal.

Uses random fixture credentials, a disposable volume, and 2 CPU/4 GiB limits.
Only measurements and structured request logs are retained. This is a local
functional/capacity preflight; it does not measure browser first paint or soak.
"""

import argparse
import asyncio
import base64
import io
import json
import re
import secrets
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from PIL import Image


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=180)
    if result.returncode:
        # Docker arguments/output may contain ephemeral authorization data.
        raise RuntimeError(f"Docker {args[0]} failed (exit {result.returncode})")
    return result.stdout


def require(response: httpx.Response, expected: int = 200):
    if response.status_code != expected:
        code = "HTTP_ERROR"
        try:
            code = response.json().get("error", {}).get("code", code)
        except ValueError:
            pass
        raise RuntimeError(f"HTTP {response.status_code}; expected {expected}; code {code}")
    return response.json() if response.content else None


def write_env(path: Path, settings: dict[str, str]) -> None:
    path.write_text("".join(f"{name}={value}\n" for name, value in settings.items()))
    path.chmod(0o600)


def retain_request_logs(name: str, destination: Path) -> None:
    try:
        result = subprocess.run(
            ["docker", "logs", name], capture_output=True, text=True, timeout=15
        )
    except (OSError, subprocess.SubprocessError):
        return
    records = []
    for line in (result.stdout + result.stderr).splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict) and record.get("event") == "http_request":
            records.append(
                {
                    key: record.get(key)
                    for key in (
                        "event",
                        "time",
                        "request_id",
                        "method",
                        "route",
                        "status",
                        "duration_ms",
                    )
                }
            )
    destination.write_text("".join(json.dumps(record) + "\n" for record in records))


def start(image: str, name: str, volume: str, env_file: Path) -> str:
    docker(
        "run",
        "-d",
        "--name",
        name,
        "--cpus",
        "2",
        "--memory",
        "4g",
        "--pids-limit",
        "256",
        "--env-file",
        str(env_file),
        "-v",
        f"{volume}:/data",
        "-p",
        "127.0.0.1::8000",
        image,
    )
    port = docker("port", name, "8000/tcp").strip().rsplit(":", 1)[1]
    origin = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 60
    with httpx.Client(timeout=2) as client:
        while time.monotonic() < deadline:
            try:
                if client.get(origin + "/api/health").status_code == 200:
                    return origin
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
    raise RuntimeError("Container did not become healthy within 60 seconds")


def headers(client: httpx.Client, origin: str) -> dict[str, str]:
    return {"Origin": origin, "X-CSRF-Token": client.cookies["datapulse_csrf"]}


def login(client: httpx.Client, origin: str, password: str) -> None:
    require(
        client.post(
            "/api/auth/login",
            headers={"Origin": origin},
            json={"username": "admin", "password": password},
        ),
        204,
    )


def seed(client: httpx.Client, origin: str) -> tuple[str, str, bytes]:
    mutation = headers(client, origin)
    file = require(
        client.post(
            "/api/admin/files",
            headers=mutation,
            files={"file": ("sales.csv", b"region,amount\nnorth,10\nsouth,20\n", "text/csv")},
        ),
        201,
    )
    dataset = require(
        client.post(
            "/api/admin/datasets/files",
            headers=mutation,
            json={"name": "Local capacity", "file_asset_id": file["id"]},
        ),
        201,
    )
    stream = io.BytesIO()
    Image.new("RGB", (8, 8), "blue").save(stream, format="PNG")
    media = stream.getvalue()
    asset = require(
        client.post(
            "/api/admin/assets",
            headers=mutation,
            files={"file": ("poster.png", media, "image/png")},
        ),
        201,
    )
    document = {
        "canvas": {"width": 1920, "height": 1080},
        "components": [
            {
                "id": "chart",
                "type": "builtin.bar",
                "frame": {"x": 0, "y": 0, "width": 900, "height": 700},
                "data_binding": {
                    "chart_spec": {
                        "dataset_id": dataset["id"],
                        "dimensions": ["region"],
                        "measures": [{"field": "amount", "aggregation": "sum"}],
                        "visual": {"type": "bar"},
                    }
                },
            },
            {
                "id": "image",
                "type": "builtin.image",
                "frame": {"x": 1000, "y": 0, "width": 100, "height": 100},
                "props": {"asset_id": asset["id"]},
            },
        ],
    }
    screen = require(
        client.post(
            "/api/admin/screens",
            headers=mutation,
            json={"name": "Local capacity", "draft_document": document},
        ),
        201,
    )
    require(
        client.post(
            f"/api/admin/screens/{screen['id']}/publish",
            headers=mutation,
            json={"expected_revision": 0},
        )
    )
    return screen["id"], asset["id"], media


def assert_rows(payload: dict) -> None:
    assert sorted(payload["rows"]) == [["north", 10], ["south", 20]]


async def capacity(origin: str, screen_id: str, key: str) -> dict:
    elapsed: list[float] = []
    ready = asyncio.Event()
    connected = 0

    async def viewer():
        nonlocal connected
        async with httpx.AsyncClient(base_url=origin, timeout=15) as client:
            require(
                await client.post(f"/api/player/screens/{screen_id}/session", json={"key": key}),
                204,
            )
            connected += 1
            if connected == 50:
                ready.set()
            await asyncio.wait_for(ready.wait(), timeout=30)
            for _ in range(5):
                started = time.monotonic()
                assert_rows(
                    require(
                        await client.post(
                            f"/api/player/screens/{screen_id}/query", json={"component_id": "chart"}
                        )
                    )
                )
                elapsed.append((time.monotonic() - started) * 1000)

    await asyncio.gather(*(viewer() for _ in range(50)))
    elapsed.sort()
    result = {
        "clients": 50,
        "rounds": 5,
        "queries": len(elapsed),
        "failed": 0,
        "p95_ms": round(elapsed[int(len(elapsed) * 0.95) - 1], 2),
        "max_ms": round(max(elapsed), 2),
        "p95_limit_ms": 3000,
    }
    assert result["p95_ms"] <= result["p95_limit_ms"], "Local runtime query p95 exceeds 3 seconds"
    return result


def verify_restored(client: httpx.Client, origin: str, sid: str, asset: str, media: bytes):
    mutation = headers(client, origin)
    screen = require(client.get(f"/api/admin/screens/{sid}"))
    edited = require(
        client.patch(
            f"/api/admin/screens/{sid}",
            headers=mutation,
            json={
                "name": "Restored local fixture",
                "expected_revision": screen["draft_revision"],
                "draft_document": screen["draft_document"],
            },
        )
    )
    require(
        client.post(
            f"/api/admin/screens/{sid}/publish",
            headers=mutation,
            json={"expected_revision": edited["draft_revision"]},
        )
    )
    key = require(client.post(f"/api/admin/screens/{sid}/display-key", headers=mutation), 201)[
        "key"
    ]
    with httpx.Client(base_url=origin, timeout=15) as viewer:
        require(viewer.post(f"/api/player/screens/{sid}/session", json={"key": key}), 204)
        assert_rows(
            require(viewer.post(f"/api/player/screens/{sid}/query", json={"component_id": "chart"}))
        )
        assert viewer.get(f"/api/player/screens/{sid}/assets/{asset}").content == media
    api_key = require(client.post("/api/admin/embed/api-key", headers=mutation), 201)["api_key"]
    ticket = require(
        client.post(
            "/api/embed/tickets",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"screen_id": sid, "allowed_origin": "https://fixture.example"},
        ),
        201,
    )["ticket"]
    auth = {"Authorization": f"Bearer {ticket}", "Origin": "https://fixture.example"}
    assert_rows(
        require(
            client.post(
                f"/api/embed/screens/{sid}/query", headers=auth, json={"component_id": "chart"}
            )
        )
    )
    assert client.get(f"/api/embed/screens/{sid}/assets/{asset}", headers=auth).content == media


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    args.evidence_dir.mkdir(parents=True, exist_ok=False)
    suffix = secrets.token_hex(5)
    name, volume = f"datapulse-p4-{suffix}", f"datapulse-p4-{suffix}-data"
    settings = {
        # This disposable loopback HTTP preflight does not terminate TLS. Production
        # Secure cookies are exercised only through the target TLS/proxy gate.
        "DATAPULSE_ENVIRONMENT": "test",
        "DATAPULSE_MASTER_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
        "DATAPULSE_SIGNING_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
    }
    password = secrets.token_urlsafe(24)
    report = {
        "started_at": datetime.now(UTC).isoformat(),
        "image": args.image,
        "cpu_limit": 2,
        "memory_limit_bytes": 4 * 1024**3,
        "pids_limit": 256,
        "application_environment": "test",
        "transport": "loopback HTTP",
        "status": "failed",
    }
    stage = "startup"
    try:
        report["image_id"] = docker("image", "inspect", args.image, "--format", "{{.Id}}").strip()
        with tempfile.TemporaryDirectory(prefix="datapulse-local-smoke-") as temporary:
            env_file = Path(temporary) / "fixture.env"
            write_env(env_file, settings)
            origin = start(args.image, name, volume, env_file)
            setup = re.search(r"one-time setup code: (\S+)", docker("logs", name))
            if setup is None:
                # Bootstrap is written to stderr; capture internally without saving it.
                logs = subprocess.run(
                    ["docker", "logs", name], capture_output=True, text=True, check=True
                )
                setup = re.search(r"one-time setup code: (\S+)", logs.stdout + logs.stderr)
            assert setup, "Setup code missing"
            with httpx.Client(base_url=origin, timeout=45) as client:
                require(
                    client.post(
                        "/api/auth/setup",
                        headers={"Origin": origin},
                        json={"code": setup[1], "username": "admin", "password": password},
                    ),
                    201,
                )
                stage = "seed"
                sid, asset, media = seed(client, origin)
                key = require(
                    client.post(
                        f"/api/admin/screens/{sid}/display-key", headers=headers(client, origin)
                    ),
                    201,
                )["key"]
                stage = "capacity"
                report["capacity"] = asyncio.run(capacity(origin, sid, key))
            report["container_usage"] = json.loads(
                docker("stats", "--no-stream", "--format", "{{json .}}", name)
            )
            docker("stop", name)
            retain_request_logs(name, args.evidence_dir / "requests-initial.jsonl")
            docker("rm", name)
            stage = "backup"

            def maintenance(*command: str):
                return docker(
                    "run",
                    "--rm",
                    "--env-file",
                    str(env_file),
                    "-v",
                    f"{volume}:/data",
                    "--entrypoint",
                    "/app/.venv/bin/python",
                    args.image,
                    "-m",
                    "datapulse.operations.cli",
                    "backup",
                    *command,
                )

            maintenance("create", "--archive", "/data/fixture.zip", "--maintenance")
            checked = json.loads(maintenance("verify", "--archive", "/data/fixture.zip"))
            report["backup_members"] = len(checked["manifest"]["members"])
            stage = "restore"
            started = time.monotonic()
            maintenance(
                "restore",
                "--archive",
                "/data/fixture.zip",
                "--target",
                "/data/restored",
                "--maintenance",
            )
            report["restore_seconds"] = round(time.monotonic() - started, 3)
            settings["DATAPULSE_DATA_DIR"] = "/data/restored"
            write_env(env_file, settings)
            origin = start(args.image, name, volume, env_file)
            with httpx.Client(base_url=origin, timeout=30) as client:
                login(client, origin, password)
                verify_restored(client, origin, sid, asset, media)
            stage = "restart"
            docker("stop", name)
            retain_request_logs(name, args.evidence_dir / "requests-restored.jsonl")
            docker("rm", name)
            origin = start(args.image, name, volume, env_file)
            with httpx.Client(base_url=origin, timeout=30) as client:
                login(client, origin, password)
                assert (
                    require(client.get(f"/api/admin/screens/{sid}"))["name"]
                    == "Restored local fixture"
                )
            report["status"] = "passed"
    except Exception as error:
        report["failed_stage"] = stage
        report["error_type"] = type(error).__name__
        if isinstance(error, RuntimeError):
            report["error"] = str(error)
    finally:
        retain_request_logs(name, args.evidence_dir / "requests-final.jsonl")
        for command in [("rm", "-f", name), ("volume", "rm", volume)]:
            subprocess.run(["docker", *command], capture_output=True, timeout=60)
        report["finished_at"] = datetime.now(UTC).isoformat()
        (args.evidence_dir / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
