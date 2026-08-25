from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
    dataset_id = _prompt_value(prompt, "dataset_ids", "missing").split(",", 1)[0]
    if "E2E_UNAUTHORIZED_DATASET" in prompt:
        dataset_id = "not-selected-by-user"
    dimension = "unknown_field" if invalid_field else "region"
    return {
        "document": {
            "schema_version": 1,
            "canvas": {"width": 1920, "height": 1080},
            "components": [
                {
                    "id": "title-1",
                    "type": "builtin.text",
                    "frame": {"x": 40, "y": 32, "width": 1840, "height": 96},
                    "props": {"text": "E2E AI 经营总览", "align": "center"},
                },
                {
                    "id": "bar-1",
                    "type": "builtin.bar",
                    "frame": {"x": 80, "y": 180, "width": 1760, "height": 760},
                    "props": {},
                    "data_binding": {
                        "chart_spec": {
                            "schema_version": 1,
                            "dataset_id": dataset_id,
                            "dimensions": [dimension],
                            "measures": [{"field": "amount", "aggregation": "sum"}],
                            "filters": [],
                            "sort": [],
                            "limit": 100,
                            "visual": {"type": "bar", "title": "区域销售额"},
                        }
                    },
                },
            ],
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


def fake_ai_content(payload: dict[str, Any]) -> str:
    messages = payload.get("messages", [])
    system = str(messages[0].get("content", "")) if messages else ""
    prompt = str(messages[-1].get("content", "")) if messages else ""
    mode = _fake_mode(prompt, system)
    if mode == "timeout":
        time.sleep(2)
    if mode == "malformed-json":
        return "{"
    if "editor assistant" in system or mode == "edit-title":
        return json.dumps(_edit_content(prompt), ensure_ascii=False)
    is_screen = "screen design assistant" in system or mode == "valid-screen"
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


def main() -> int:
    config_path = prepare()
    arguments = sys.argv[1:]
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    try:
        with fake_ai_server() as ai_base_url:
            environment = {
                **os.environ,
                "DATAPULSE_E2E_CONFIG": str(config_path),
                "DATAPULSE_AI_ENABLED": "true",
                "DATAPULSE_AI_BASE_URL": ai_base_url,
                "DATAPULSE_AI_API_KEY": "e2e-fake-key",
                "DATAPULSE_AI_MODEL": "e2e-fake-model",
                "DATAPULSE_AI_TIMEOUT_SECONDS": "1",
            }
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
                    *arguments,
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
