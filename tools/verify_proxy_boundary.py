from __future__ import annotations

import argparse
import base64
import json
import re
import secrets
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
NGINX_CONFIG = ROOT / "deploy" / "nginx" / "datapulse.conf"
ADMIN_PASSWORD = "proxy-e2e-password"


def command(
    *arguments: str,
    check: bool = True,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        cwd=ROOT,
        check=check,
        capture_output=capture,
        text=True,
    )


def docker(*arguments: str, check: bool = True) -> str:
    return command("docker", *arguments, check=check).stdout.strip()


def container_logs(container: str) -> str:
    completed = command("docker", "logs", container)
    return f"{completed.stdout}{completed.stderr}".strip()


def require_status(response: httpx.Response, status: int) -> dict[str, Any]:
    if response.status_code != status:
        raise RuntimeError(
            f"Expected HTTP {status}, got {response.status_code}: {response.text[:500]}"
        )
    if not response.content:
        return {}
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Expected a JSON object response.")
    return payload


def mutation_headers(client: httpx.Client, origin: str) -> dict[str, str]:
    csrf = client.cookies.get("datapulse_csrf")
    if not csrf:
        raise RuntimeError("The CSRF cookie was not set through the TLS proxy.")
    return {"Origin": origin, "X-CSRF-Token": csrf}


def wait_for_healthy(container: str) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        status = docker("inspect", "--format", "{{.State.Health.Status}}", container)
        if status == "healthy":
            return
        if status == "unhealthy":
            raise RuntimeError(f"Container {container} became unhealthy.")
        time.sleep(1)
    raise RuntimeError(f"Container {container} did not become healthy in time.")


def wait_for_proxy(base_url: str) -> None:
    deadline = time.monotonic() + 30
    with httpx.Client(base_url=base_url, verify=False, trust_env=False) as client:
        while time.monotonic() < deadline:
            try:
                if client.get("/api/health").status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.5)
    raise RuntimeError("The TLS reverse proxy did not become ready in time.")


def error_contract(response: httpx.Response, code: str) -> bool:
    payload = require_status(response, 403)
    error = payload.get("error")
    if not isinstance(error, dict) or error.get("code") != code:
        actual = error.get("code") if isinstance(error, dict) else None
        raise RuntimeError(f"Expected {code}, got {actual!r}.")
    request_id = error.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        raise RuntimeError("The error response did not contain a request ID.")
    return True


def verify_boundary(
    *,
    base_url: str,
    proxy_ip: str,
    proxy_container: str,
    app_container: str,
    setup_code: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    host_origin = "https://host.example.test"
    secrets_to_redact: dict[str, str] = {setup_code: "[SETUP_CODE]"}
    with httpx.Client(base_url=base_url, verify=False, trust_env=False) as admin:
        require_status(
            admin.post(
                "/api/auth/setup",
                headers={"Origin": base_url},
                json={
                    "code": setup_code,
                    "username": "proxy-admin",
                    "password": ADMIN_PASSWORD,
                },
            ),
            201,
        )
        headers = mutation_headers(admin, base_url)
        created = require_status(
            admin.post(
                "/api/admin/screens",
                headers=headers,
                json={"name": "Proxy Boundary Screen"},
            ),
            201,
        )
        screen_id = str(created["id"])
        published = require_status(
            admin.post(
                f"/api/admin/screens/{screen_id}/publish",
                headers=headers,
                json={"expected_revision": created["draft_revision"]},
            ),
            200,
        )
        if published.get("published_document") is None:
            raise RuntimeError("The proxy fixture screen was not published.")
        display_payload = require_status(
            admin.post(
                f"/api/admin/screens/{screen_id}/display-key",
                headers=headers,
            ),
            201,
        )
        display_key = str(display_payload["key"])
        secrets_to_redact[display_key] = "[DISPLAY_KEY]"

        require_status(
            admin.patch(
                f"/api/admin/screens/{screen_id}/access-policy",
                headers=headers,
                json={"allowed_origins": [], "allowed_ips": ["198.51.100.7"]},
            ),
            200,
        )
        with httpx.Client(base_url=base_url, verify=False, trust_env=False) as viewer:
            spoofed = viewer.post(
                f"/api/player/screens/{screen_id}/session",
                headers={
                    "Origin": "https://evil.example.test",
                    "X-Forwarded-For": "198.51.100.7",
                    "X-Forwarded-Proto": "http",
                },
                json={"key": display_key},
            )
            spoof_rejected = error_contract(spoofed, "DISPLAY_ADDRESS_DENIED")

            require_status(
                admin.patch(
                    f"/api/admin/screens/{screen_id}/access-policy",
                    headers=headers,
                    json={
                        "allowed_origins": [host_origin],
                        "allowed_ips": [proxy_ip],
                    },
                ),
                200,
            )
            allowed = viewer.post(
                f"/api/player/screens/{screen_id}/session",
                headers={"Origin": "https://evil.example.test"},
                json={"key": display_key},
            )
            require_status(allowed, 204)
            display_cookie = allowed.headers.get("set-cookie", "")
            cookie_flags = {
                "http_only": "httponly" in display_cookie.lower(),
                "secure": "secure" in display_cookie.lower(),
                "same_site_lax": "samesite=lax" in display_cookie.lower(),
                "player_path": "path=/api/player" in display_cookie.lower(),
            }
            if not all(cookie_flags.values()):
                raise RuntimeError(f"Invalid display cookie flags: {cookie_flags}")

        api_key_payload = require_status(
            admin.post("/api/admin/embed/api-key", headers=headers),
            201,
        )
        api_key = str(api_key_payload["api_key"])
        secrets_to_redact[api_key] = "[EMBED_API_KEY]"
        ticket_payload = require_status(
            admin.post(
                "/api/embed/tickets",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "screen_id": screen_id,
                    "allowed_origin": host_origin,
                    "lifetime_seconds": 3600,
                },
            ),
            201,
        )
        ticket = str(ticket_payload["ticket"])
        secrets_to_redact[ticket] = "[EMBED_TICKET]"

    with httpx.Client(base_url=base_url, verify=False, trust_env=False) as viewer:
        embedded = viewer.get(
            f"/embed/{screen_id}",
            params={"ticket": ticket},
            headers={"Origin": host_origin},
        )
        if embedded.status_code != 200:
            raise RuntimeError(
                f"Expected embed HTML 200, got {embedded.status_code}: {embedded.text[:500]}"
            )
        security_headers = {
            "cache_control": embedded.headers.get("cache-control"),
            "content_security_policy": embedded.headers.get("content-security-policy"),
            "referrer_policy": embedded.headers.get("referrer-policy"),
            "x_content_type_options": embedded.headers.get("x-content-type-options"),
        }
        expected_headers = {
            "cache_control": "no-store",
            "content_security_policy": f"frame-ancestors {host_origin}",
            "referrer_policy": "no-referrer",
            "x_content_type_options": "nosniff",
        }
        if security_headers != expected_headers:
            raise RuntimeError(f"Unexpected embed security headers: {security_headers}")
        cross_origin_rejected = error_contract(
            viewer.get(
                f"/embed/{screen_id}",
                params={"ticket": ticket},
                headers={"Origin": "https://evil.example.test"},
            ),
            "EMBED_ORIGIN_DENIED",
        )

    time.sleep(0.2)
    proxy_logs = container_logs(proxy_container)
    app_logs = container_logs(app_container)
    if setup_code in proxy_logs or app_logs.count(setup_code) != 1:
        raise RuntimeError("The one-time setup code crossed its intended startup log boundary.")
    for secret in (display_key, api_key, ticket):
        if secret in proxy_logs or secret in app_logs:
            raise RuntimeError("A temporary credential appeared in container logs.")
    if "?" in "\n".join(line for line in proxy_logs.splitlines() if " /embed/" in line):
        raise RuntimeError("The proxy access log retained an embed query string.")

    return (
        {
            "tls_proxy_health": "passed",
            "same_origin_mutation_through_tls_termination": "passed",
            "spoofed_forwarded_headers_rejected": spoof_rejected,
            "trusted_proxy_client_ip_allowed": True,
            "display_cookie": cookie_flags,
            "embed_security_headers": security_headers,
            "cross_origin_embed_rejected": cross_origin_rejected,
            "setup_code_app_log_occurrences": 1,
            "setup_code_in_proxy_log": False,
            "temporary_credentials_in_logs": False,
            "proxy_query_strings_logged": False,
        },
        {
            "proxy": proxy_logs,
            "app": app_logs,
            **secrets_to_redact,
        },
    )


def redact_logs(value: str, replacements: dict[str, str]) -> str:
    redacted = value
    for secret, replacement in replacements.items():
        redacted = redacted.replace(secret, replacement)
    redacted = re.sub(
        r"ticket=[^&\s\"]+",
        "ticket=[REDACTED]",
        redacted,
    )
    redacted = re.sub(
        r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
        "[REDACTED_JWT]",
        redacted,
    )
    return re.sub(
        r"(DataPulse one-time setup code: )\S+",
        r"\1[REDACTED]",
        redacted,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-context", type=Path, default=ROOT)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    arguments = parser.parse_args()
    build_context = arguments.build_context.resolve()
    evidence_dir = arguments.evidence_dir.resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    if not (build_context / "Dockerfile").is_file():
        raise RuntimeError(f"No Dockerfile found in build context: {build_context}")

    suffix = uuid4().hex[:10]
    image = f"datapulse-proxy-check:{suffix}"
    network = f"datapulse-proxy-check-{suffix}"
    volume = f"datapulse-proxy-check-{suffix}"
    app_container = f"datapulse-proxy-app-{suffix}"
    proxy_container = f"datapulse-proxy-nginx-{suffix}"
    created: list[tuple[str, str]] = []
    build_log = evidence_dir / "build.log"

    try:
        built = command(
            "docker",
            "build",
            "-t",
            image,
            str(build_context),
            check=False,
            capture=True,
        )
        build_log.write_text(built.stdout + built.stderr, encoding="utf-8")
        if built.returncode != 0:
            raise RuntimeError(
                f"The production image build failed with exit code {built.returncode}."
            )
        created.append(("image", image))
        docker("network", "create", network)
        created.append(("network", network))
        docker("volume", "create", volume)
        created.append(("volume", volume))
        subnet = docker(
            "network",
            "inspect",
            "--format",
            "{{(index .IPAM.Config 0).Subnet}}",
            network,
        )
        gateway = docker(
            "network",
            "inspect",
            "--format",
            "{{(index .IPAM.Config 0).Gateway}}",
            network,
        )
        master_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        signing_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        docker(
            "run",
            "-d",
            "--name",
            app_container,
            "--network",
            network,
            "--network-alias",
            "datapulse",
            "--health-cmd",
            "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health').read()\"",
            "--health-interval",
            "1s",
            "--health-timeout",
            "3s",
            "--health-retries",
            "30",
            "-e",
            f"DATAPULSE_MASTER_KEY={master_key}",
            "-e",
            f"DATAPULSE_SIGNING_KEY={signing_key}",
            "-e",
            f"DATAPULSE_FORWARDED_ALLOW_IPS={subnet}",
            "-v",
            f"{volume}:/data",
            image,
        )
        created.append(("container", app_container))
        wait_for_healthy(app_container)
        bootstrap_match = re.search(
            r"DataPulse one-time setup code: (\S+)",
            container_logs(app_container),
        )
        if bootstrap_match is None:
            raise RuntimeError("The production container did not emit a setup code.")
        setup_code = bootstrap_match.group(1)

        with tempfile.TemporaryDirectory(prefix="datapulse-proxy-tls-") as tls_dir_value:
            tls_dir = Path(tls_dir_value)
            command(
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-keyout",
                str(tls_dir / "key.pem"),
                "-out",
                str(tls_dir / "cert.pem"),
                "-days",
                "1",
                "-subj",
                "/CN=127.0.0.1",
                "-addext",
                "subjectAltName=IP:127.0.0.1",
            )
            docker(
                "run",
                "-d",
                "--name",
                proxy_container,
                "--network",
                network,
                "-p",
                "127.0.0.1::8443",
                "-v",
                f"{NGINX_CONFIG}:/etc/nginx/nginx.conf:ro",
                "-v",
                f"{tls_dir}:/etc/nginx/tls:ro",
                "nginx:alpine",
            )
            created.append(("container", proxy_container))
            host_port = docker(
                "inspect",
                "--format",
                '{{(index (index .NetworkSettings.Ports "8443/tcp") 0).HostPort}}',
                proxy_container,
            )
            base_url = f"https://127.0.0.1:{host_port}"
            wait_for_proxy(base_url)
            result, logs = verify_boundary(
                base_url=base_url,
                proxy_ip=gateway,
                proxy_container=proxy_container,
                app_container=app_container,
                setup_code=setup_code,
            )
            replacements = {
                key: value for key, value in logs.items() if key not in {"proxy", "app"}
            }
            (evidence_dir / "proxy.log").write_text(
                redact_logs(logs["proxy"], replacements),
                encoding="utf-8",
            )
            (evidence_dir / "app.log").write_text(
                redact_logs(logs["app"], replacements),
                encoding="utf-8",
            )
            (evidence_dir / "result.json").write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        for kind, name in created:
            if kind != "container":
                continue
            label = "proxy" if name == proxy_container else "app"
            diagnostic_path = evidence_dir / f"diagnostic-{label}.log"
            try:
                diagnostic_path.write_text(
                    redact_logs(container_logs(name), {}),
                    encoding="utf-8",
                )
            except subprocess.CalledProcessError:
                pass
        for kind, name in reversed(created):
            if kind == "container":
                docker("rm", "-f", name, check=False)
            elif kind == "volume":
                docker("volume", "rm", name, check=False)
            elif kind == "network":
                docker("network", "rm", name, check=False)
            elif kind == "image":
                docker("image", "rm", name, check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
