from collections.abc import Mapping
from typing import Any

CURRENT_SCHEMA_VERSION = 1
CURRENT_COMPONENT_CONTRACT_VERSION = "1.0.0"


def _migrate_payload(value: Any, *, kind: str) -> Any:
    if not isinstance(value, Mapping):
        return value
    payload = dict(value)
    version = payload.get("schema_version", 0)
    if version == 0:
        payload["schema_version"] = CURRENT_SCHEMA_VERSION
        return payload
    if version != CURRENT_SCHEMA_VERSION:
        raise ValueError(f"Unsupported {kind} schema version: {version}")
    return payload


def migrate_component_payload(value: Any) -> Any:
    payload = _migrate_payload(value, kind="component")
    if not isinstance(payload, Mapping):
        return payload
    migrated = dict(payload)
    contract_version = migrated.get("contract_version", CURRENT_COMPONENT_CONTRACT_VERSION)
    if contract_version != CURRENT_COMPONENT_CONTRACT_VERSION:
        raise ValueError(f"Unsupported component contract version: {contract_version}")
    migrated["contract_version"] = CURRENT_COMPONENT_CONTRACT_VERSION
    return migrated


def migrate_dashboard_document_payload(value: Any) -> Any:
    return _migrate_payload(value, kind="dashboard document")


__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "CURRENT_COMPONENT_CONTRACT_VERSION",
    "migrate_component_payload",
    "migrate_dashboard_document_payload",
]
