import re
from pathlib import PurePosixPath
from typing import Literal, Self

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from pydantic import Field, field_validator, model_validator

from datapulse.contracts.common import ContractModel, JsonValue, NonBlankStr

_REVERSE_DOMAIN_ID = re.compile(r"^[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+$")
_SEMANTIC_VERSION = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


class PluginComponent(ContractModel):
    type: NonBlankStr
    name: NonBlankStr
    category: NonBlankStr
    property_schema: dict[str, JsonValue]
    data_schema: dict[str, JsonValue]
    default_props: dict[str, JsonValue] = Field(default_factory=dict)


class PluginManifest(ContractModel):
    schema_version: Literal[1] = 1
    id: NonBlankStr
    version: NonBlankStr
    compatible_api: NonBlankStr
    name: NonBlankStr
    description: str = ""
    license: NonBlankStr = "UNLICENSED"
    source: NonBlankStr = "local"
    entry: NonBlankStr
    components: tuple[PluginComponent, ...] = Field(min_length=1)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not _REVERSE_DOMAIN_ID.fullmatch(value):
            raise ValueError("plugin ID must use lowercase reverse-domain syntax")
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if not _SEMANTIC_VERSION.fullmatch(value):
            raise ValueError("version must use semantic version syntax")
        return value

    @field_validator("compatible_api")
    @classmethod
    def validate_compatible_api(cls, value: str) -> str:
        try:
            SpecifierSet(value)
        except InvalidSpecifier as error:
            raise ValueError("compatible_api must be a valid version specifier") from error
        return value

    @field_validator("entry")
    @classmethod
    def validate_entry(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or path.suffix != ".mjs"
            or "\\" in value
            or ":" in value
            or any(part in {"", ".", ".."} for part in value.split("/"))
            or any(ord(char) < 32 for char in value)
            or str(path) != value
        ):
            raise ValueError("entry must be a safe relative .mjs path")
        return value

    @model_validator(mode="after")
    def validate_unique_component_types(self) -> Self:
        component_types = [component.type for component in self.components]
        if len(component_types) != len(set(component_types)):
            raise ValueError("component types must be unique")
        return self
