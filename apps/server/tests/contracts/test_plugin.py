import pytest
from pydantic import ValidationError

from datapulse.contracts.plugin import PluginManifest


def manifest_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": "com.example.status-card",
        "version": "1.2.0",
        "compatible_api": ">=1.0.0,<2.0.0",
        "name": "Status Card",
        "entry": "bundle.mjs",
        "components": (
            {
                "type": "example.status-card",
                "name": "Status Card",
                "category": "indicator",
                "property_schema": {"type": "object"},
                "data_schema": {"type": "object"},
            },
        ),
    }


def test_plugin_manifest_round_trips() -> None:
    manifest = PluginManifest.model_validate(manifest_payload())

    restored = PluginManifest.model_validate_json(manifest.model_dump_json())

    assert restored == manifest
    assert restored.components[0].type == "example.status-card"


@pytest.mark.parametrize("plugin_id", ["StatusCard", "status-card", "com.Example.card"])
def test_plugin_manifest_rejects_non_reverse_domain_ids(plugin_id: str) -> None:
    payload = manifest_payload()
    payload["id"] = plugin_id

    with pytest.raises(ValidationError):
        PluginManifest.model_validate(payload)


@pytest.mark.parametrize("version", ["1", "1.0", "v1.0.0"])
def test_plugin_manifest_rejects_non_semantic_versions(version: str) -> None:
    payload = manifest_payload()
    payload["version"] = version

    with pytest.raises(ValidationError):
        PluginManifest.model_validate(payload)


@pytest.mark.parametrize("entry", ["/bundle.mjs", "../bundle.mjs", "bundle.js"])
def test_plugin_manifest_rejects_unsafe_entry_paths(entry: str) -> None:
    payload = manifest_payload()
    payload["entry"] = entry

    with pytest.raises(ValidationError):
        PluginManifest.model_validate(payload)


def test_plugin_manifest_rejects_duplicate_component_types() -> None:
    payload = manifest_payload()
    component = payload["components"][0]  # type: ignore[index]
    payload["components"] = (component, component)

    with pytest.raises(ValidationError, match="component types must be unique"):
        PluginManifest.model_validate(payload)
