import io
import json
import stat
import zipfile
from pathlib import Path

import pytest

from datapulse.ecosystem.service import EcosystemService
from datapulse.errors import DataPulseError


def plugin_manifest(**updates):
    return {
        "id": "org.example.metrics",
        "version": "1.0.0",
        "compatible_api": ">=1,<2",
        "name": "Metrics",
        "license": "MIT",
        "entry": "index.mjs",
        "components": [
            {
                "type": "org.example.metric",
                "name": "Metric",
                "category": "Data",
                "property_schema": {"type": "object"},
                "data_schema": {},
            }
        ],
        **updates,
    }


def archive(manifest=None, files=None, *, compression=zipfile.ZIP_STORED):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=compression) as package:
        package.writestr("manifest.json", json.dumps(manifest or plugin_manifest()))
        for name, data in (files or {"index.mjs": b"export default {apiVersion:1};"}).items():
            package.writestr(name, data)
    return output.getvalue()


def test_install_is_immutable_and_survives_restart(tmp_path):
    service = EcosystemService(root=tmp_path)
    payload = archive()
    package = service.install(payload)
    assert package.kind == "plugin"
    assert package.id == "org.example.metrics"
    assert len(package.sha256) == 64
    assert package.manifest.license == "MIT"
    assert service.install(payload) == package
    restored = EcosystemService(root=tmp_path)
    assert restored.list() == (package,)
    assert restored.get("plugin", package.id, package.version) == package
    with pytest.raises(DataPulseError, match="immutable"):
        restored.install(archive(files={"index.mjs": b"different"}))
    assert restored.list() == (package,)
    assert not list((tmp_path / ".staging").iterdir())


@pytest.mark.parametrize(
    "name",
    [
        "../escape.mjs",
        "/absolute.mjs",
        "a/../bad.mjs",
        "a//bad.mjs",
        "./bad.mjs",
        "a\\bad.mjs",
        "C:/bad.mjs",
    ],
)
def test_rejects_noncanonical_archive_paths(tmp_path, name):
    service = EcosystemService(root=tmp_path)
    with pytest.raises(DataPulseError):
        service.install(archive(files={"index.mjs": b"ok", name: b"bad"}))
    assert service.list() == ()
    assert not list((tmp_path / ".staging").iterdir())


def test_rejects_duplicate_members_and_symlinks(tmp_path):
    service = EcosystemService(root=tmp_path)
    duplicate = io.BytesIO(archive())
    with pytest.warns(UserWarning), zipfile.ZipFile(duplicate, "a") as package:
        package.writestr("index.mjs", "other")
    with pytest.raises(DataPulseError):
        service.install(duplicate.getvalue())
    symlink = zipfile.ZipInfo("linked.mjs")
    symlink.create_system = 3
    symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(DataPulseError):
        service.install(archive(files={"index.mjs": b"ok", symlink: b"/etc/passwd"}))


@pytest.mark.parametrize(
    "manifest",
    [
        plugin_manifest(compatible_api=">=2"),
        plugin_manifest(entry="missing.mjs"),
        plugin_manifest(entry="./index.mjs"),
        plugin_manifest(
            components=[
                {
                    "type": "builtin.text",
                    "name": "x",
                    "category": "x",
                    "property_schema": {},
                    "data_schema": {},
                }
            ]
        ),
        plugin_manifest(secret="bad"),
        plugin_manifest(version="../bad"),
    ],
)
def test_rejects_invalid_manifests(tmp_path, manifest):
    service = EcosystemService(root=tmp_path)
    with pytest.raises(DataPulseError):
        service.install(archive(manifest))
    assert service.list() == ()


def test_rejects_compression_bombs_and_limits(tmp_path):
    service = EcosystemService(root=tmp_path)
    with pytest.raises(DataPulseError):
        service.install(
            archive(files={"index.mjs": b"a" * 2_000_000}, compression=zipfile.ZIP_DEFLATED)
        )
    with pytest.raises(DataPulseError):
        service.install(archive(files={f"{i}.txt": b"x" for i in range(257)}))


def test_failed_commit_leaves_no_installed_or_staged_package(tmp_path, monkeypatch):
    service = EcosystemService(root=tmp_path)
    original = Path.rename

    def fail_commit(path, target):
        if path.parent == tmp_path / ".staging":
            raise OSError("disk unavailable")
        return original(path, target)

    monkeypatch.setattr(Path, "rename", fail_commit)
    with pytest.raises(OSError, match="disk unavailable"):
        service.install(archive())
    assert service.list() == ()
    assert not list((tmp_path / ".staging").iterdir())


def template_document():
    return {
        "canvas": {"width": 1000, "height": 800},
        "components": [
            {
                "id": "metric",
                "type": "builtin.kpi",
                "frame": {"x": 0, "y": 0, "width": 100, "height": 100},
                "state": {"group_id": "group-one"},
                "data_binding": {"source": "static", "rows": [[1]]},
            },
            {
                "id": "speaker",
                "type": "builtin.digital_human",
                "frame": {"x": 100, "y": 0, "width": 100, "height": 100},
                "state": {"group_id": "group-one"},
                "props": {},
                "data_binding": {
                    "source": "components",
                    "variables": [{"name": "value", "component_id": "metric", "field": "value"}],
                },
            },
        ],
    }


def template_archive(document=None, **updates):
    return archive(
        {
            "kind": "template",
            "id": "org.example.board",
            "version": "1.0.0",
            "name": "Board",
            "compatible_api": ">=1,<2",
            **updates,
        },
        {"document.json": json.dumps(document or template_document())},
    )


@pytest.mark.anyio
async def test_apply_template_remaps_components_groups_and_preserves_parameter_links(services):
    from datapulse.ecosystem.models import TemplateApply

    ecosystem, screens, _ = services
    document = template_document()
    document["parameters"] = [{"id": "region-id", "name": "region", "data_type": "string"}]
    document["components"][0]["interactions"] = [
        {"event": "click", "action": "set_parameter", "parameter": "region", "field": "region"}
    ]
    ecosystem.install(template_archive(document))
    created = await ecosystem.apply_template(
        "org.example.board", "1.0.0", TemplateApply(name="New")
    )
    saved = await screens.get(created.id)
    metric, speaker = saved.draft_document.components
    assert metric.id != "metric" and speaker.id != "speaker"
    assert speaker.data_binding["variables"][0]["component_id"] == metric.id
    assert metric.state.group_id == speaker.state.group_id != "group-one"
    assert metric.interactions[0].parameter == "region"
    assert saved.published_document is None


@pytest.mark.anyio
async def test_template_requires_explicit_authorized_reference_mapping(services):
    from datapulse.ecosystem.models import TemplateApply

    ecosystem, screens, factory = services
    document = template_document()
    document["components"][0]["data_binding"] = {"dataset_id": "old-dataset"}
    document["components"][0]["props"] = {"asset_id": "old-asset"}
    ecosystem.install(template_archive(document, datasets=["old-dataset"], assets=["old-asset"]))
    with pytest.raises(DataPulseError, match="mapping"):
        await ecosystem.apply_template("org.example.board", "1.0.0", TemplateApply(name="Missing"))
    payload = TemplateApply(
        name="Mapped",
        dataset_mapping={"old-dataset": "allowed"},
        asset_mapping={"old-asset": "allowed-asset"},
    )
    calls = []

    async def denied(kind, identifier):
        calls.append((kind, identifier))
        raise DataPulseError("FORBIDDEN", "Denied", 403)

    with pytest.raises(DataPulseError, match="Denied"):
        await ecosystem.apply_template(
            "org.example.board", "1.0.0", payload, authorize_reference=denied
        )
    assert calls == [("dataset", "allowed")]
    assert await screens.list() == ()
    with pytest.raises(DataPulseError, match="authorization"):
        await ecosystem.apply_template("org.example.board", "1.0.0", payload)


@pytest.mark.parametrize(
    "props",
    [
        {"api_key": "hidden"},
        {"nested": {"password": "hidden"}},
        {"url": "https://user:password@example.test/"},
        {"token": "Bearer secret"},
    ],
)
def test_template_cannot_carry_secrets(tmp_path, props):
    document = template_document()
    document["components"][0]["props"] = props
    with pytest.raises(DataPulseError, match="credential|secret"):
        EcosystemService(root=tmp_path).install(template_archive(document))


def test_template_requires_declared_references(tmp_path):
    document = template_document()
    document["components"][0]["data_binding"] = {"dataset_id": "production"}
    with pytest.raises(DataPulseError, match="declared"):
        EcosystemService(root=tmp_path).install(template_archive(document))


@pytest.mark.anyio
async def test_uninstall_unreferenced_package_and_keep_version_hash(services):
    ecosystem, _, _ = services
    payload = archive()
    package = ecosystem.install(payload)
    await ecosystem.uninstall("plugin", package.id, package.version)
    assert ecosystem.list() == ()
    with pytest.raises(DataPulseError, match="immutable"):
        ecosystem.install(archive(files={"index.mjs": b"changed"}))
    assert ecosystem.install(payload).sha256 == package.sha256


def plugin_document(version="1.0.0", props=None):
    from datapulse.contracts.dashboard import DashboardDocument

    return DashboardDocument.model_validate(
        {
            "canvas": {"width": 1000, "height": 800},
            "plugin_dependencies": [{"id": "org.example.metrics", "version": version}],
            "components": [
                {
                    "id": "metric",
                    "type": "org.example.metric",
                    "props": props or {},
                    "frame": {"x": 0, "y": 0, "width": 100, "height": 100},
                }
            ],
        }
    )


@pytest.mark.anyio
async def test_uninstall_protects_draft_and_published_exact_versions(services):
    from datapulse.contracts.dashboard import DashboardDocument
    from datapulse.screen.models import ScreenCreate, ScreenDraftUpdate
    from datapulse.screen.repository import ScreenRepository

    ecosystem, screens, factory = services
    ecosystem.install(archive())
    ecosystem.install(archive(plugin_manifest(version="2.0.0")))
    screen = await screens.create(ScreenCreate(name="Plugins", draft_document=plugin_document()))
    with pytest.raises(DataPulseError) as caught:
        await ecosystem.uninstall("plugin", "org.example.metrics", "1.0.0")
    assert caught.value.code == "ECOSYSTEM_IN_USE"
    await ScreenRepository(factory).publish(
        screen.id, document=plugin_document(), expected_revision=0
    )
    await screens.save_draft(
        screen.id,
        ScreenDraftUpdate(
            expected_revision=0,
            draft_document=DashboardDocument(canvas={"width": 1000, "height": 800}),
        ),
    )
    with pytest.raises(DataPulseError):
        await ecosystem.uninstall("plugin", "org.example.metrics", "1.0.0")
    await ecosystem.uninstall("plugin", "org.example.metrics", "2.0.0")
    assert ecosystem.get("plugin", "org.example.metrics", "1.0.0")


def test_document_assets_are_bound_to_exact_dependency_and_hash(tmp_path):
    service = EcosystemService(root=tmp_path)
    package = service.install(archive())
    path = service.file_path_for_document(plugin_document(), package.id, "1.0.0", "index.mjs")
    assert path.read_bytes().startswith(b"export default")
    with pytest.raises(DataPulseError):
        service.file_path_for_document(plugin_document("2.0.0"), package.id, "1.0.0", "index.mjs")
    with pytest.raises(DataPulseError):
        service.file_path_for_document(plugin_document(), package.id, "1.0.0", "../record.json")
    with pytest.raises(DataPulseError):
        service.file_path_for_document(plugin_document(), package.id, "1.0.0", "record.json")
    path.write_text("tampered")
    with pytest.raises(DataPulseError) as caught:
        service.file_path_for_document(plugin_document(), package.id, "1.0.0", "index.mjs")
    assert caught.value.code == "ECOSYSTEM_CORRUPT"


def test_plugin_document_requires_installed_version_and_valid_properties(tmp_path):
    service = EcosystemService(root=tmp_path)
    manifest = plugin_manifest()
    manifest["components"][0]["property_schema"] = {
        "type": "object",
        "properties": {"label": {"type": "string"}},
        "required": ["label"],
        "additionalProperties": False,
    }
    manifest["components"][0]["default_props"] = {"label": "Total"}
    service.install(archive(manifest))
    service.validate_document(plugin_document(props={"label": "Hello"}))
    for document in [
        plugin_document(props={"label": 2}),
        plugin_document("8.0.0"),
        plugin_document().model_copy(update={"plugin_dependencies": ()}),
    ]:
        with pytest.raises(DataPulseError):
            service.validate_document(document)


@pytest.mark.parametrize("schema", [{"type": "unknown"}, {"$ref": "https://evil.test/schema"}])
def test_install_rejects_invalid_or_external_property_schemas(tmp_path, schema):
    manifest = plugin_manifest()
    manifest["components"][0]["property_schema"] = schema
    with pytest.raises(DataPulseError):
        EcosystemService(root=tmp_path).install(archive(manifest))


@pytest.mark.parametrize("field", ["property_schema", "data_schema"])
def test_install_rejects_unresolved_local_references_even_in_unused_schema_branches(
    tmp_path, field
):
    manifest = plugin_manifest()
    manifest["components"][0][field] = {
        "type": "object",
        "properties": {"optional": {"$ref": "#/definitions/missing"}},
    }
    service = EcosystemService(root=tmp_path)
    with pytest.raises(DataPulseError):
        service.install(archive(manifest))
    assert service.list() == ()
    assert not list((tmp_path / ".staging").iterdir())


@pytest.mark.parametrize(
    "schema",
    [
        {"$schema": "https://json-schema.org/draft/2020-12/schema"},
        {"type": "object", "unevaluatedProperties": False},
        {"properties": {"items": {"type": "array", "prefixItems": [{"type": "string"}]}}},
    ],
)
def test_install_rejects_schema_dialects_the_browser_cannot_enforce(tmp_path, schema):
    manifest = plugin_manifest()
    manifest["components"][0]["property_schema"] = schema
    with pytest.raises(DataPulseError):
        EcosystemService(root=tmp_path).install(archive(manifest))


def test_plugin_schema_uses_draft_seven_tuple_and_local_reference_semantics(tmp_path):
    manifest = plugin_manifest()
    manifest["components"][0]["property_schema"] = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "definitions": {"label": {"type": "string", "minLength": 1}},
        "properties": {
            "values": {
                "type": "array",
                "items": [{"$ref": "#/definitions/label"}],
                "additionalItems": False,
            },
        },
    }
    manifest["components"][0]["default_props"] = {"values": ["Total"]}
    service = EcosystemService(root=tmp_path)
    service.install(archive(manifest))
    service.validate_document(plugin_document(props={"values": ["Valid"]}))
    with pytest.raises(DataPulseError):
        service.validate_document(plugin_document(props={"values": [2]}))


@pytest.mark.anyio
async def test_apply_valid_mapping_checks_existence_and_rewrites_references(services):
    from datapulse.ecosystem.models import TemplateApply
    from datapulse.metadata.models import DatasetRecord, ScreenAssetRecord

    ecosystem, _, factory = services
    document = template_document()
    document["components"][0]["data_binding"] = {"dataset_id": "old-dataset"}
    document["components"][0]["props"] = {"avatar_asset_id": "old-asset"}
    ecosystem.install(template_archive(document, datasets=["old-dataset"], assets=["old-asset"]))
    async with factory.begin() as session:
        session.add(DatasetRecord(id="mapped-dataset", name="Mapped", definition_json={}))
        session.add(
            ScreenAssetRecord(
                id="mapped-asset",
                asset_type="image",
                mime_type="image/png",
                sha256="a" * 64,
                size_bytes=10,
                storage_path="asset.png",
                family_id="family",
                version=1,
            )
        )
    calls = []

    async def allowed(kind, identifier):
        calls.append((kind, identifier))

    created = await ecosystem.apply_template(
        "org.example.board",
        "1.0.0",
        TemplateApply(
            name="Mapped",
            dataset_mapping={"old-dataset": "mapped-dataset"},
            asset_mapping={"old-asset": "mapped-asset"},
        ),
        authorize_reference=allowed,
    )
    assert created.draft_document.components[0].data_binding["dataset_id"] == "mapped-dataset"
    assert created.draft_document.components[0].props["avatar_asset_id"] == "mapped-asset"
    assert calls == [("dataset", "mapped-dataset"), ("asset", "mapped-asset")]
    with pytest.raises(DataPulseError, match="does not exist"):
        await ecosystem.apply_template(
            "org.example.board",
            "1.0.0",
            TemplateApply(
                name="Missing",
                dataset_mapping={"old-dataset": "absent"},
                asset_mapping={"old-asset": "mapped-asset"},
            ),
            authorize_reference=allowed,
        )


@pytest.mark.parametrize(
    "files",
    [
        {"index.mjs": b"ok", "nested": b"file", "nested/file.txt": b"child"},
        {"index.mjs": b"ok", "nested/file.txt": b"child", "nested": b"file"},
    ],
)
def test_rejects_archive_file_directory_collisions(tmp_path, files):
    service = EcosystemService(root=tmp_path)
    with pytest.raises(DataPulseError):
        service.install(archive(files=files))
    assert service.list() == ()


@pytest.mark.parametrize(
    "props",
    [
        {"token": "a-private-token"},
        {"url": "https://example.test/image?api_key=secret-value"},
    ],
)
def test_template_rejects_generic_tokens_and_credentials_in_query_strings(tmp_path, props):
    document = template_document()
    document["components"][0]["props"] = props
    with pytest.raises(DataPulseError):
        EcosystemService(root=tmp_path).install(template_archive(document))


def test_template_install_requires_its_exact_plugin_dependencies(tmp_path):
    service = EcosystemService(root=tmp_path)
    with pytest.raises(DataPulseError):
        service.install(template_archive(plugin_document().model_dump(mode="json")))
    assert service.list() == ()


@pytest.mark.anyio
async def test_template_install_racing_uninstall_never_leaves_a_missing_dependency(
    services, monkeypatch
):
    from threading import Event, Thread

    ecosystem, _, factory = services
    ecosystem.install(archive())
    installer = EcosystemService(root=ecosystem.root, session_factory=factory)
    scanned, installed = Event(), Event()
    failures = []
    original_list = ecosystem.list

    def scan_then_allow_install():
        snapshot = original_list()
        scanned.set()
        installed.wait(timeout=0.2)
        return snapshot

    def install_template():
        if not scanned.wait(timeout=5):
            return
        try:
            installer.install(template_archive(plugin_document().model_dump(mode="json")))
        except DataPulseError as error:
            failures.append(error)
        finally:
            installed.set()

    monkeypatch.setattr(ecosystem, "list", scan_then_allow_install)
    worker = Thread(target=install_template)
    worker.start()
    try:
        await ecosystem.uninstall("plugin", "org.example.metrics", "1.0.0")
    except DataPulseError as error:
        assert error.code == "ECOSYSTEM_IN_USE"
    finally:
        worker.join(timeout=5)
    assert not worker.is_alive()
    packages = original_list()
    if any(package.kind == "template" for package in packages):
        assert any(package.kind == "plugin" for package in packages)
    else:
        assert failures and failures[0].code == "ECOSYSTEM_NOT_FOUND"


@pytest.mark.anyio
async def test_cancelled_uninstall_keeps_reference_guard_until_removal_finishes(
    services, monkeypatch
):
    import asyncio
    from threading import Event

    ecosystem, _, _ = services
    ecosystem.install(archive())
    started, finish = Event(), Event()
    entered = asyncio.Event()
    original_remove = ecosystem._remove_package

    def blocked_removal(*args):
        started.set()
        assert finish.wait(timeout=5)
        original_remove(*args)

    async def publisher():
        async with ecosystem.publication_guard():
            entered.set()

    monkeypatch.setattr(ecosystem, "_remove_package", blocked_removal)
    removal = asyncio.create_task(ecosystem.uninstall("plugin", "org.example.metrics", "1.0.0"))
    assert await asyncio.to_thread(started.wait, 5)
    removal.cancel()
    publication = asyncio.create_task(publisher())
    try:
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(entered.wait(), timeout=0.1)
    finally:
        finish.set()
        with pytest.raises(asyncio.CancelledError):
            await removal
        await publication
