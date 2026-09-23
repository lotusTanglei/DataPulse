import json
import sqlite3
import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools import run_e2e  # noqa: E402
from tools.prepare_e2e import cleanup_run, prepare  # noqa: E402


def test_fake_screen_model_returns_semantic_plan_without_pixel_coordinates() -> None:
    content = run_e2e._screen_content("dataset_ids: sales")

    assert "document" not in content
    plan = content["plan"]
    assert plan["dataset_ids"] == ["sales"]
    assert all(widget["dataset_id"] == "sales" for widget in plan["widgets"])
    assert plan["widgets"][0]["measures"][0]["aggregation"] == "count"
    serialized = json.dumps(plan)
    assert all(name not in serialized for name in ('"frame"', '"x"', '"y"'))


def test_fake_ai_content_returns_updated_plan_for_screen_edit() -> None:
    plan = run_e2e._screen_content("dataset_ids: sales")["plan"]
    content = json.loads(
        run_e2e.fake_ai_content(
            {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a DataPulse dashboard planning assistant.",
                    },
                    {
                        "role": "user",
                        "content": (
                            "question: 改成饼图\n"
                            "requested_region_ids: main\n"
                            f"plan: {json.dumps(plan, ensure_ascii=False)}"
                        ),
                    },
                ]
            }
        )
    )

    assert content["affected_region_ids"] == ["main"]
    assert content["plan"]["widgets"][0]["chart_type"] == "pie"
    assert content["explanation"] == "E2E AI 已修改区域对比图表。"


def fixture_runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[Path]:
    runtime_root = tmp_path / "runtime"
    prepared: list[Path] = []

    def prepare_run() -> Path:
        config = prepare(runtime_root)
        prepared.append(config)
        return config

    monkeypatch.setattr(run_e2e, "prepare", prepare_run)
    monkeypatch.setattr(run_e2e, "cleanup_run", lambda config: cleanup_run(config, runtime_root))
    monkeypatch.setattr(run_e2e, "fake_ai_server", lambda: nullcontext("http://fixture-ai/v1"))
    monkeypatch.setattr(run_e2e, "fake_tts_server", lambda: nullcontext("http://fixture-tts/v1"))
    return prepared


@pytest.mark.parametrize("projects", [
    ["--project=firefox", "--project=webkit"],
    ["--project", "firefox", "--project", "webkit"],
    ["--project", "firefox", "webkit"],
    ["--project=firefox", "e2e/identity.spec.ts", "--project=webkit"],
])
def test_browser_runs_isolate_mutable_state_and_preserve_failed_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, projects: list[str]
) -> None:
    prepared = fixture_runner(monkeypatch, tmp_path)
    output = tmp_path / "artifacts"
    monkeypatch.setenv("PLAYWRIGHT_HTML_OUTPUT_DIR", str(tmp_path / "html"))
    monkeypatch.setenv("PLAYWRIGHT_JSON_OUTPUT_FILE", str(tmp_path / "json" / "results.json"))
    monkeypatch.setattr(sys, "argv", [
        "run_e2e", "--", "e2e/screen-editor.spec.ts", *projects,
        "--output", str(output), "--grep", "builds a screen", "--retries=0",
    ])
    calls: list[tuple[list[str], dict[str, str]]] = []
    data_dirs: list[Path] = []

    def launch(command: list[str], *, cwd: Path, env: dict[str, str], check: bool):
        assert cwd == run_e2e.REPOSITORY_ROOT
        assert check is False
        config = json.loads(Path(env["DATAPULSE_E2E_CONFIG"]).read_text())
        data_dir = Path(config["dataDir"])
        if data_dirs:
            assert not data_dirs[-1].exists(), "previous browser must be cleaned first"
        data_dirs.append(data_dir)
        # Both browsers create the same uniquely named screen. Sharing state would
        # fail here just as SCREEN_NAME_CONFLICT fails real browser fixtures.
        with sqlite3.connect(data_dir / "metadata.db") as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS screen (name TEXT UNIQUE)")
            connection.execute("INSERT INTO screen VALUES ('editor fixture')")
        calls.append((command, env))
        output_option = next((item for item in command if item.startswith("--output=")), None)
        evidence_dir = Path(
            output_option.removeprefix("--output=") if output_option
            else command[command.index("--output") + 1]
        )
        evidence_dir.mkdir(parents=True)
        (evidence_dir / "trace.zip").write_bytes(b"browser evidence")
        return subprocess.CompletedProcess(command, 7 if len(calls) == 1 else 0)

    monkeypatch.setattr(run_e2e.subprocess, "run", launch)
    assert run_e2e.main() == 7
    assert len(calls) == 2
    assert len(set(data_dirs)) == 2
    for project, (command, environment) in zip(["firefox", "webkit"], calls, strict=True):
        assert [item for item in command if item.startswith("--project=")] == [
            f"--project={project}"
        ]
        assert "e2e/screen-editor.spec.ts" in command
        assert command[command.index("--grep") + 1] == "builds a screen"
        assert "--retries=0" in command
        assert (output / project / "trace.zip").exists()
        assert environment["DATAPULSE_E2E_TTS_BASE_URL"] == "http://fixture-tts/v1"
        assert environment["DATAPULSE_AI_BASE_URL"] == "http://fixture-ai/v1"
        assert environment["PLAYWRIGHT_HTML_OUTPUT_DIR"] == str(tmp_path / "html" / project)
        assert environment["PLAYWRIGHT_JSON_OUTPUT_FILE"] == str(
            tmp_path / "json" / project / "results.json"
        )
    assert all(not config.exists() for config in prepared)
    assert all(not directory.exists() for directory in data_dirs)


def test_single_target_project_retains_its_arguments_and_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    prepared = fixture_runner(monkeypatch, tmp_path)
    arguments = [
        "--config=playwright.target.config.ts", "--grep", "@soak",
        "--output=target-artifacts", "--reporter=line",
    ]
    monkeypatch.setattr(sys, "argv", ["run_e2e", *arguments])
    commands: list[list[str]] = []

    def launch(command: list[str], **_kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 3)

    monkeypatch.setattr(run_e2e.subprocess, "run", launch)
    assert run_e2e.main() == 3
    assert commands == [[
        "pnpm", "--filter", "@datapulse/web", "exec", "playwright", "test",
        "--project=chromium", *arguments,
    ]]
    assert len(prepared) == 1
    assert not prepared[0].exists()


def test_browser_launch_failure_cleans_up_and_runs_remaining_projects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    prepared = fixture_runner(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", ["run_e2e", "--project=firefox", "--project=webkit"])
    launches = 0

    def launch(command: list[str], **_kwargs):
        nonlocal launches
        launches += 1
        if launches == 1:
            raise OSError("fixture launch failure")
        assert "--output=test-results/webkit" in command
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(run_e2e.subprocess, "run", launch)
    assert run_e2e.main() != 0
    assert launches == 2
    assert all(not config.exists() for config in prepared)
