import pytest
from pydantic import ValidationError

from datapulse.contracts.dashboard import DashboardDocument


def legacy_document() -> dict[str, object]:
    return {
        "canvas": {"width": 1920, "height": 1080},
        "components": [
            {
                "id": "legacy-kpi",
                "type": "builtin.kpi",
                "frame": {"x": 40, "y": 40, "width": 320, "height": 180},
                "data_binding": {
                    "source": "static",
                    "static_data": {
                        "columns": [{"name": "value", "data_type": "number"}],
                        "rows": [[42]],
                    },
                },
            }
        ],
    }


def test_legacy_document_and_components_migrate_to_current_contract() -> None:
    document = DashboardDocument.model_validate(legacy_document())

    assert document.schema_version == 1
    assert document.components[0].schema_version == 1
    assert document.components[0].contract_version == "1.0.0"
    assert document.model_dump(mode="json")["components"][0]["schema_version"] == 1
    assert document.model_dump(mode="json")["components"][0]["contract_version"] == "1.0.0"


@pytest.mark.parametrize(
    "payload",
    [
        {**legacy_document(), "schema_version": 2},
        {
            **legacy_document(),
            "schema_version": 1,
            "components": [
                {
                    **legacy_document()["components"][0],
                    "schema_version": 2,
                }
            ],
        },
        {
            **legacy_document(),
            "schema_version": 1,
            "components": [
                {
                    **legacy_document()["components"][0],
                    "contract_version": "2.0.0",
                }
            ],
        },
    ],
)
def test_future_document_and_component_versions_fail_closed(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError, match="Unsupported .* version"):
        DashboardDocument.model_validate(payload)
