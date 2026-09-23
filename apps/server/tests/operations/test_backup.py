import asyncio
import base64
import hashlib
import io
import json
import sqlite3
import stat
import zipfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from datapulse.datasource.secrets import SecretBox, SecretEnvelope
from datapulse.metadata.models import (
    AdminAccount,
    AdminSession,
    DatasetRecord,
    DataSourceRecord,
    DisplayAccessRecord,
    EmbedAccessRecord,
    FileAssetRecord,
    ScreenAssetRecord,
    ScreenRecord,
    SpeechPlanRecord,
    SpeechTaskRecord,
    SystemState,
    utc_now,
)
from datapulse.settings import Settings

MASTER_KEY = base64.urlsafe_b64encode(b"m" * 32).decode()
SERVER_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def source(tmp_path, monkeypatch):
    monkeypatch.delenv("DATAPULSE_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATAPULSE_DATA_DIR", raising=False)
    root = tmp_path / "source"
    root.mkdir()
    database = root / "datapulse.db"
    config = Config(str(SERVER_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "head")
    for name in ("files", "assets", "sources"):
        (root / name).mkdir()
    csv = root / "files" / "sales.csv"
    csv.write_text("region,amount\nEast,12\nWest,9\n")
    media = root / "assets" / "poster.png"
    from PIL import Image

    Image.new("RGB", (4, 4), "red").save(media)
    thumbnail = root / "assets" / "poster.preview.png"
    thumbnail.write_bytes(media.read_bytes())
    with sqlite3.connect(root / "sources" / "metrics.db") as connection:
        connection.execute("CREATE TABLE metrics (amount INTEGER)")
        connection.execute("INSERT INTO metrics VALUES (21)")
    document = {
        "schema_version": 1,
        "canvas": {"width": 1920, "height": 1080},
        "components": [
            {
                "id": "image",
                "type": "builtin.image",
                "frame": {"x": 0, "y": 0, "width": 100, "height": 100},
                "props": {"asset_id": "poster"},
            }
        ],
    }
    now = utc_now()
    engine = create_engine(f"sqlite:///{database}")
    with Session(engine) as session, session.begin():
        session.add(AdminAccount(id="admin", username="admin", password_hash="hash"))
        session.flush()
        session.add(
            AdminSession(
                id="old-session", admin_id="admin", csrf_token_hash="old-csrf", expires_at=now
            )
        )
        session.add(SystemState(id=1, setup_code_hash="old-setup", setup_code_expires_at=now))
        session.add(
            DataSourceRecord(
                id="metrics",
                name="Metrics",
                connector_type="sqlite",
                config_json={"type": "sqlite", "path": "metrics.db"},
                secret_envelope=SecretBox(MASTER_KEY)
                .encrypt("metrics", "secret")
                .model_dump_json(),
            )
        )
        session.add(
            FileAssetRecord(
                id="sales",
                original_name="sales.csv",
                format="csv",
                mime_type="text/csv",
                sha256=hashlib.sha256(csv.read_bytes()).hexdigest(),
                size_bytes=csv.stat().st_size,
                storage_path=str(csv),
                row_count=2,
                fields_json=[],
            )
        )
        session.add(
            ScreenAssetRecord(
                id="poster",
                family_id="poster",
                asset_type="image",
                mime_type="image/png",
                sha256=hashlib.sha256(media.read_bytes()).hexdigest(),
                size_bytes=media.stat().st_size,
                storage_path=str(media),
                thumbnail_path=str(thumbnail),
            )
        )
        session.add(
            ScreenRecord(
                id="screen",
                name="Operations",
                draft_document=document,
                published_document=document,
                published_at=now,
            )
        )
        session.flush()
        session.add(
            DatasetRecord(
                id="sales",
                name="Sales",
                definition_json={
                    "id": "sales",
                    "name": "Sales",
                    "query": {"kind": "file", "asset_id": "sales", "format": "csv"},
                },
            )
        )
        session.add(DisplayAccessRecord(screen_id="screen", key_hash="old-display"))
        session.add(EmbedAccessRecord(id=1, api_key_hash="old-embed"))
    engine.dispose()
    (root / ".env").write_text("TOP_SECRET=not-in-backup")
    (root / "secret.key").write_text(MASTER_KEY)
    (root / "files" / "orphan.log").write_text("private log")
    return Settings(data_dir=root, master_key=MASTER_KEY)


def create_archive(source, tmp_path):
    from datapulse.operations.backup import create_backup

    archive = tmp_path / "backup.zip"
    create_backup(source, archive, maintenance=True)
    return archive


@pytest.mark.parametrize("status", ["succeeded", "failed", "cancelled", "running"])
def test_backup_detaches_deleted_terminal_speech_cache_only_in_snapshot(source, tmp_path, status):
    from datapulse.metadata import create_metadata_engine, create_session_factory
    from datapulse.operations.backup import (
        BackupError,
        create_backup,
        restore_backup,
        verify_backup,
    )
    from datapulse.screen.assets import ScreenAssetRepository

    engine = create_engine(f"sqlite:///{source.data_dir / 'datapulse.db'}")
    with Session(engine) as session, session.begin():
        session.add(SpeechPlanRecord(
            id="plan", screen_id="screen", component_id="speaker", text="Hello",
            language="en", content_hash="f" * 64,
        ))
        session.add(SpeechTaskRecord(
            id="finished", plan_id="plan", status=status, asset_id="poster",
            finished_at=utc_now(),
        ))
    engine.dispose()
    create_backup(source, tmp_path / "with-cache.zip", maintenance=True)
    with sqlite3.connect(source.data_dir / "datapulse.db") as connection:
        document = json.loads(connection.execute("SELECT draft_document FROM screen").fetchone()[0])
        document["components"] = []
        connection.execute(
            "UPDATE screen SET draft_document=?, published_document=?",
            (json.dumps(document), json.dumps(document)),
        )

    async def delete_asset():
        engine = create_metadata_engine(source)
        try:
            await ScreenAssetRepository(create_session_factory(engine)).delete("poster")
        finally:
            await engine.dispose()

    asyncio.run(delete_asset())
    archive = tmp_path / "deleted-cache.zip"
    if status == "running":
        with pytest.raises(BackupError, match="Speech task references a missing"):
            create_backup(source, archive, maintenance=True)
        assert not archive.exists()
        return
    create_backup(source, archive, maintenance=True)
    verify_backup(archive)
    target = tmp_path / "restored-cache"
    restore_backup(archive, target, master_key=MASTER_KEY, maintenance=True)
    with sqlite3.connect(target / "datapulse.db") as connection:
        assert connection.execute(
            "SELECT status, asset_id FROM speech_task WHERE id='finished'"
        ).fetchone() == (status, "")
    with sqlite3.connect(source.data_dir / "datapulse.db") as connection:
        assert connection.execute(
            "SELECT status, asset_id FROM speech_task WHERE id='finished'"
        ).fetchone() == (status, "poster")


@pytest.mark.parametrize("fault", ["missing_exact_plugin", "invalid_document"])
def test_template_document_and_exact_dependencies_are_verified(source, tmp_path, fault):
    import shutil

    from datapulse.ecosystem.service import EcosystemService
    from datapulse.operations.backup import BackupError, create_backup
    from tests.ecosystem.test_service import archive, plugin_manifest, template_archive

    service = EcosystemService(root=source.data_dir / "ecosystem")
    service.install(archive())
    document = {
        "canvas": {"width": 1920, "height": 1080},
        "plugin_dependencies": [{"id": "org.example.metrics", "version": "1.0.0"}],
        "components": [{
            "id": "metric", "type": "org.example.metric",
            "frame": {"x": 0, "y": 0, "width": 100, "height": 100},
        }],
    }
    service.install(template_archive(document))
    create_backup(source, tmp_path / "valid-template.zip", maintenance=True)
    packages = source.data_dir / "ecosystem/packages"
    if fault == "missing_exact_plugin":
        service.install(archive(plugin_manifest(version="1.1.0")))
        shutil.rmtree(packages / "plugin/org.example.metrics/1.0.0")
    else:
        directory = packages / "template/org.example.board/1.0.0"
        payload = json.dumps({**document, "canvas": {"width": 0, "height": 1080}}).encode()
        (directory / "content/document.json").write_bytes(payload)
        record = json.loads((directory / "record.json").read_text())
        for entry in record["files"]:
            if entry["path"] == "document.json":
                entry.update(size=len(payload), sha256=hashlib.sha256(payload).hexdigest())
        (directory / "record.json").write_text(json.dumps(record))
    with pytest.raises(BackupError, match="template|Template|plugin|document"):
        create_backup(source, tmp_path / "invalid-template.zip", maintenance=True)


def test_roundtrip_remaps_storage_and_invalidates_credentials(source, tmp_path):
    from datapulse.operations.backup import restore_backup, verify_backup

    archive = create_archive(source, tmp_path)
    manifest = verify_backup(archive)
    assert manifest.app_version == source.app_version
    assert manifest.master_key_required
    assert manifest.member_count == len(manifest.members)
    assert stat.S_IMODE(archive.stat().st_mode) == 0o600
    with zipfile.ZipFile(archive) as zipped:
        assert not any(
            ".env" in name or ".key" in name or ".log" in name for name in zipped.namelist()
        )
        assert MASTER_KEY.encode() not in zipped.read("manifest.json")
    target = tmp_path / "restored"
    restore_backup(archive, target, master_key=MASTER_KEY, maintenance=True)
    with sqlite3.connect(target / "datapulse.db") as connection:
        (path,) = connection.execute("SELECT storage_path FROM file_asset").fetchone()
        assert Path(path) == target / "files" / "sales.csv"
        import duckdb

        with duckdb.connect() as query:
            assert query.execute("SELECT sum(amount) FROM read_csv_auto(?)", [path]).fetchone() == (
                21,
            )
        path, thumbnail = connection.execute(
            "SELECT storage_path, thumbnail_path FROM screen_asset"
        ).fetchone()
        assert Path(path).read_bytes() == (source.data_dir / "assets" / "poster.png").read_bytes()
        assert Path(thumbnail).is_relative_to(target)
        assert (
            json.loads(connection.execute("SELECT published_document FROM screen").fetchone()[0])[
                "components"
            ][0]["props"]["asset_id"]
            == "poster"
        )
        (envelope,) = connection.execute("SELECT secret_envelope FROM data_source").fetchone()
        assert (
            SecretBox(MASTER_KEY).decrypt("metrics", SecretEnvelope.model_validate_json(envelope))
            == "secret"
        )
        source_config = json.loads(
            connection.execute("SELECT config_json FROM data_source").fetchone()[0]
        )
        with sqlite3.connect(target / "sources" / source_config["path"]) as metrics:
            assert metrics.execute("SELECT sum(amount) FROM metrics").fetchone() == (21,)
        for table in ("admin_session", "display_access", "embed_access"):
            assert connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
        assert connection.execute(
            "SELECT setup_code_hash, setup_code_expires_at FROM system_state"
        ).fetchone() == (None, None)
        assert connection.execute("SELECT count(*) FROM admin_account").fetchone()[0] == 1


@pytest.mark.parametrize("master_key", [None, base64.urlsafe_b64encode(b"x" * 32).decode()])
def test_missing_or_wrong_key_preserves_empty_target(source, tmp_path, master_key):
    from datapulse.operations.backup import BackupError, restore_backup

    archive = create_archive(source, tmp_path)
    target = tmp_path / "restored"
    target.mkdir()
    with pytest.raises(BackupError, match="master key"):
        restore_backup(archive, target, master_key=master_key, maintenance=True)
    assert list(target.iterdir()) == []
    assert not list(tmp_path.glob(".restored.restore-*"))


def test_maintenance_acknowledgement_and_runtime_lock_are_required(source, tmp_path):
    from datapulse.operations.backup import BackupError, create_backup
    from datapulse.operations.maintenance import runtime_lease

    with pytest.raises(BackupError, match="maintenance"):
        create_backup(source, tmp_path / "backup.zip")
    with runtime_lease(source.data_dir), runtime_lease(source.data_dir):
        with pytest.raises(BackupError, match="running|active"):
            create_backup(source, tmp_path / "backup.zip", maintenance=True)
    assert not (tmp_path / "backup.zip").exists()


def rewrite_archive(archive, *, extra=None, replace=None, change_manifest=None):
    with zipfile.ZipFile(archive) as zipped:
        entries = [(info, zipped.read(info)) for info in zipped.infolist()]
    with zipfile.ZipFile(archive, "w") as zipped:
        for info, data in entries:
            if replace and info.filename == replace[0]:
                data = replace[1]
            if change_manifest and info.filename == "manifest.json":
                manifest = json.loads(data)
                change_manifest(manifest)
                data = json.dumps(manifest).encode()
            zipped.writestr(info, data)
        if extra:
            zipped.writestr(*extra)


@pytest.mark.parametrize(
    "name",
    ["../escape", "/absolute", "C:/windows", "files\\escape", "files//double", "files/./dot"],
)
def test_unsafe_archive_paths_rejected_without_target(source, tmp_path, name):
    from datapulse.operations.backup import BackupError, restore_backup

    archive = create_archive(source, tmp_path)
    rewrite_archive(archive, extra=(name, b"bad"))
    with pytest.raises(BackupError, match="path|member"):
        restore_backup(archive, tmp_path / "restored", master_key=MASTER_KEY, maintenance=True)
    assert not (tmp_path / "restored").exists()
    assert not (tmp_path / "escape").exists()


@pytest.mark.parametrize(
    "kind", ["duplicate", "symlink", "unexpected", "checksum", "schema", "version"]
)
def test_archive_tampering_is_rejected(source, tmp_path, kind):
    from datapulse.operations.backup import BackupError, verify_backup

    archive = create_archive(source, tmp_path)
    if kind == "duplicate":
        with pytest.warns(UserWarning, match="Duplicate"):
            rewrite_archive(archive, extra=("manifest.json", b"{}"))
    elif kind == "symlink":
        info = zipfile.ZipInfo("files/link")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        rewrite_archive(archive, extra=(info, b"/etc/passwd"))
    elif kind == "unexpected":
        rewrite_archive(archive, extra=("files/unlisted", b"bad"))
    elif kind == "checksum":
        rewrite_archive(archive, replace=("files/sales.csv", b"changed"))
    elif kind == "schema":
        rewrite_archive(archive, change_manifest=lambda m: m.update(schema_version=999))
    else:
        rewrite_archive(archive, change_manifest=lambda m: m.update(app_version="999.0.0"))
    with pytest.raises(BackupError):
        verify_backup(archive)


def test_archive_resource_limits(source, tmp_path):
    from datapulse.operations.backup import ArchiveLimits, BackupError, verify_backup

    archive = create_archive(source, tmp_path)
    for limits in (
        ArchiveLimits(max_members=2),
        ArchiveLimits(max_total_bytes=100),
        ArchiveLimits(max_member_bytes=100),
        ArchiveLimits(max_archive_bytes=100),
    ):
        with pytest.raises(BackupError, match="limit"):
            verify_backup(archive, limits=limits)


def test_existing_archive_and_nonempty_restore_are_preserved(source, tmp_path):
    from datapulse.operations.backup import BackupError, create_backup, restore_backup

    archive = create_archive(source, tmp_path)
    original = archive.read_bytes()
    with pytest.raises(BackupError, match="exist"):
        create_backup(source, archive, maintenance=True)
    assert archive.read_bytes() == original
    with pytest.raises(BackupError, match="empty"):
        restore_backup(archive, source.data_dir, master_key=MASTER_KEY, maintenance=True)
    assert (source.data_dir / ".env").read_text() == "TOP_SECRET=not-in-backup"


def test_missing_referenced_file_and_symlink_are_rejected(source, tmp_path):
    from datapulse.operations.backup import BackupError, create_backup

    file = source.data_dir / "files" / "sales.csv"
    file.unlink()
    with pytest.raises(BackupError, match="missing|file"):
        create_backup(source, tmp_path / "missing.zip", maintenance=True)
    external = tmp_path / "outside.csv"
    external.write_text("secret")
    file.symlink_to(external)
    with pytest.raises(BackupError, match="symlink|symbolic"):
        create_backup(source, tmp_path / "symlink.zip", maintenance=True)
    assert not (tmp_path / "missing.zip").exists()
    assert not (tmp_path / "symlink.zip").exists()


def test_external_roots_require_explicit_opt_in(source, tmp_path):
    from datapulse.operations.backup import BackupError, create_backup, restore_backup

    external = tmp_path / "external-assets"
    (source.data_dir / "assets").rename(external)
    with sqlite3.connect(source.data_dir / "datapulse.db") as connection:
        connection.execute(
            "UPDATE screen_asset SET storage_path=?, thumbnail_path=?",
            (
                str(external / "poster.png"),
                str(external / "poster.preview.png"),
            ),
        )
    settings = source.model_copy(update={"assets_dir": external})
    with pytest.raises(BackupError, match="external"):
        create_backup(settings, tmp_path / "backup.zip", maintenance=True)
    create_backup(settings, tmp_path / "backup.zip", maintenance=True, include_external_paths=True)
    restore_backup(
        tmp_path / "backup.zip", tmp_path / "restored", master_key=MASTER_KEY, maintenance=True
    )
    assert (tmp_path / "restored" / "assets" / "poster.png").exists()


def test_postgresql_automatic_backup_fails_clearly(source, tmp_path):
    from datapulse.operations.backup import BackupError, create_backup

    settings = source.model_copy(
        update={"database_url": "postgresql+asyncpg://secret@localhost/db"}
    )
    with pytest.raises(BackupError, match="PostgreSQL|SQLite") as error:
        create_backup(settings, tmp_path / "backup.zip", maintenance=True)
    assert "secret" not in str(error.value)


def test_declared_package_files_and_uninstall_history_survive_restore(source, tmp_path):
    import asyncio

    from datapulse.ecosystem.service import EcosystemService
    from datapulse.metadata import create_metadata_engine, create_session_factory
    from datapulse.operations.backup import restore_backup

    engine = create_metadata_engine(source)
    service = EcosystemService(
        root=source.data_dir / "ecosystem", session_factory=create_session_factory(engine)
    )
    manifest = {
        "id": "org.example.counter",
        "version": "1.0.0",
        "name": "Counter",
        "compatible_api": ">=1,<2",
        "entry": "counter.mjs",
        "components": [
            {
                "type": "org.example.counter",
                "name": "Counter",
                "category": "custom",
                "property_schema": {"type": "object"},
                "data_schema": {"type": "object"},
            }
        ],
    }

    def package(version):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zipped:
            zipped.writestr("manifest.json", json.dumps({**manifest, "version": version}))
            zipped.writestr("counter.mjs", "export default { components: {} };")
        return buffer.getvalue()

    service.install(package("1.0.0"))
    service.install(package("0.9.0"))
    asyncio.run(service.uninstall("plugin", "org.example.counter", "0.9.0"))
    asyncio.run(engine.dispose())
    target = tmp_path / "restored"
    restore_backup(
        create_archive(source, tmp_path), target, maintenance=True, master_key=MASTER_KEY
    )
    restored = EcosystemService(root=target / "ecosystem")
    assert restored.get("plugin", "org.example.counter", "1.0.0").version == "1.0.0"
    assert (target / "ecosystem/history/plugin/org.example.counter/0.9.0.json").is_file()
    assert (
        restored.file_path("plugin", "org.example.counter", "1.0.0", "counter.mjs")
        .read_text()
        .startswith("export")
    )


def test_checksum_valid_but_corrupted_database_is_rejected(source, tmp_path):
    from datapulse.operations.backup import BackupError, verify_backup

    archive = create_archive(source, tmp_path)
    broken = b"this is not SQLite"

    def update(manifest):
        for member in manifest["members"]:
            if member["path"] == "datapulse.db":
                manifest["total_bytes"] += len(broken) - member["size"]
                member.update(size=len(broken), sha256=hashlib.sha256(broken).hexdigest())

    rewrite_archive(archive, replace=("datapulse.db", broken), change_manifest=update)
    with pytest.raises(BackupError, match="corrupt|database"):
        verify_backup(archive)


def test_missing_published_references_rejected(source, tmp_path):
    from datapulse.operations.backup import BackupError, create_backup

    with sqlite3.connect(source.data_dir / "datapulse.db") as connection:
        connection.execute("DELETE FROM screen_asset")
    with pytest.raises(BackupError, match="missing media"):
        create_backup(source, tmp_path / "backup.zip", maintenance=True)


def test_missing_published_plugin_dependency_rejected(source, tmp_path):
    from datapulse.operations.backup import BackupError, create_backup

    with sqlite3.connect(source.data_dir / "datapulse.db") as connection:
        document = json.loads(
            connection.execute("SELECT published_document FROM screen").fetchone()[0]
        )
        document["plugin_dependencies"] = [{"id": "org.example.missing", "version": "1.0.0"}]
        connection.execute("UPDATE screen SET published_document=?", (json.dumps(document),))
    with pytest.raises(BackupError, match="plugin|file"):
        create_backup(source, tmp_path / "backup.zip", maintenance=True)


@pytest.mark.parametrize("document_column", ["draft_document", "published_document"])
def test_missing_nested_chart_dataset_reference_rejected(source, tmp_path, document_column):
    from datapulse.operations.backup import BackupError, create_backup

    with sqlite3.connect(source.data_dir / "datapulse.db") as connection:
        document = json.loads(
            connection.execute(f"SELECT {document_column} FROM screen").fetchone()[0]
        )
        document["components"].append(
            {
                "id": "sales-chart",
                "type": "builtin.bar",
                "frame": {"x": 100, "y": 0, "width": 400, "height": 300},
                "data_binding": {
                    "source": "dataset",
                    "chart_spec": {
                        "dataset_id": "sales",
                        "dimensions": ["region"],
                        "measures": [{"field": "amount", "aggregate": "sum"}],
                        "visual": {"type": "bar"},
                    },
                },
            }
        )
        connection.execute(
            f"UPDATE screen SET {document_column}=?", (json.dumps(document),)
        )
    create_backup(source, tmp_path / "valid.zip", maintenance=True)
    with sqlite3.connect(source.data_dir / "datapulse.db") as connection:
        connection.execute("DELETE FROM dataset WHERE id='sales'")
    with pytest.raises(BackupError, match="missing dataset"):
        create_backup(source, tmp_path / "broken.zip", maintenance=True)
    assert not (tmp_path / "broken.zip").exists()


def test_compressed_bomb_is_rejected_before_extraction(source, tmp_path):
    from datapulse.operations.backup import BackupError, verify_backup

    archive = create_archive(source, tmp_path)
    with zipfile.ZipFile(archive, "a", compression=zipfile.ZIP_DEFLATED) as zipped:
        zipped.writestr("files/bomb", b"0" * 1_000_000)
    with pytest.raises(BackupError, match="ratio|limit"):
        verify_backup(archive)


def test_failure_during_finalization_preserves_target(source, tmp_path, monkeypatch):
    from datapulse.operations import backup

    archive = create_archive(source, tmp_path)
    target = tmp_path / "restored"
    target.mkdir()

    def failed_rename(*args):
        raise OSError("simulated full disk")

    monkeypatch.setattr(backup.os, "rename", failed_rename)
    with pytest.raises(backup.BackupError, match="preserved"):
        backup.restore_backup(archive, target, maintenance=True, master_key=MASTER_KEY)
    assert list(target.iterdir()) == []
    assert not list(tmp_path.glob(".restored.restore-*"))


def test_cli_create_verify_inspect_and_restore(source, tmp_path, monkeypatch, capsys):
    from datapulse.operations.cli import main

    monkeypatch.setenv("DATAPULSE_DATA_DIR", str(source.data_dir))
    monkeypatch.setenv("DATAPULSE_MASTER_KEY", MASTER_KEY)
    archive = tmp_path / "cli.zip"
    assert main(["backup", "create", "--archive", str(archive), "--maintenance"]) == 0
    for action in ("verify", "inspect"):
        assert main(["backup", action, "--archive", str(archive)]) == 0
    assert (
        main(
            [
                "backup",
                "restore",
                "--archive",
                str(archive),
                "--target",
                str(tmp_path / "restored"),
                "--maintenance",
            ]
        )
        == 0
    )
    assert main(["backup", "create", "--archive", str(tmp_path / "missing-flag.zip")]) == 1
    captured = capsys.readouterr()
    assert MASTER_KEY not in captured.out + captured.err
    assert "maintenance" in captured.err


def test_restore_does_not_replay_pending_speech_or_retain_worker_leases(source, tmp_path):
    from datapulse.metadata.models import SpeechTaskRecord
    from datapulse.operations.backup import restore_backup

    engine = create_engine(f"sqlite:///{source.data_dir / 'datapulse.db'}")
    with Session(engine) as session, session.begin():
        session.add(SpeechTaskRecord(id="pending", plan_id="plan", status="queued"))
        session.add(
            SpeechTaskRecord(
                id="running",
                plan_id="plan",
                status="running",
                lease_owner="old-worker",
                lease_expires_at=utc_now(),
                reserved_audio_seconds=10,
                quota_period=utc_now(),
            )
        )
    engine.dispose()
    target = tmp_path / "restored"
    restore_backup(
        create_archive(source, tmp_path), target, maintenance=True, master_key=MASTER_KEY
    )
    with sqlite3.connect(target / "datapulse.db") as connection:
        assert connection.execute(
            "SELECT DISTINCT status, error_code, lease_owner, "
            "reserved_audio_seconds FROM speech_task"
        ).fetchall() == [
            ("failed", "SPEECH_TASK_INTERRUPTED", None, 0),
        ]
