import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from datapulse.contracts import CONTRACT_MODELS

ROOT = Path(__file__).resolve().parents[4]
SCHEMA_DIR = ROOT / "packages" / "schema" / "schemas"

FIXTURES = {
    "studio-user": {
        "id": "editor-1",
        "username": "editor",
        "role": "editor",
        "active": True,
        "created_at": datetime(2026, 9, 21, tzinfo=UTC),
        "updated_at": datetime(2026, 9, 21, tzinfo=UTC),
    },
    "studio-user-create": {"username": "editor", "password": "fixture-password", "role": "editor"},
    "studio-user-patch": {"active": False},
    "resource-grant": {
        "resource_type": "screen",
        "resource_id": "screen-1",
        "user_id": "editor-1",
        "permission": "read",
    },
    "identity-audit": {
        "id": "audit-1",
        "actor_id": "admin",
        "action": "grant.saved",
        "resource_type": "screen",
        "resource_id": "screen-1",
        "subject_id": "editor-1",
        "request_id": "fixture-1",
        "created_at": datetime(2026, 9, 21, tzinfo=UTC),
    },
    "template-manifest": {
        "kind": "template",
        "id": "org.example.template",
        "version": "1.0.0",
        "compatible_api": ">=1,<2",
        "name": "Template",
        "document": "document.json",
    },
    "template-apply": {"name": "Imported template"},
    "resource-access": {"read": True, "write": False, "publish": False, "manage": False},
    "speech-provider-option": {
        "id": "provider-1",
        "name": "Fixture",
        "language": "zh-CN",
        "default_voice": "alloy",
    },
    "catalog-package": {
        "kind": "template",
        "id": "org.example.template",
        "version": "1.0.0",
        "compatible_api": ">=1,<2",
        "name": "Template",
        "description": "",
        "license": "MIT",
        "source": "local",
        "sha256": "a" * 64,
        "installed_at": datetime(2026, 9, 21, tzinfo=UTC),
        "files": [],
        "manifest": {
            "kind": "template",
            "id": "org.example.template",
            "version": "1.0.0",
            "compatible_api": ">=1,<2",
            "name": "Template",
            "document": "document.json",
        },
    },
    "screen-asset": {
        "id": "asset-1",
        "name": "Avatar",
        "original_name": "avatar.png",
        "asset_type": "image",
        "mime_type": "image/png",
        "sha256": "a" * 64,
        "size_bytes": 100,
        "family_id": "asset-1",
        "version": 1,
        "created_at": datetime(2026, 9, 9, tzinfo=UTC),
    },
    "screen-asset-patch": {"name": "Avatar"},
    "screen-asset-reference": {
        "screen_id": "screen-1",
        "screen_name": "Operations",
        "in_draft": True,
        "in_published": False,
    },
    "screen-asset-usage": {
        "asset_count": 1,
        "size_bytes": 100,
        "duration_seconds": 0,
        "max_total_bytes": 1000,
        "max_total_duration_seconds": 300,
        "max_image_bytes": 1000,
        "max_media_bytes": 1000,
        "max_duration_seconds": 30,
    },
    "analysis-plan": {
        "question": "按月份汇总销售额",
        "dataset_ids": ["sales"],
        "recommended_chart": "line",
    },
    "ai-edit-response": {
        "commands": [
            {
                "type": "update_props",
                "component_id": "title-1",
                "patch": {"text": "新的标题"},
            }
        ],
        "explanation": "更新选中标题。",
        "warnings": [],
    },
    "chart-spec": {
        "dataset_id": "sales",
        "visual": {"type": "line"},
    },
    "dashboard-document": {
        "canvas": {"width": 1920, "height": 1080},
    },
    "dashboard-plan": {
        "title": "销售经营总览",
        "audience": "区域负责人",
        "narrative": "先看核心指标，再看趋势。",
        "dataset_ids": ["sales"],
        "regions": [{"id": "main", "kind": "main"}],
        "widgets": [
            {
                "id": "revenue-trend",
                "title": "销售额趋势",
                "intent": "展示月度销售额变化",
                "region_id": "main",
                "dataset_id": "sales",
                "chart_type": "line",
            }
        ],
    },
    "dataset-definition": {
        "id": "sales",
        "name": "Sales",
        "query": {"kind": "sql", "sql": "SELECT month, amount FROM sales"},
    },
    "digital-human-trigger": {"kind": "data_change"},
    "digital-human-action": {
        "id": "wave",
        "kind": "wave",
        "asset_id": "action-asset",
        "asset_kind": "image",
    },
    "speech-script-segment": {"kind": "pause", "duration_ms": 800},
    "digital-human-binding": {
        "source": "components",
        "variables": [{"name": "sales.value", "component_id": "sales", "field": "value"}],
    },
    "digital-human-spec": {
        "name": "播报员",
        "speech_template": "当前值 {{value | number}}",
        "trigger": {"kind": "data_change"},
    },
    "digital-human-provider": {
        "id": "provider-1",
        "name": "测试 TTS",
        "provider_type": "custom",
        "base_url": "https://tts.example.com",
        "default_voice": "zh-CN-1",
        "language": "zh-CN",
        "enabled": True,
        "configured": False,
        "cost_per_minute": 0,
        "provider_version": "v1",
        "health_status": "unconfigured",
        "consecutive_failures": 0,
    },
    "digital-human-provider-test": {"ok": True, "latency_ms": 12, "voices": ["zh-CN-1"]},
    "digital-human-usage": {
        "period_start": datetime(2026, 9, 9, tzinfo=UTC),
        "task_count": 2,
        "succeeded_count": 1,
        "failed_count": 1,
        "generated_seconds": 3.5,
        "cached_count": 0,
        "estimated_cost": 0,
    },
    "digital-human-settings": {
        "enabled": True,
        "default_muted": False,
        "default_subtitles": True,
        "max_speech_seconds": 30,
        "cooldown_seconds": 5,
        "daily_task_limit": 1000,
        "daily_audio_seconds_limit": 36000,
        "ai_enabled": True,
        "ai_model": "",
        "ai_context_limit": 100,
        "data_retention_days": 30,
        "forbidden_words": [],
        "sensitive_patterns": [],
        "manual_review_required": False,
        "updated_at": datetime(2026, 9, 9, tzinfo=UTC),
    },
    "digital-human-provider-health": {
        "provider_id": "provider-1",
        "checked_at": datetime(2026, 9, 9, tzinfo=UTC),
        "ok": True,
        "latency_ms": 12,
    },
    "digital-human-cost-report": {
        "period_start": datetime(2026, 9, 9, tzinfo=UTC),
        "period_end": datetime(2026, 9, 10, tzinfo=UTC),
        "rows": [],
        "total_task_count": 0,
        "total_generated_seconds": 0,
        "total_estimated_cost": 0,
    },
    "digital-human-cache-clear": {
        "detached_task_count": 1,
        "deleted_asset_count": 1,
    },
    "digital-human-metrics": {
        "collected_at": datetime(2026, 9, 9, tzinfo=UTC),
        "tasks_queued": 1,
        "tasks_succeeded": 1,
        "tasks_failed": 0,
        "tasks_cancelled": 0,
        "cache_hits": 0,
        "synthesis_attempts": 1,
        "synthesis_failures": 0,
        "synthesis_total_ms": 12.5,
        "average_synthesis_ms": 12.5,
    },
    "digital-human-audit": {
        "id": "audit-1",
        "created_at": datetime(2026, 9, 9, tzinfo=UTC),
        "actor": "system",
        "action": "speech.failed",
        "resource_type": "task",
        "resource_id": "task-1",
        "details": {"error_code": "SPEECH_TASK_FAILED"},
    },
    "digital-human-playback-diagnostic": {
        "screen_id": "screen-1",
        "component_id": "speaker",
        "task_id": "task-1",
        "status": "failed",
        "provider_id": "provider-1",
        "source": "runtime",
        "asset_id": "",
        "error_code": "SPEECH_PROVIDER_UNAVAILABLE",
        "created_at": datetime(2026, 9, 9, tzinfo=UTC),
    },
    "speech-plan": {
        "id": "plan-1",
        "screen_id": "screen-1",
        "component_id": "speaker",
        "text": "当前值 123",
        "language": "zh-CN",
        "provider_id": "",
        "voice": "",
        "provider_version": "v1",
        "content_hash": "a" * 64,
        "created_at": datetime(2026, 9, 9, tzinfo=UTC),
    },
    "speech-task": {
        "id": "task-1",
        "plan_id": "plan-1",
        "status": "queued",
        "provider_id": "",
        "asset_id": "",
        "created_at": datetime(2026, 9, 9, tzinfo=UTC),
    },
    "speech-draft": {"text": "当前值 {{value}}", "warnings": []},
    "embed-message": {"type": "ready", "instance_id": "embed-1"},
    "embed-ticket-claims": {
        "ticket_id": "ticket-1",
        "screen_id": "sales-overview",
        "allowed_origin": "https://host.example.com",
        "issued_at": datetime(2026, 7, 29, tzinfo=UTC),
        "expires_at": datetime(2026, 7, 29, tzinfo=UTC) + timedelta(minutes=5),
    },
    "generation-self-check": {
        "valid": True,
        "widget_count": 1,
        "executed_count": 1,
        "fallback_count": 0,
        "checks": [
            {
                "widget_id": "trend",
                "dataset_id": "sales",
                "row_count": 12,
                "status": "ok",
            }
        ],
    },
    "plugin-manifest": {
        "id": "com.example.status-card",
        "version": "1.2.0",
        "compatible_api": ">=1.0.0,<2.0.0",
        "name": "Status Card",
        "entry": "bundle.mjs",
        "components": [
            {
                "type": "example.status-card",
                "name": "Status Card",
                "category": "indicator",
                "property_schema": {"type": "object"},
                "data_schema": {"type": "object"},
            }
        ],
    },
}


@pytest.mark.parametrize("name", sorted(CONTRACT_MODELS))
def test_exported_schema_is_valid_and_accepts_model_fixture(name: str) -> None:
    schema = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)

    model = CONTRACT_MODELS[name].model_validate(FIXTURES[name])
    Draft202012Validator(schema).validate(model.model_dump(mode="json"))


def test_exported_schema_set_matches_contract_registry() -> None:
    exported = {path.name.removesuffix(".schema.json") for path in SCHEMA_DIR.glob("*.json")}

    assert exported == set(CONTRACT_MODELS)
