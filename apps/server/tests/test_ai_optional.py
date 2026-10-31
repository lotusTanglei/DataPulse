import ast
import subprocess
import sys
from pathlib import Path

from datapulse.app import create_app
from datapulse.settings import Settings

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPOSITORY_ROOT / "apps" / "server" / "src" / "datapulse"


def test_core_python_modules_do_not_import_ai_package() -> None:
    violations: list[str] = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        if "ai" in path.relative_to(PACKAGE_ROOT).parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "datapulse.ai"
            ):
                violations.append(f"{path.relative_to(REPOSITORY_ROOT)}:{node.lineno}")
            if isinstance(node, ast.Import):
                violations.extend(
                    f"{path.relative_to(REPOSITORY_ROOT)}:{node.lineno}"
                    for alias in node.names
                    if alias.name.startswith("datapulse.ai")
                )

    assert violations == []


def test_ai_routes_are_absent_when_disabled_and_present_when_enabled() -> None:
    disabled_paths = set(create_app(Settings(ai_enabled=False)).openapi()["paths"])
    enabled_paths = set(create_app(Settings(ai_enabled=True)).openapi()["paths"])

    assert not any(path.startswith("/api/admin/ai") for path in disabled_paths)
    assert "/api/admin/ai/status" in enabled_paths
    assert "/api/admin/datasets" in disabled_paths
    assert "/api/admin/screens" in disabled_paths


def test_repeatable_no_ai_deployment_verification_command() -> None:
    result = subprocess.run(
        [sys.executable, "tools/verify_no_ai_deployment.py"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert '"ai_loaded": false' in result.stdout
    assert '"status": "ok"' in result.stdout
