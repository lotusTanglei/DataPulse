import asyncio
import hashlib
import io
import json
import re
import shutil
import stat
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

from filelock import FileLock
from packaging.specifiers import SpecifierSet
from pydantic import ValidationError

from datapulse.contracts.dashboard import DashboardDocument
from datapulse.contracts.plugin import PluginManifest
from datapulse.ecosystem.models import CatalogPackage, PackageFile, TemplateManifest
from datapulse.errors import DataPulseError

MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
MAX_EXPANDED_BYTES = 50 * 1024 * 1024
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_FILES = 256
MAX_RATIO = 100
API_VERSION = "1.0.0"


def invalid(message: str, *, code: str = "ECOSYSTEM_INVALID_PACKAGE", status: int = 422):
    return DataPulseError(code=code, message=message, status_code=status)


def safe_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or len(value) > 240
        or path.is_absolute()
        or "\\" in value
        or ":" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or any(ord(char) < 32 for char in value)
        or str(path) != value
    ):
        raise invalid("Package paths must be canonical relative POSIX paths.")
    return value


def _json(data: bytes):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("Duplicate JSON keys are not allowed.")
            result[key] = value
        return result

    return json.loads(
        data,
        object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite JSON")),
    )


class EcosystemService:
    def __init__(self, *, root: Path, screen_service=None, session_factory=None):
        self.root = root
        self._screens = screen_service
        self._session_factory = session_factory
        self._packages = root / "packages"
        self._staging = root / ".staging"
        self._packages.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._staging.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._lock = FileLock(str(root / ".catalog.lock"))

    def _directory(self, kind: str, package_id: str, version: str) -> Path:
        try:
            if kind not in {"plugin", "template"}:
                raise ValueError("Invalid package kind")
            PluginManifest.validate_id(package_id)
            PluginManifest.validate_version(version)
        except ValueError as error:
            raise invalid(
                "Package does not exist.", code="ECOSYSTEM_NOT_FOUND", status=404
            ) from error
        return self._packages / kind / package_id / version

    def get(self, kind: str, package_id: str, version: str) -> CatalogPackage:
        directory = self._directory(kind, package_id, version)
        try:
            package = CatalogPackage.model_validate_json((directory / "record.json").read_bytes())
        except FileNotFoundError as error:
            raise invalid(
                "Package does not exist.", code="ECOSYSTEM_NOT_FOUND", status=404
            ) from error
        if (package.kind, package.id, package.version) != (kind, package_id, version):
            raise invalid(
                "Installed package metadata is corrupt.", code="ECOSYSTEM_CORRUPT", status=409
            )
        return package

    def list(self) -> tuple[CatalogPackage, ...]:
        with self._lock:
            return tuple(
                self.get(path.parts[-4], path.parts[-3], path.parts[-2])
                for path in sorted(self._packages.glob("*/*/*/record.json"))
            )

    def install(self, payload: bytes) -> CatalogPackage:
        if len(payload) > MAX_ARCHIVE_BYTES:
            raise invalid("Package exceeds upload size limit.", status=413)
        with self._lock, tempfile.TemporaryDirectory(dir=self._staging) as temporary:
            staging = Path(temporary)
            content = staging / "content"
            content.mkdir()
            try:
                files = self._extract(payload, content)
                manifest_data = _json((content / "manifest.json").read_bytes())
                if not isinstance(manifest_data, dict):
                    raise ValueError("Manifest must be an object.")
                kind = "template" if manifest_data.get("kind") == "template" else "plugin"
                model = TemplateManifest if kind == "template" else PluginManifest
                manifest = model.model_validate(manifest_data)
                if API_VERSION not in SpecifierSet(manifest.compatible_api):
                    raise ValueError("Package is incompatible with the host API.")
                if isinstance(manifest, PluginManifest):
                    if not (content / safe_path(manifest.entry)).is_file():
                        raise ValueError("Plugin entry does not exist.")
                    if any(c.type.startswith("builtin.") for c in manifest.components):
                        raise ValueError("Plugin cannot override a built-in component.")
                    self._validate_schemas(manifest)
                    self._check_component_collisions(manifest)
                else:
                    document = DashboardDocument.model_validate(
                        _json((content / manifest.document).read_bytes())
                    )
                    self._validate_template(manifest, document)
                    self.validate_document(document)
                package = CatalogPackage(
                    kind=kind,
                    id=manifest.id,
                    version=manifest.version,
                    name=manifest.name,
                    description=manifest.description,
                    license=manifest.license,
                    source=manifest.source,
                    compatible_api=manifest.compatible_api,
                    manifest=manifest,
                    sha256=hashlib.sha256(payload).hexdigest(),
                    installed_at=datetime.now(UTC),
                    files=files,
                )
            except (
                ValueError,
                ValidationError,
                KeyError,
                zipfile.BadZipFile,
                RuntimeError,
                FileNotFoundError,
                NotImplementedError,
            ) as error:
                raise invalid(f"Invalid package: {error}") from error
            destination = self._directory(kind, manifest.id, manifest.version)
            history = self.root / "history" / kind / manifest.id / f"{manifest.version}.json"
            if history.exists():
                previous = CatalogPackage.model_validate_json(history.read_bytes())
                if previous.sha256 != package.sha256:
                    raise invalid(
                        "An installed ID/version is immutable; install a new version.",
                        code="ECOSYSTEM_VERSION_CONFLICT",
                        status=409,
                    )
            if destination.exists():
                installed = self.get(kind, manifest.id, manifest.version)
                if installed.sha256 == package.sha256:
                    return installed
                raise invalid(
                    "An installed ID/version is immutable; install a new version.",
                    code="ECOSYSTEM_VERSION_CONFLICT",
                    status=409,
                )
            (staging / "record.json").write_text(package.model_dump_json(), encoding="utf-8")
            destination.parent.mkdir(parents=True, exist_ok=True)
            staging.rename(destination)
            return package

    def _extract(self, payload: bytes, content: Path) -> tuple[PackageFile, ...]:
        files = []
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = archive.infolist()
            if not members or len(members) > MAX_FILES:
                raise ValueError("Package contains too many files.")
            names = set()
            expanded = 0
            for member in members:
                # Packages contain files only; directory members are unnecessary and rejected.
                name = safe_path(member.filename)
                if name != member.orig_filename or name.casefold() in names:
                    raise ValueError("Duplicate or ambiguous archive member.")
                if any(
                    name.casefold().startswith(existing + "/")
                    or existing.startswith(name.casefold() + "/")
                    for existing in names
                ):
                    raise ValueError("Archive file and directory paths conflict.")
                names.add(name.casefold())
                mode = member.external_attr >> 16
                if stat.S_IFMT(mode) not in {0, stat.S_IFREG} or member.is_dir():
                    raise ValueError("Only regular files are supported.")
                if member.flag_bits & 1:
                    raise ValueError("Encrypted ZIP entries are not supported.")
                expanded += member.file_size
                if (
                    member.file_size > MAX_FILE_BYTES
                    or expanded > MAX_EXPANDED_BYTES
                    or member.file_size > max(1, member.compress_size) * MAX_RATIO
                ):
                    raise ValueError(
                        "Package exceeds file, expanded size, or compression ratio limit."
                    )
                target = content / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source:
                    data = source.read(MAX_FILE_BYTES + 1)
                if len(data) != member.file_size or len(data) > MAX_FILE_BYTES:
                    raise ValueError("Invalid ZIP member size.")
                target.write_bytes(data)
                files.append(
                    PackageFile(path=name, size=len(data), sha256=hashlib.sha256(data).hexdigest())
                )
        return tuple(sorted(files, key=lambda item: item.path))

    def _check_component_collisions(self, manifest: PluginManifest) -> None:
        offered = {component.type for component in manifest.components}
        for installed in self.list():
            if installed.kind != "plugin" or installed.id == manifest.id:
                continue
            if offered.intersection(component.type for component in installed.manifest.components):
                raise ValueError("Another plugin already owns this component type.")

    @staticmethod
    def _validate_schemas(manifest: PluginManifest) -> None:
        from jsonschema import Draft7Validator
        from jsonschema.exceptions import SchemaError
        from jsonschema.exceptions import ValidationError as SchemaValidationError

        from datapulse.ecosystem.schemas import check_plugin_schema

        for component in manifest.components:
            try:
                for schema in (component.property_schema, component.data_schema):
                    check_plugin_schema(schema)
                Draft7Validator(component.property_schema).validate(component.default_props)
            except (SchemaError, SchemaValidationError) as error:
                raise ValueError("Plugin schemas and default properties must be valid.") from error

    def _validate_template(self, manifest: TemplateManifest, document: DashboardDocument) -> None:
        # Reference and secret validation is shared with application below.
        payload = document.model_dump(mode="json")
        self._reject_secrets(payload)
        datasets, assets = self._references(payload)
        if datasets != set(manifest.datasets) or assets != set(manifest.assets):
            raise ValueError(
                "Template references must match explicitly declared datasets and assets."
            )

    @staticmethod
    def _reject_secrets(value) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                normalized = re.sub(r"[^a-z0-9]", "", key.lower())
                if normalized == "token" or any(
                    term in normalized
                    for term in (
                        "password",
                        "secret",
                        "credential",
                        "authorization",
                        "apikey",
                        "accesstoken",
                        "refreshtoken",
                        "privatekey",
                        "connectionstring",
                        "cookie",
                        "sessiontoken",
                    )
                ):
                    raise ValueError("Templates cannot contain credentials or secret fields.")
                EcosystemService._reject_secrets(item)
        elif isinstance(value, list):
            for item in value:
                EcosystemService._reject_secrets(item)
        elif isinstance(value, str) and re.search(
            r"(?:Bearer\s+\S+|-----BEGIN .*PRIVATE KEY-----|https?://[^/@\s]+:[^/@\s]+@"
            r"|[?&](?:api[_-]?key|token|access[_-]?token|secret|password|signature)=)",
            value,
            re.IGNORECASE,
        ):
            raise ValueError("Templates cannot contain embedded credentials.")

    @staticmethod
    def _references(value) -> tuple[set[str], set[str]]:
        datasets, assets = set(), set()

        def walk(item):
            if isinstance(item, dict):
                for key, child in item.items():
                    if isinstance(child, str) and child:
                        if key == "dataset_id":
                            datasets.add(child)
                        elif key == "asset_id" or key.endswith("_asset_id"):
                            assets.add(child)
                        elif key in {"datasource_id", "data_source_id"}:
                            raise ValueError(
                                "Templates must bind datasets, not raw datasource IDs."
                            )
                    walk(child)
            elif isinstance(item, list):
                for child in item:
                    walk(child)

        walk(value)
        return datasets, assets

    def publication_guard(self):
        """Serialize document writes and uninstall across processes.

        Callers must validate dependencies and write the document inside this guard.
        A fresh lock object per context prevents async tasks treating each other as reentrant.
        """
        from filelock import AsyncFileLock

        return AsyncFileLock(str(self.root / ".references.lock"), run_in_executor=True)

    async def uninstall(self, kind: str, package_id: str, version: str) -> None:
        from sqlalchemy import select

        from datapulse.metadata.models import ScreenRecord

        async with self.publication_guard():
            self.get(kind, package_id, version)
            if kind == "plugin":
                if self._session_factory is None:
                    raise invalid("Reference checks require the screen repository.", status=503)
                async with self._session_factory() as session:
                    records = await session.execute(
                        select(ScreenRecord.draft_document, ScreenRecord.published_document)
                    )
                    for draft, published in records:
                        for document in (draft, published):
                            if document and any(
                                item.get("id") == package_id and item.get("version") == version
                                for item in document.get("plugin_dependencies", [])
                            ):
                                raise invalid(
                                    "Package version is referenced by a screen.",
                                    code="ECOSYSTEM_IN_USE",
                                    status=409,
                                )
            # The template scan and removal share the install lock. Run blocking
            # filesystem work off the event loop while retaining the reference guard.
            removal = asyncio.create_task(
                asyncio.to_thread(self._remove_package, kind, package_id, version)
            )
            cancelled = False
            while True:
                try:
                    await asyncio.shield(removal)
                    break
                except asyncio.CancelledError:
                    # A cancelled request cannot abandon a worker that may still
                    # remove files after a publisher acquires the reference guard.
                    cancelled = True
            if cancelled:
                raise asyncio.CancelledError

    def _remove_package(self, kind: str, package_id: str, version: str) -> None:
        with self._lock:
            package = self.get(kind, package_id, version)
            if kind == "plugin":
                for installed in self.list():
                    if installed.kind != "template":
                        continue
                    document = _json(
                        self.file_path(
                            "template", installed.id, installed.version, "document.json"
                        ).read_bytes()
                    )
                    if any(
                        item.get("id") == package_id and item.get("version") == version
                        for item in document.get("plugin_dependencies", [])
                    ):
                        raise invalid(
                            "Package version is referenced by a template.",
                            code="ECOSYSTEM_IN_USE",
                            status=409,
                        )
            directory = self._directory(kind, package_id, version)
            # Preserve identity even after uninstall, so reinstall cannot change old content.
            history = self.root / "history" / kind / package_id
            history.mkdir(parents=True, exist_ok=True)
            (history / f"{version}.json").write_text(
                package.model_dump_json(), encoding="utf-8"
            )
            removed = self._staging / f"removed-{uuid4().hex}"
            directory.rename(removed)
            shutil.rmtree(removed)

    def file_path(self, kind: str, package_id: str, version: str, file_path: str) -> Path:
        package = self.get(kind, package_id, version)
        safe_path(file_path)
        record = next((item for item in package.files if item.path == file_path), None)
        if record is None:
            raise invalid("Package file does not exist.", code="ECOSYSTEM_NOT_FOUND", status=404)
        content = self._directory(kind, package_id, version) / "content"
        target = content / file_path
        if target.is_symlink() or not target.resolve().is_relative_to(content.resolve()):
            raise invalid(
                "Installed package content is corrupt.", code="ECOSYSTEM_CORRUPT", status=409
            )
        try:
            data = target.read_bytes()
        except FileNotFoundError as error:
            raise invalid(
                "Package file does not exist.", code="ECOSYSTEM_NOT_FOUND", status=404
            ) from error
        if len(data) != record.size or hashlib.sha256(data).hexdigest() != record.sha256:
            raise invalid(
                "Installed package content is corrupt.", code="ECOSYSTEM_CORRUPT", status=409
            )
        return target

    async def apply_template(
        self, package_id: str, version: str, payload, *, authorize_reference=None
    ):
        from sqlalchemy import select

        from datapulse.metadata.models import DatasetRecord, ScreenAssetRecord
        from datapulse.screen.models import ScreenCreate

        if self._screens is None:
            raise invalid("Screen creation is unavailable.", status=503)
        async with self.publication_guard():
            package = self.get("template", package_id, version)
            manifest = package.manifest
            if set(payload.dataset_mapping) != set(manifest.datasets) or set(
                payload.asset_mapping
            ) != set(manifest.assets):
                raise invalid("Explicit mapping is required for every dataset and asset reference.")
            for kind, mapping, model in (
                ("dataset", payload.dataset_mapping, DatasetRecord),
                ("asset", payload.asset_mapping, ScreenAssetRecord),
            ):
                for target in sorted(set(mapping.values())):
                    if authorize_reference is None:
                        raise invalid("Reference authorization is required.", status=403)
                    await authorize_reference(kind, target)
                    if self._session_factory is None:
                        raise invalid(
                            "Reference checks require the metadata repository.", status=503
                        )
                    async with self._session_factory() as session:
                        exists = await session.scalar(select(model.id).where(model.id == target))
                    if exists is None:
                        raise invalid("Mapped reference does not exist.")
            document = _json(
                self.file_path("template", package_id, version, manifest.document).read_bytes()
            )
            ids = {item["id"]: str(uuid4()) for item in document.get("components", [])}
            groups = {}

            def remap(item):
                if isinstance(item, dict):
                    result = {}
                    for key, value in item.items():
                        if key == "component_id" and isinstance(value, str):
                            if value not in ids:
                                raise invalid("Unknown template component reference.")
                            result[key] = ids[value]
                        elif key == "dataset_id" and value:
                            result[key] = payload.dataset_mapping[value]
                        elif (key == "asset_id" or key.endswith("_asset_id")) and value:
                            result[key] = payload.asset_mapping[value]
                        elif key == "group_id" and value:
                            result[key] = groups.setdefault(value, str(uuid4()))
                        else:
                            result[key] = remap(value)
                    return result
                if isinstance(item, list):
                    return [remap(value) for value in item]
                return item

            document = remap(document)
            for component in document.get("components", []):
                component["id"] = ids[component["id"]]
            validated = DashboardDocument.model_validate(document)
            self.validate_document(validated)
            return await self._screens.create(
                ScreenCreate(
                    name=payload.name, description=payload.description, draft_document=validated
                )
            )

    def validate_document(self, document: DashboardDocument) -> None:
        """Validate exact installed plugin versions and component properties."""
        from jsonschema import Draft7Validator
        from jsonschema.exceptions import ValidationError as SchemaValidationError

        owners = {}
        for dependency in getattr(document, "plugin_dependencies", ()):
            package = self.get("plugin", dependency.id, dependency.version)
            for component in package.manifest.components:
                if component.type in owners:
                    raise invalid("A component type resolves to multiple plugin versions.")
                owners[component.type] = component
        for component in document.components:
            if component.type.startswith("builtin."):
                continue
            definition = owners.get(component.type)
            if definition is None:
                raise invalid("Every plugin component requires an exact installed dependency.")
            try:
                Draft7Validator(definition.property_schema).validate(component.props)
            except SchemaValidationError as error:
                raise invalid("Plugin component properties do not match their schema.") from error

    def file_path_for_document(
        self, document: DashboardDocument, package_id: str, version: str, file_path: str
    ) -> Path:
        """Call only after authenticating the viewer and resolving its published document."""
        if not any(
            item.id == package_id and item.version == version
            for item in getattr(document, "plugin_dependencies", ())
        ):
            raise invalid(
                "Plugin version is not authorized for this document.",
                code="ECOSYSTEM_NOT_FOUND",
                status=404,
            )
        return self.file_path("plugin", package_id, version, file_path)
