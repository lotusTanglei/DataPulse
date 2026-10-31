import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def test_upgrade_rollback_verification_command_and_guide_are_complete() -> None:
    scripts = json.loads((REPOSITORY_ROOT / "package.json").read_text(encoding="utf-8"))[
        "scripts"
    ]
    assert scripts["verify:upgrade-rollback"] == (
        "uv run --package datapulse-server pytest "
        "apps/server/tests/metadata/test_migrations.py "
        "apps/server/tests/contracts/test_version_migrations.py "
        "apps/server/tests/operations/test_restore_rehearsal.py"
    )
    guide = (REPOSITORY_ROOT / "docs/operations/version-migrations.md").read_text(
        encoding="utf-8"
    )
    for required in (
        "pnpm verify:upgrade-rollback",
        "文档版本",
        "组件版本",
        "模板版本",
        "编辑命令版本",
        "备份",
        "恢复",
        "回滚",
    ):
        assert required in guide


def test_each_scenario_pack_has_a_documented_repository_case() -> None:
    manifest = json.loads(
        (REPOSITORY_ROOT / "fixtures/scenarios/manifest.json").read_text(encoding="utf-8")
    )
    catalog = (REPOSITORY_ROOT / "docs/scenarios/README.md").read_text(encoding="utf-8")

    assert len(manifest["packs"]) == 4
    for pack in manifest["packs"]:
        case_path = REPOSITORY_ROOT / "docs/scenarios" / f"{pack['id']}.md"
        case = case_path.read_text(encoding="utf-8")
        assert pack["name"] in catalog
        assert pack["name"] in case
        assert pack["sample_data"] in case
        assert (REPOSITORY_ROOT / pack["sample_data"]).is_file()
        assert pack["template_id"] in case


def test_contribution_workflow_enforces_component_quality_gates() -> None:
    contributing = (REPOSITORY_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    pull_request = (
        REPOSITORY_ROOT / ".github/pull_request_template.md"
    ).read_text(encoding="utf-8")
    combined = contributing + pull_request

    for required in (
        "合同版本",
        "一个数据源",
        "pnpm verify",
        "视觉回归",
        "E2E",
        "迁移",
    ):
        assert required in combined
