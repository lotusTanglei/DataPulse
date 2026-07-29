import pytest
from pydantic import ValidationError

from datapulse.contracts.dataset import DatasetDefinition


def dataset_payload() -> dict[str, object]:
    return {
        "id": "sales",
        "name": "Sales",
        "data_source_id": "warehouse",
        "query": {
            "kind": "sql",
            "sql": "SELECT month, amount FROM sales",
        },
        "fields": (
            {"name": "month", "data_type": "string"},
            {"name": "amount", "data_type": "number"},
        ),
        "cache": {"mode": "disabled"},
        "refresh": {"mode": "manual"},
        "max_rows": 5000,
        "timeout_seconds": 30,
    }


def test_dataset_definition_round_trips_with_schema_version() -> None:
    dataset = DatasetDefinition.model_validate(dataset_payload())

    restored = DatasetDefinition.model_validate_json(dataset.model_dump_json())

    assert dataset.schema_version == 1
    assert restored == dataset
    assert restored.query.kind == "sql"


@pytest.mark.parametrize("sql", ["", "   "])
def test_dataset_definition_rejects_blank_sql(sql: str) -> None:
    payload = dataset_payload()
    payload["query"] = {"kind": "sql", "sql": sql}

    with pytest.raises(ValidationError):
        DatasetDefinition.model_validate(payload)
