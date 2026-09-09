import json
import sys
from pathlib import Path

import httpx
import pytest


def test_playwright_arguments_default_to_chromium_and_allow_overrides() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from tools.run_e2e import playwright_arguments

    assert playwright_arguments([]) == [
        "--config",
        "playwright.config.ts",
        "--project=chromium",
    ]
    assert playwright_arguments(["--", "--project=webkit"]) == [
        "--config",
        "playwright.config.ts",
        "--project=webkit",
    ]
    assert playwright_arguments(
        ["--config=playwright.target.config.ts", "--grep", "@soak"],
    ) == [
        "--project=chromium",
        "--config=playwright.target.config.ts",
        "--grep",
        "@soak",
    ]


def request_payload(mode: str, *, system: str = "analytics assistant") -> dict[str, object]:
    return {
        "model": "e2e-fake-model",
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (f"question: E2E_MODE:{mode}\ndataset_ids: dataset-1\n"),
            },
        ],
    }


def test_fake_ai_server_exposes_deterministic_modes() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from tools.run_e2e import fake_ai_server

    with fake_ai_server() as base_url:
        valid = httpx.post(
            f"{base_url}/chat/completions",
            json=request_payload("valid-analysis"),
        )
        screen = httpx.post(
            f"{base_url}/chat/completions",
            json=request_payload("valid-screen", system="screen design assistant"),
        )
        invalid = httpx.post(
            f"{base_url}/chat/completions",
            json=request_payload("invalid-field"),
        )
        malformed = httpx.post(
            f"{base_url}/chat/completions",
            json=request_payload("malformed-json"),
        )

        assert json.loads(valid.json()["choices"][0]["message"]["content"])["narrative"]
        assert json.loads(screen.json()["choices"][0]["message"]["content"])["document"]
        assert "unknown_field" in invalid.json()["choices"][0]["message"]["content"]
        assert malformed.json()["choices"][0]["message"]["content"] == "{"
        with pytest.raises(httpx.TimeoutException):
            httpx.post(
                f"{base_url}/chat/completions",
                json=request_payload("timeout"),
                timeout=0.05,
            )
