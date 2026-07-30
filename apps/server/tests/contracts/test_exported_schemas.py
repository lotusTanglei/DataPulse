import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from datapulse.contracts import CONTRACT_MODELS

ROOT = Path(__file__).resolve().parents[4]
SCHEMA_DIR = ROOT / "packages" / "schema" / "schemas"

FIXTURES = {
    "analysis-plan": {
        "question": "按月份汇总销售额",
        "dataset_ids": ["sales"],
        "recommended_chart": "line",
    },
    "chart-spec": {
        "dataset_id": "sales",
        "visual": {"type": "line"},
    },
    "dashboard-document": {
        "canvas": {"width": 1920, "height": 1080},
    },
    "dataset-definition": {
        "id": "sales",
        "name": "Sales",
        "query": {"kind": "sql", "sql": "SELECT month, amount FROM sales"},
    },
    "embed-message": {"type": "ready", "instance_id": "embed-1"},
    "embed-ticket-claims": {
        "ticket_id": "ticket-1",
        "screen_id": "sales-overview",
        "allowed_origin": "https://host.example.com",
        "issued_at": datetime(2026, 7, 29, tzinfo=UTC),
        "expires_at": datetime(2026, 7, 29, tzinfo=UTC) + timedelta(minutes=5),
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
