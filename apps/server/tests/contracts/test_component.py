import pytest
from pydantic import ValidationError

from datapulse.contracts.component import ComponentContract


def test_component_contract_versions_props_and_data_input_schemas() -> None:
    contract = ComponentContract.model_validate(
        {
            "type": "builtin.relation_graph",
            "version": "1.0.0",
            "category": "图表",
            "props_schema": {"type": "object", "properties": {}},
            "data_input_schema": {
                "type": "object",
                "required": ["source", "target"],
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                },
            },
        }
    )

    assert contract.schema_version == 1
    assert contract.version == "1.0.0"
    assert contract.props_schema["type"] == "object"
    assert contract.data_input_schema["type"] == "object"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("type", "relation_graph"),
        ("version", "v1"),
        ("props_schema", {"type": "array"}),
        ("data_input_schema", {"properties": {}}),
    ],
)
def test_component_contract_rejects_unversioned_or_ambiguous_shapes(
    field: str,
    value: object,
) -> None:
    payload = {
        "type": "builtin.relation_graph",
        "version": "1.0.0",
        "category": "图表",
        "props_schema": {"type": "object", "properties": {}},
        "data_input_schema": {"type": "object", "properties": {}},
        field: value,
    }

    with pytest.raises(ValidationError):
        ComponentContract.model_validate(payload)
