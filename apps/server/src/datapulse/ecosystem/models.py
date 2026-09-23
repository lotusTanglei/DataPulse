from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from datapulse.contracts.common import ContractModel, NonBlankStr
from datapulse.contracts.plugin import PluginManifest

PackageKind = Literal["plugin", "template"]


class TemplateManifest(ContractModel):
    kind: Literal["template"] = "template"
    schema_version: Literal[1] = 1
    id: NonBlankStr
    version: NonBlankStr
    compatible_api: NonBlankStr
    name: NonBlankStr
    description: str = ""
    license: NonBlankStr = "UNLICENSED"
    source: NonBlankStr = "local"
    document: Literal["document.json"] = "document.json"
    datasets: tuple[NonBlankStr, ...] = ()
    assets: tuple[NonBlankStr, ...] = ()

    _id = field_validator("id")(PluginManifest.validate_id.__func__)
    _version = field_validator("version")(PluginManifest.validate_version.__func__)
    _api = field_validator("compatible_api")(PluginManifest.validate_compatible_api.__func__)

    @field_validator("datasets", "assets")
    @classmethod
    def unique_references(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("Template references must be unique.")
        return value


class PackageFile(ContractModel):
    path: NonBlankStr
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    size: int = Field(ge=0)


class CatalogPackage(ContractModel):
    kind: PackageKind
    id: NonBlankStr
    version: NonBlankStr
    name: NonBlankStr
    description: str
    license: NonBlankStr
    source: NonBlankStr
    compatible_api: NonBlankStr
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    installed_at: datetime
    manifest: PluginManifest | TemplateManifest
    files: tuple[PackageFile, ...]


class TemplateApply(ContractModel):
    name: NonBlankStr
    description: str = ""
    dataset_mapping: dict[str, NonBlankStr] = Field(default_factory=dict)
    asset_mapping: dict[str, NonBlankStr] = Field(default_factory=dict)
