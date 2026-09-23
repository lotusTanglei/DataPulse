from __future__ import annotations

import io
import json
import math
import os
import re
import struct
import subprocess
import sys
import threading
import time
import wave
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from tools.prepare_e2e import REPOSITORY_ROOT, cleanup_run, prepare

_FAKE_MODES = (
    "valid-analysis",
    "valid-screen",
    "edit-title",
    "invalid-field",
    "malformed-json",
    "timeout",
)


def playwright_arguments(arguments: list[str]) -> list[str]:
    normalized = arguments[1:] if arguments[:1] == ["--"] else list(arguments)
    has_config = any(
        argument == "--config" or argument.startswith("--config=")
        for argument in normalized
    )
    has_project = any(
        argument == "--project" or argument.startswith("--project=")
        for argument in normalized
    )
    return [
        *([] if has_config else ["--config", "playwright.config.ts"]),
        *([] if has_project else ["--project=chromium"]),
        *normalized,
    ]


def playwright_runs(arguments: list[str]) -> list[tuple[str | None, list[str]]]:
    """Split named projects while leaving the single-project CLI unchanged."""
    projects: list[str] = []
    common: list[str] = []
    output = "test-results"
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        index += 1
        if argument == "--":
            common.extend(arguments[index - 1:])
            break
        if argument == "--project" or argument.startswith("--project="):
            if argument.startswith("--project="):
                projects.append(argument.removeprefix("--project="))
                # Commander treats inline assignment as one value; following
                # positional test-file filters do not belong to this option.
                continue
            start = index
            # Playwright's project selector is variadic: both repeated options
            # and `--project firefox webkit` are supported.
            while index < len(arguments) and not arguments[index].startswith("-"):
                projects.append(arguments[index])
                index += 1
            if argument == "--project" and index == start:
                return [(None, arguments)]  # Let Playwright diagnose invalid CLI input.
        elif argument == "--output" and index < len(arguments):
            output = arguments[index]
            index += 1
        elif argument.startswith("--output="):
            output = argument.removeprefix("--output=")
        else:
            common.append(argument)
    projects = list(dict.fromkeys(projects))
    if len(projects) < 2:
        return [(None, arguments)]
    runs: list[tuple[str | None, list[str]]] = []
    labels: set[str] = set()
    for project in projects:
        label = re.sub(r"[^A-Za-z0-9_-]+", "-", project).strip("-") or "project"
        if label in labels:
            label = f"{label}-{len(runs) + 1}"
        labels.add(label)
        runs.append((label, [
            f"--project={project}", f"--output={Path(output) / label}", *common,
        ]))
    return runs


def project_report_environment(environment: dict[str, str], project: str) -> None:
    """Keep built-in reporter files from overwriting another browser's evidence."""
    for reporter, default in (("HTML", "playwright-report"), ("BLOB", "blob-report")):
        variable = f"PLAYWRIGHT_{reporter}_OUTPUT_DIR"
        environment[variable] = str(Path(environment.get(variable, default)) / project)
    for reporter in ("JSON", "JUNIT"):
        prefix = f"PLAYWRIGHT_{reporter}_OUTPUT_"
        if filename := environment.get(prefix + "FILE"):
            path = Path(filename)
            environment[prefix + "FILE"] = str(path.parent / project / path.name)
        elif prefix + "DIR" in environment or prefix + "NAME" in environment:
            environment[prefix + "DIR"] = str(
                Path(environment.get(prefix + "DIR", ".")) / project
            )


def _prompt_value(prompt: str, name: str, fallback: str) -> str:
    match = re.search(rf"^{re.escape(name)}:\s*(.+)$", prompt, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def _fake_mode(prompt: str, system: str) -> str:
    for mode in _FAKE_MODES:
        if f"E2E_MODE:{mode}" in prompt:
            return mode
    return "valid-screen" if "screen design assistant" in system else "valid-analysis"


def _analysis_content(prompt: str, *, invalid_field: bool = False) -> dict[str, Any]:
    dataset_id = _prompt_value(prompt, "dataset_ids", "missing").split(",", 1)[0]
    question = _prompt_value(prompt, "question", "E2E analysis")
    dimension = "unknown_field" if invalid_field else "region"
    return {
        "plan": {
            "schema_version": 1,
            "question": question,
            "dataset_ids": [dataset_id],
            "dimensions": [dimension],
            "measures": [{"field": "amount", "aggregation": "sum"}],
            "filters": [],
            "sort": [],
            "recommended_chart": "bar",
            "assumptions": ["E2E fixed response"],
            "requires_confirmation": True,
        },
        "narrative": "E2E AI 建议按区域汇总销售额。",
        "chart_spec": {
            "schema_version": 1,
            "dataset_id": dataset_id,
            "dimensions": [dimension],
            "measures": [{"field": "amount", "aggregation": "sum"}],
            "filters": [],
            "sort": [],
            "limit": 100,
            "visual": {"type": "bar", "title": "区域销售额"},
        },
        "warnings": [],
    }


def _screen_content(prompt: str, *, invalid_field: bool = False) -> dict[str, Any]:
    requested_dataset_id = _prompt_value(prompt, "dataset_ids", "missing").split(",", 1)[0]
    dataset_id = requested_dataset_id
    if "E2E_UNAUTHORIZED_DATASET" in prompt:
        dataset_id = "not-selected-by-user"
    dimension = "unknown_field" if invalid_field else "region"
    return {
        "plan": {
            "schema_version": 1,
            "title": "E2E AI 经营总览",
            "audience": "经营负责人",
            "narrative": "展示区域销售额对比。",
            "dataset_ids": [requested_dataset_id],
            "layout": {
                "template": "comparison-board",
                "grid_columns": 24,
                "density": "comfortable",
                "theme": "dark",
            },
            "regions": [
                {
                    "id": "main",
                    "kind": "main",
                    "title": "区域对比",
                    "order": 0,
                }
            ],
            "widgets": [
                {
                    "id": "bar-1",
                    "title": "区域销售额",
                    "intent": "比较各区域销售额",
                    "region_id": "main",
                    "dataset_id": dataset_id,
                    "chart_type": "bar",
                    "dimensions": [dimension],
                    "measures": [{"field": "amount", "aggregation": "count"}],
                    "filters": [],
                    "sort": [],
                    "limit": 100,
                }
            ],
            "parameters": [],
        },
        "explanation": "E2E AI 已生成标题和区域销售额图表。",
        "warnings": [],
    }


def _edit_content(prompt: str) -> dict[str, Any]:
    component_id = _prompt_value(prompt, "selected_component_ids", "title-1").split(",", 1)[0]
    return {
        "commands": [
            {
                "type": "update_props",
                "component_id": component_id,
                "patch": {"text": "E2E AI 局部修改标题"},
            }
        ],
        "explanation": "E2E AI 已修改选中标题。",
        "warnings": [],
    }


def _screen_edit_content(prompt: str) -> dict[str, Any]:
    plan = json.loads(_prompt_value(prompt, "plan", "{}"))
    affected_region_ids = [
        item.strip()
        for item in _prompt_value(prompt, "requested_region_ids", "main").split(",")
        if item.strip()
    ]
    widgets = plan.get("widgets", [])
    if widgets:
        widgets[0]["chart_type"] = "pie"
    return {
        "plan": plan,
        "affected_region_ids": affected_region_ids,
        "explanation": "E2E AI 已修改区域对比图表。",
        "warnings": [],
    }


def fake_ai_content(payload: dict[str, Any]) -> str:
    messages = payload.get("messages", [])
    system = str(messages[0].get("content", "")) if messages else ""
    prompt = str(messages[-1].get("content", "")) if messages else ""
    mode = _fake_mode(prompt, system)
    if mode == "timeout":
        time.sleep(2)
    if mode == "malformed-json":
        return "{"
    if "requested_region_ids:" in prompt and "plan:" in prompt:
        return json.dumps(_screen_edit_content(prompt), ensure_ascii=False)
    if "editor assistant" in system or mode == "edit-title":
        return json.dumps(_edit_content(prompt), ensure_ascii=False)
    is_screen = (
        "dashboard planning assistant" in system
        or "screen design assistant" in system
        or mode == "valid-screen"
    )
    content = (
        _screen_content(prompt, invalid_field=mode == "invalid-field")
        if is_screen
        else _analysis_content(prompt, invalid_field=mode == "invalid-field")
    )
    return json.dumps(content, ensure_ascii=False)


class _FakeAiHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length))
            content = fake_ai_content(payload)
            body = json.dumps(
                {"choices": [{"message": {"content": content}}]},
                ensure_ascii=False,
            ).encode()
        except (TypeError, ValueError):
            self.send_error(400)
            return
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format: str, *args: object) -> None:
        del format, args


class _FakeTtsHandler(BaseHTTPRequestHandler):
    """Deterministic, local-only TTS fixture for browser integration tests."""

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/v1/voices":
            self.send_error(404)
            return
        self._send(
            200,
            "application/json",
            b'{"data":[{"id":"alloy"},{"id":"fixture-voice"}]}',
        )

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/audio/speech":
            self.send_error(404)
            return
        if self.headers.get("Authorization") != "Bearer e2e-fake-tts-key":
            self.send_error(401)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            json.loads(self.rfile.read(length))
            stream = io.BytesIO()
            with wave.open(stream, "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(16_000)
                frames = bytearray()
                for index in range(16_000):
                    sample = int(10_000 * math.sin(2 * math.pi * 440 * index / 16_000))
                    frames.extend(struct.pack("<h", sample))
                audio.writeframes(bytes(frames))
            self._send(200, "audio/wav", stream.getvalue())
        except (TypeError, ValueError, wave.Error):
            self.send_error(400)

    def log_message(self, format: str, *args: object) -> None:
        del format, args


@contextmanager
def fake_ai_server() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeAiHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@contextmanager
def fake_tts_server() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeTtsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def main() -> int:
    exit_code = 0
    for project, arguments in playwright_runs(playwright_arguments(sys.argv[1:])):
        config_path: Path | None = None
        try:
            config_path = prepare()
            if project:
                print(f"[E2E] Running isolated project: {project}", flush=True)
            with fake_ai_server() as ai_base_url, fake_tts_server() as tts_base_url:
                environment = {
                    **os.environ,
                    "DATAPULSE_E2E_CONFIG": str(config_path),
                    "DATAPULSE_AI_ENABLED": "true",
                    "DATAPULSE_AI_BASE_URL": ai_base_url,
                    "DATAPULSE_AI_API_KEY": "e2e-fake-key",
                    "DATAPULSE_AI_MODEL": "e2e-fake-model",
                    "DATAPULSE_AI_TIMEOUT_SECONDS": "1",
                    # E2E-only key so the server can encrypt the fake provider secret.
                    "DATAPULSE_MASTER_KEY": (
                        "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
                    ),
                    "DATAPULSE_E2E_TTS_BASE_URL": tts_base_url,
                    "DATAPULSE_E2E_TTS_API_KEY": "e2e-fake-tts-key",
                }
                if project:
                    project_report_environment(environment, project)
                completed = subprocess.run(
                    [
                        "pnpm",
                        "--filter",
                        "@datapulse/web",
                        "exec",
                        "playwright",
                        "test",
                        *arguments,
                    ],
                    cwd=REPOSITORY_ROOT,
                    env=environment,
                    check=False,
                )
                exit_code = exit_code or completed.returncode
        except OSError as error:
            print(f"[E2E] Could not run {project or 'project'}: {error}", file=sys.stderr)
            exit_code = exit_code or 1
        finally:
            if config_path is not None:
                cleanup_run(config_path)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
