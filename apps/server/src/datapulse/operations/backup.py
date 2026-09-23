"""Bounded SQLite backup archives; no generic directory extraction or overwrite."""

import base64
import hashlib
import hmac
import json
import os
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Literal

from alembic.config import Config
from alembic.script import ScriptDirectory
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.engine import make_url

from datapulse.contracts.dashboard import DashboardDocument
from datapulse.datasource.secrets import SecretBox, SecretEnvelope
from datapulse.ecosystem.models import CatalogPackage, TemplateManifest
from datapulse.metadata import Base, metadata_database_url
from datapulse.operations.maintenance import MaintenanceBusy, maintenance_lease
from datapulse.screen.assets import collect_asset_references
from datapulse.settings import Settings


class BackupError(ValueError):
    """A safe, non-secret operational diagnostic."""


@dataclass(frozen=True)
class ArchiveLimits:
    max_members: int = 20_000
    max_member_bytes: int = 1024**3
    max_total_bytes: int = 10 * 1024**3
    max_archive_bytes: int = 10 * 1024**3
    max_compression_ratio: int = 200


DEFAULT_LIMITS = ArchiveLimits()


class ArchiveMember(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    path: str
    size: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class BackupManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1] = 1
    app_version: str
    alembic_revision: str
    created_at: str
    master_key_required: bool
    master_key_fingerprint: str | None
    member_count: int = Field(ge=1)
    total_bytes: int = Field(ge=0)
    members: list[ArchiveMember]


def _safe_name(name: str) -> str:
    parts = name.split("/")
    if (
        not name
        or "\\" in name
        or ":" in name
        or any(ord(char) < 32 or ord(char) == 127 for char in name)
        or any(part in ("", ".", "..") for part in parts)
        or PurePosixPath(name).is_absolute()
    ):
        raise BackupError("Archive member path is unsafe.")
    return name


def _regular_file(path: Path, root: Path | None = None) -> Path:
    # Resolve only after inspecting each lexical component: resolving first
    # would silently accept links that point back inside a managed root.
    absolute = path.absolute()
    for component in (absolute, *absolute.parents):
        if component.is_symlink():
            raise BackupError("A symbolic link is not a supported backup source.")
    if not absolute.is_file():
        raise BackupError("A referenced backup file is missing or is not regular.")
    if not stat.S_ISREG(absolute.stat().st_mode):
        raise BackupError("A backup source is not a regular file.")
    resolved = absolute.resolve()
    if root is not None and not resolved.is_relative_to(root.resolve()):
        raise BackupError("A referenced file escapes its configured storage root.")
    return resolved


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _revision() -> str:
    config = Config()
    config.set_main_option(
        "script_location", str(Path(__file__).resolve().parents[3] / "migrations")
    )
    heads = ScriptDirectory.from_config(config).get_heads()
    if len(heads) != 1:
        raise BackupError("Backup requires one installed Alembic schema head.")
    return heads[0]


def _sqlite_path(settings: Settings) -> Path:
    url = make_url(metadata_database_url(settings))
    if url.get_backend_name() != "sqlite":
        raise BackupError(
            "Automatic backup supports SQLite only; use the PostgreSQL maintenance runbook."
        )
    if not url.database or url.database == ":memory:" or url.query:
        raise BackupError("Backup requires a regular SQLite database file without URI options.")
    return _regular_file(Path(url.database))


@contextmanager
def _database(path: Path, *, writable: bool = False) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(f"{path.as_uri()}?mode={'rw' if writable else 'ro'}", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA trusted_schema=OFF")
    connection.execute("PRAGMA foreign_keys=ON")
    if not writable:
        connection.execute("PRAGMA query_only=ON")
    try:
        yield connection
        if writable:
            connection.commit()
    finally:
        connection.close()


def _validate_database(connection: sqlite3.Connection, revision: str) -> None:
    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise BackupError("SQLite database integrity check failed.")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise BackupError("SQLite database has missing foreign key references.")
    if connection.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('view','trigger')"
    ).fetchone():
        raise BackupError("Unexpected SQLite schema objects in backup.")
    tables = {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    expected = set(Base.metadata.tables) | {"alembic_version"}
    if tables - {"sqlite_sequence"} != expected:
        raise BackupError("SQLite schema tables do not match the installed application.")
    for table in Base.metadata.sorted_tables:
        columns = {row[1] for row in connection.execute(f'PRAGMA table_info("{table.name}")')}
        if columns != set(table.columns.keys()):
            raise BackupError("SQLite schema columns do not match the installed application.")
    versions = [row[0] for row in connection.execute("SELECT version_num FROM alembic_version")]
    if versions != [revision] or revision != _revision():
        raise BackupError(
            "SQLite Alembic version is incompatible; restore with the matching release."
        )


def _has_secrets(connection: sqlite3.Connection) -> bool:
    return any(
        connection.execute(
            f"SELECT 1 FROM {table} WHERE secret_envelope IS NOT NULL LIMIT 1"
        ).fetchone()
        for table in ("data_source", "digital_human_provider")
    )


def _key_fingerprint(key: str | None) -> str:
    if not key:
        raise BackupError("The original master key is required for encrypted credentials.")
    try:
        SecretBox(key)
        decoded = base64.urlsafe_b64decode(key + "=" * (-len(key) % 4))
    except ValueError as error:
        raise BackupError("The configured master key is invalid.") from error
    return hmac.new(decoded, b"datapulse:backup:master-key:v1", hashlib.sha256).hexdigest()


def _validate_secrets(connection: sqlite3.Connection, key: str | None) -> None:
    if not _has_secrets(connection):
        return
    _key_fingerprint(key)
    box = SecretBox(key)  # type: ignore[arg-type]
    try:
        for row in connection.execute(
            "SELECT id, secret_envelope FROM data_source WHERE secret_envelope IS NOT NULL"
        ):
            box.decrypt(row["id"], SecretEnvelope.model_validate_json(row["secret_envelope"]))
        for row in connection.execute(
            "SELECT id, secret_envelope FROM digital_human_provider "
            "WHERE secret_envelope IS NOT NULL"
        ):
            box.decrypt_for(
                row["id"], "tts-api-key", SecretEnvelope.model_validate_json(row["secret_envelope"])
            )
    except ValueError as error:
        raise BackupError(
            "Credential ciphertext cannot be decrypted with the supplied master key."
        ) from error


def _copy_file(source: Path, stage: Path, member: str, limits: ArchiveLimits) -> None:
    _safe_name(member)
    destination = stage / member
    if destination.exists():
        if _digest(source) != _digest(destination):
            raise BackupError("Conflicting files share a backup member path.")
        return
    if source.stat().st_size > limits.max_member_bytes:
        raise BackupError("Backup member size limit exceeded.")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with source.open("rb") as incoming, destination.open("xb") as outgoing:
        os.chmod(destination, 0o600)
        shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)


def _snapshot(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with _database(source) as incoming, sqlite3.connect(destination) as outgoing:
        incoming.backup(outgoing)
    os.chmod(destination, 0o600)


def _normalize_files(
    connection: sqlite3.Connection, settings: Settings, stage: Path, limits: ArchiveLimits
) -> None:
    roots = {
        "file_asset": ("files", settings.resolved_files_dir()),
        "screen_asset": ("assets", settings.resolved_assets_dir()),
    }
    for table, (prefix, root) in roots.items():
        columns = (
            ("storage_path", "thumbnail_path") if table == "screen_asset" else ("storage_path",)
        )
        for row in connection.execute(f"SELECT * FROM {table}").fetchall():
            for column in columns:
                if not row[column]:
                    continue
                source = _regular_file(Path(row[column]), root)
                member = f"{prefix}/{source.relative_to(root).as_posix()}"
                if column == "storage_path" and (
                    _digest(source) != row["sha256"] or source.stat().st_size != row["size_bytes"]
                ):
                    raise BackupError("Referenced file metadata checksum or size does not match.")
                _copy_file(source, stage, member, limits)
                connection.execute(f"UPDATE {table} SET {column}=? WHERE id=?", (member, row["id"]))
    root = settings.resolved_sources_dir()
    for row in connection.execute(
        "SELECT id, config_json FROM data_source WHERE connector_type='sqlite'"
    ).fetchall():
        config = json.loads(row["config_json"])
        source = _regular_file(root / config["path"], root)
        # Native snapshot also folds any source database WAL into the copy.
        member = f"sources/{hashlib.sha256(row['id'].encode()).hexdigest()}.db"
        _snapshot(source, stage / member)
        config["path"] = member.removeprefix("sources/")
        connection.execute(
            "UPDATE data_source SET config_json=? WHERE id=?", (json.dumps(config), row["id"])
        )


def _json(data: bytes) -> object:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise BackupError("Duplicate JSON field in backup metadata.")
            result[key] = value
        return result

    return json.loads(data, object_pairs_hook=unique)


def _package_files(root: Path) -> set[str]:
    """Only package records and their declared content; never .staging or locks."""
    expected: set[str] = set()
    plugins: set[tuple[str, str]] = set()
    templates: list[DashboardDocument] = []
    if not root.exists():
        return expected
    if root.is_symlink() or any(path.is_symlink() for path in root.rglob("*")):
        raise BackupError("A symbolic link is not a supported ecosystem package entry.")
    for record_path in root.glob("*/*/*/record.json"):
        _regular_file(record_path, root)
        record = _json(record_path.read_bytes())
        if not isinstance(record, dict) or not isinstance(record.get("files"), list):
            raise BackupError("Ecosystem package record is invalid.")
        relative = record_path.parent.relative_to(root).as_posix()
        package = CatalogPackage.model_validate(record)
        if relative != f"{package.kind}/{package.id}/{package.version}":
            raise BackupError("Ecosystem package identity does not match its storage path.")
        expected.add(f"{relative}/record.json")
        declared = set()
        for item in record["files"]:
            if not isinstance(item, dict):
                raise BackupError("Ecosystem package file declaration is invalid.")
            name = _safe_name(item.get("path", item.get("name", "")))
            if name in declared:
                raise BackupError("Duplicate ecosystem package file declaration.")
            declared.add(name)
            path = _regular_file(record_path.parent / "content" / name, root)
            if _digest(path) != item.get("sha256") or path.stat().st_size != item.get(
                "size", item.get("size_bytes")
            ):
                raise BackupError("Ecosystem package file checksum or size mismatch.")
            expected.add(f"{relative}/content/{name}")
        if "manifest.json" not in declared:
            raise BackupError("Ecosystem package manifest is missing from declared files.")
        content_manifest = _json((record_path.parent / "content/manifest.json").read_bytes())
        validated_manifest = type(package.manifest).model_validate(content_manifest)
        if validated_manifest != package.manifest:
            raise BackupError("Ecosystem package manifest disagrees with its catalog record.")
        if package.kind == "plugin":
            plugins.add((package.id, package.version))
        else:
            if not isinstance(package.manifest, TemplateManifest):
                raise BackupError("Template package manifest is invalid.")
            document_name = package.manifest.document
            if document_name not in declared:
                raise BackupError("Template document is missing from declared files.")
            try:
                templates.append(
                    DashboardDocument.model_validate(
                        _json((record_path.parent / "content" / document_name).read_bytes())
                    )
                )
            except ValueError as error:
                raise BackupError("Template document is invalid.") from error
    for document in templates:
        for dependency in document.plugin_dependencies:
            if (dependency.id, dependency.version) not in plugins:
                raise BackupError("Template references a missing exact plugin dependency.")
    # Fail on unknown installed entries instead of silently omitting a version.
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if not path.is_dir()}
    if actual != expected:
        raise BackupError("Unexpected or incomplete ecosystem package files.")
    return expected


def _history_files(root: Path) -> set[str]:
    expected: set[str] = set()
    if not root.exists():
        return expected
    for path in root.rglob("*"):
        if path.is_symlink():
            raise BackupError("A symbolic link is not a supported ecosystem history entry.")
        if path.is_dir():
            continue
        _regular_file(path, root)
        package = CatalogPackage.model_validate(_json(path.read_bytes()))
        relative = path.relative_to(root).as_posix()
        if relative != f"{package.kind}/{package.id}/{package.version}.json":
            raise BackupError("Ecosystem history identity does not match its storage path.")
        expected.add(relative)
    return expected


def _references(connection: sqlite3.Connection, stage: Path) -> set[str]:
    expected = {"datapulse.db"}
    for table, prefix in (("file_asset", "files/"), ("screen_asset", "assets/")):
        for row in connection.execute(f"SELECT * FROM {table}"):
            columns = (
                ("storage_path", "thumbnail_path") if table == "screen_asset" else ("storage_path",)
            )
            for column in columns:
                if not row[column]:
                    continue
                member = _safe_name(row[column])
                if not member.startswith(prefix):
                    raise BackupError("Database file reference escapes its managed root.")
                path = _regular_file(stage / member, stage)
                if column == "storage_path" and (
                    _digest(path) != row["sha256"] or path.stat().st_size != row["size_bytes"]
                ):
                    raise BackupError("Database file reference checksum mismatch.")
                expected.add(member)
    for row in connection.execute(
        "SELECT config_json FROM data_source WHERE connector_type='sqlite'"
    ):
        member = "sources/" + _safe_name(json.loads(row[0])["path"])
        path = _regular_file(stage / member, stage / "sources")
        with _database(path) as source:
            if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise BackupError("SQLite source integrity check failed.")
        expected.add(member)
    file_ids = {row[0] for row in connection.execute("SELECT id FROM file_asset")}
    asset_ids = {row[0] for row in connection.execute("SELECT id FROM screen_asset")}
    dataset_ids = {row[0] for row in connection.execute("SELECT id FROM dataset")}
    for row in connection.execute("SELECT definition_json FROM dataset"):
        definition = json.loads(row[0])
        query = definition.get("query", {})
        if query.get("kind") == "file" and query.get("asset_id") not in file_ids:
            raise BackupError("Dataset references a missing file asset.")
    for row in connection.execute("SELECT draft_document, published_document FROM screen"):
        for value in row:
            if value is None or value == "null":
                continue
            document = DashboardDocument.model_validate_json(value)
            for dependency in document.plugin_dependencies:
                record = (
                    stage
                    / "ecosystem/packages/plugin"
                    / dependency.id
                    / dependency.version
                    / "record.json"
                )
                if not record.is_file():
                    raise BackupError("Screen references a missing plugin dependency.")
            if collect_asset_references(document.model_dump(mode="json")) - asset_ids:
                raise BackupError("Screen references a missing media asset.")
            for component in document.components:
                bindings = [component.data_binding]
                chart_spec = component.data_binding.get("chart_spec")
                if isinstance(chart_spec, dict):
                    bindings.append(chart_spec)
                for binding in bindings:
                    dataset_id = binding.get("dataset_id")
                    if dataset_id and (
                        not isinstance(dataset_id, str) or dataset_id not in dataset_ids
                    ):
                        raise BackupError("Screen references a missing dataset.")
    for row in connection.execute("SELECT asset_id FROM speech_task WHERE asset_id != ''"):
        if row[0] not in asset_ids:
            raise BackupError("Speech task references a missing media asset.")
    expected.update(
        f"ecosystem/packages/{name}" for name in _package_files(stage / "ecosystem/packages")
    )
    expected.update(
        f"ecosystem/history/{name}" for name in _history_files(stage / "ecosystem/history")
    )
    return expected


def create_backup(
    settings: Settings,
    archive: Path,
    *,
    maintenance: bool = False,
    include_external_paths: bool = False,
    limits: ArchiveLimits = DEFAULT_LIMITS,
) -> BackupManifest:
    if not maintenance:
        raise BackupError("Explicit offline maintenance acknowledgement is required.")
    archive = archive.absolute()
    if archive.exists() or archive.is_symlink():
        raise BackupError("Backup archive already exists.")
    database = _sqlite_path(settings)
    roots = [
        database,
        settings.resolved_assets_dir(),
        settings.resolved_files_dir(),
        settings.resolved_sources_dir(),
    ]
    if not include_external_paths and any(
        not path.is_relative_to(settings.data_dir.resolve()) for path in roots
    ):
        raise BackupError("Configured external paths require --include-external-paths.")
    try:
        with (
            maintenance_lease(settings.data_dir),
            tempfile.TemporaryDirectory(prefix="datapulse-backup-") as temporary,
        ):
            stage = Path(temporary).resolve()
            _snapshot(database, stage / "datapulse.db")
            with _database(stage / "datapulse.db", writable=True) as connection:
                revision = _revision()
                _validate_database(connection, revision)
                required = _has_secrets(connection)
                fingerprint = _key_fingerprint(settings.master_key) if required else None
                _validate_secrets(connection, settings.master_key)
                _normalize_files(connection, settings, stage, limits)
                # Completed speech task assets are disposable cache entries.
                # Normal media deletion retains the source task history; clear
                # only stale terminal cache pointers in the private snapshot.
                connection.execute(
                    "UPDATE speech_task SET asset_id='' "
                    "WHERE status IN ('succeeded', 'failed', 'cancelled') "
                    "AND asset_id != '' AND asset_id NOT IN (SELECT id FROM screen_asset)"
                )
            packages = settings.data_dir / "ecosystem" / "packages"
            for name in _package_files(packages):
                _copy_file(
                    _regular_file(packages / name, packages),
                    stage,
                    f"ecosystem/packages/{name}",
                    limits,
                )
            history = settings.data_dir / "ecosystem" / "history"
            for name in _history_files(history):
                _copy_file(
                    _regular_file(history / name, history),
                    stage,
                    f"ecosystem/history/{name}",
                    limits,
                )
            with _database(stage / "datapulse.db") as connection:
                names = _references(connection, stage)
            members = [
                ArchiveMember(
                    path=name, size=(stage / name).stat().st_size, sha256=_digest(stage / name)
                )
                for name in sorted(names)
            ]
            if (
                len(members) + 1 > limits.max_members
                or any(m.size > limits.max_member_bytes for m in members)
                or sum(m.size for m in members) > limits.max_total_bytes
            ):
                raise BackupError("Backup size or member count limit exceeded.")
            manifest = BackupManifest(
                app_version=settings.app_version,
                alembic_revision=revision,
                created_at=datetime.now(UTC).isoformat(),
                master_key_required=required,
                master_key_fingerprint=fingerprint,
                member_count=len(members),
                total_bytes=sum(member.size for member in members),
                members=members,
            )
            # Build beside the destination, then link without overwriting an existing file.
            descriptor, temporary_archive = tempfile.mkstemp(
                prefix=".datapulse-backup-", dir=archive.parent
            )
            os.close(descriptor)
            try:
                with zipfile.ZipFile(
                    temporary_archive, "w", compression=zipfile.ZIP_STORED
                ) as zipped:
                    zipped.writestr("manifest.json", manifest.model_dump_json())
                    for member in members:
                        zipped.write(stage / member.path, member.path)
                if Path(temporary_archive).stat().st_size > limits.max_archive_bytes:
                    raise BackupError("Backup archive size limit exceeded.")
                with open(temporary_archive, "rb") as stream:
                    os.fsync(stream.fileno())
                os.link(temporary_archive, archive)
            finally:
                Path(temporary_archive).unlink(missing_ok=True)
            return manifest
    except (sqlite3.Error, OSError, ValueError, MaintenanceBusy) as error:
        if isinstance(error, BackupError):
            raise
        if isinstance(error, MaintenanceBusy):
            raise BackupError(str(error)) from error
        raise BackupError(
            "Backup failed; check database integrity and managed file availability."
        ) from error


@contextmanager
def _verified_archive(
    archive: Path, *, app_version: str, limits: ArchiveLimits
) -> Iterator[tuple[BackupManifest, Path]]:
    try:
        _regular_file(archive)
        if archive.stat().st_size > limits.max_archive_bytes:
            raise BackupError("Archive size limit exceeded.")
        with zipfile.ZipFile(archive) as zipped:
            infos = zipped.infolist()
            if len(infos) > limits.max_members:
                raise BackupError("Archive member count limit exceeded.")
            names = set()
            total = 0
            for info in infos:
                name = _safe_name(info.filename)
                if name in names:
                    raise BackupError("Duplicate archive member.")
                names.add(name)
                mode = info.external_attr >> 16
                if (
                    info.is_dir()
                    or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
                    or info.flag_bits & 1
                ):
                    raise BackupError(
                        "Archive member must be an unencrypted regular file, never a symlink."
                    )
                total += info.file_size
                if (
                    info.file_size > limits.max_member_bytes
                    or total > limits.max_total_bytes
                    or info.file_size > max(1, info.compress_size) * limits.max_compression_ratio
                ):
                    raise BackupError("Archive expansion size or compression ratio limit exceeded.")
            if (
                "manifest.json" not in names
                or zipped.getinfo("manifest.json").file_size > 4 * 1024**2
            ):
                raise BackupError("Backup manifest is missing or exceeds its size limit.")
            manifest = BackupManifest.model_validate(_json(zipped.read("manifest.json")))
            expected = {member.path for member in manifest.members}
            if (
                len(expected) != len(manifest.members)
                or names != expected | {"manifest.json"}
                or "manifest.json" in expected
                or "datapulse.db" not in expected
                or manifest.member_count != len(manifest.members)
                or manifest.total_bytes != sum(member.size for member in manifest.members)
            ):
                raise BackupError("Unexpected, missing or duplicate manifest members.")
            if manifest.app_version != app_version or manifest.alembic_revision != _revision():
                raise BackupError(
                    "Backup application or schema version is incompatible; "
                    "use the matching release."
                )
            if manifest.master_key_required != bool(manifest.master_key_fingerprint):
                raise BackupError("Backup master key dependency metadata is invalid.")
            # Stream hashes before any member is written to disk.
            for member in manifest.members:
                _safe_name(member.path)
                if zipped.getinfo(member.path).file_size != member.size:
                    raise BackupError("Archive member size mismatch.")
                with zipped.open(member.path) as stream:
                    if hashlib.file_digest(stream, "sha256").hexdigest() != member.sha256:
                        raise BackupError("Archive member checksum mismatch.")
            with tempfile.TemporaryDirectory(prefix="datapulse-verify-") as temporary:
                stage = Path(temporary).resolve()
                for member in manifest.members:
                    path = stage / member.path
                    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    with zipped.open(member.path) as incoming, path.open("xb") as outgoing:
                        os.chmod(path, 0o600)
                        shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)
                with _database(stage / "datapulse.db") as connection:
                    _validate_database(connection, manifest.alembic_revision)
                    if _has_secrets(connection) != manifest.master_key_required:
                        raise BackupError(
                            "Backup encryption dependencies do not match the database."
                        )
                    if _references(connection, stage) != expected:
                        raise BackupError("Archive contains unreferenced or missing managed files.")
                yield manifest, stage
    except (
        OSError,
        sqlite3.Error,
        ValueError,
        KeyError,
        TypeError,
        zipfile.BadZipFile,
        RuntimeError,
    ) as error:
        if isinstance(error, BackupError):
            raise
        raise BackupError("Backup archive is invalid or corrupted.") from error


def verify_backup(
    archive: Path, *, app_version: str = "0.1.0", limits: ArchiveLimits = DEFAULT_LIMITS
) -> BackupManifest:
    with _verified_archive(archive, app_version=app_version, limits=limits) as (manifest, _):
        return manifest


def inspect_backup(archive: Path, **kwargs) -> BackupManifest:
    """Inspection verifies first so corrupt metadata is never presented as trusted."""
    return verify_backup(archive, **kwargs)


def restore_backup(
    archive: Path,
    target: Path,
    *,
    master_key: str | None = None,
    maintenance: bool = False,
    app_version: str = "0.1.0",
    limits: ArchiveLimits = DEFAULT_LIMITS,
) -> BackupManifest:
    if not maintenance:
        raise BackupError("Explicit offline maintenance acknowledgement is required.")
    target = target.absolute()
    if target.is_symlink() or any(parent.is_symlink() for parent in target.parents):
        raise BackupError("Restore target may not contain symbolic links.")
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise BackupError("Restore target must be an empty or nonexistent directory.")
    if not target.parent.is_dir():
        raise BackupError("Restore target parent directory must exist.")
    with _verified_archive(archive, app_version=app_version, limits=limits) as (manifest, verified):
        if manifest.master_key_required and not hmac.compare_digest(
            _key_fingerprint(master_key), manifest.master_key_fingerprint or ""
        ):
            raise BackupError("The supplied master key does not match the backup.")
        stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.restore-", dir=target.parent))
        try:
            shutil.copytree(verified, stage, dirs_exist_ok=True)
            with _database(stage / "datapulse.db", writable=True) as connection:
                _validate_secrets(connection, master_key)
                for table in ("file_asset", "screen_asset"):
                    columns = (
                        ("storage_path", "thumbnail_path")
                        if table == "screen_asset"
                        else ("storage_path",)
                    )
                    for column in columns:
                        for row in connection.execute(
                            f"SELECT id, {column} FROM {table}"
                        ).fetchall():
                            if row[column]:
                                connection.execute(
                                    f"UPDATE {table} SET {column}=? WHERE id=?",
                                    (str(target / row[column]), row["id"]),
                                )
                for table in ("admin_session", "display_access", "embed_access"):
                    connection.execute(f"DELETE FROM {table}")
                connection.execute(
                    "UPDATE system_state SET setup_code_hash=NULL, setup_code_expires_at=NULL"
                )
                connection.execute(
                    "UPDATE speech_task SET status='failed', error_code='SPEECH_TASK_INTERRUPTED', "
                    "finished_at=?, lease_owner=NULL, lease_expires_at=NULL, "
                    "reserved_audio_seconds=0, quota_period=NULL "
                    "WHERE status IN ('queued', 'running')",
                    (datetime.now(UTC).isoformat(),),
                )
                _validate_database(connection, manifest.alembic_revision)
            for root in ("files", "assets", "sources", "ecosystem/packages"):
                (stage / root).mkdir(parents=True, exist_ok=True, mode=0o700)
            # Same-filesystem rename atomically installs the complete tree. It
            # refuses a destination that became nonempty during verification.
            os.rename(stage, target)
        except (sqlite3.Error, OSError, ValueError) as error:
            if isinstance(error, BackupError):
                raise
            raise BackupError(
                "Restore failed before finalization; target data was preserved."
            ) from error
        finally:
            if stage.exists():
                shutil.rmtree(stage)
        return manifest
