import base64
import json
import stat
import subprocess
import sys
from pathlib import Path

from datapulse.operations.delivery import (
    build_compose_command,
    build_demo_document,
    run_clean_delivery_rehearsal,
    write_demo_environment,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def _decode_key(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def test_generated_dashboard_narration_uses_shared_result_and_static_fallback() -> None:
    document = build_demo_document("sales-dataset")
    chart = next(item for item in document["components"] if item["id"] == "sales-trend")
    speaker = next(item for item in document["components"] if item["id"] == "sales-speaker")

    assert chart["data_binding"]["chart_spec"]["dataset_id"] == "sales-dataset"
    assert speaker["data_binding"] == {
        "source": "components",
        "variables": [
            {
                "name": "sales.amount",
                "component_id": "sales-trend",
                "field": "销售额",
                "row": 0,
            }
        ],
    }
    assert speaker["props"]["speech_source"] == "browser"
    assert "audio_asset_id" not in speaker["props"]
    assert "{{sales.amount | number}}" in speaker["props"]["speech_template"]


def test_clean_delivery_rehearsal_covers_publish_play_embed_and_permissions(
    tmp_path: Path,
) -> None:
    report = run_clean_delivery_rehearsal(tmp_path)

    assert report["status"] == "ok"
    assert report["sample_rows"] > 0
    assert report["checks"] == {
        "ai_disabled": True,
        "dataset_profiled": True,
        "draft_created": True,
        "static_speech_fallback": True,
        "published": True,
        "standalone_playback": True,
        "embed_playback": True,
        "embed_permission_denied": True,
    }


def test_demo_deployment_environment_is_secure_and_repeatable(tmp_path: Path) -> None:
    environment_path = tmp_path / ".env.demo"

    first = write_demo_environment(environment_path, http_port=8123)
    second = write_demo_environment(environment_path, http_port=9000)

    assert first == second
    assert first["DATAPULSE_HTTP_PORT"] == "8123"
    assert len(_decode_key(first["DATAPULSE_MASTER_KEY"])) == 32
    assert len(_decode_key(first["DATAPULSE_SIGNING_KEY"])) == 32
    assert first["DATAPULSE_MASTER_KEY"] != first["DATAPULSE_SIGNING_KEY"]
    assert stat.S_IMODE(environment_path.stat().st_mode) == 0o600
    assert build_compose_command(environment_path, "datapulse-demo") == [
        "docker",
        "compose",
        "--env-file",
        str(environment_path),
        "--project-name",
        "datapulse-demo",
        "up",
        "--detach",
        "--build",
        "--wait",
        "datapulse",
    ]


def test_delivery_demo_command_and_operator_guide_are_repeatable(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "tools/run_delivery_demo.py",
            "--output",
            str(tmp_path / "delivery-report.json"),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    report = json.loads((tmp_path / "delivery-report.json").read_text(encoding="utf-8"))
    assert report["status"] == "ok"
    assert '"status": "ok"' in result.stdout

    scripts = json.loads((REPOSITORY_ROOT / "package.json").read_text(encoding="utf-8"))["scripts"]
    assert scripts["demo:verify"].endswith("tools/run_delivery_demo.py")
    assert scripts["demo:deploy"].endswith("tools/deploy_demo.py")

    guide = (REPOSITORY_ROOT / "docs/operations/delivery-demo.md").read_text(encoding="utf-8")
    for required in (
        "pnpm demo:deploy",
        "pnpm demo:verify",
        "接入数据",
        "生成草稿",
        "发布",
        "独立播放",
        "嵌入",
        "权限",
    ):
        assert required in guide
