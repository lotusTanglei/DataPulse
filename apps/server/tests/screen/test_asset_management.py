import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import update

from datapulse.contracts.dashboard import DashboardDocument
from datapulse.contracts.screen_asset import ScreenAssetPatch
from datapulse.metadata import ScreenAssetRecord
from datapulse.screen.assets import (
    AssetInUse,
    AssetInvalid,
    AssetLimits,
    AssetNotFound,
    AssetQuotaExceeded,
    AssetScanRejected,
    AssetService,
    ScreenAssetRepository,
)
from datapulse.screen.media import MediaBusy, MediaInspector, MediaLimits
from datapulse.screen.publishing import PublishingService
from tests.screen.test_assets import mutation_headers, setup_admin
from tests.screen.test_publishing import DatasetLookup
from tests.support.app import build_test_app
from tests.support.media import image_bytes, wav_bytes


def picture_document(asset_id: str) -> DashboardDocument:
    return DashboardDocument(
        canvas={"width": 960, "height": 540},
        components=[
            {
                "id": "picture",
                "type": "builtin.image",
                "frame": {"x": 0, "y": 0, "width": 320, "height": 240},
                "props": {"asset_id": asset_id},
            }
        ],
    )


@pytest.mark.anyio
async def test_concurrent_uploads_deduplicate_payloads_and_preserve_quota(
    metadata_session_factory, tmp_path
) -> None:
    content = image_bytes()
    inspected = await MediaInspector().inspect(content, "image/png", ".png")
    total_size = len(content) + len(inspected.thumbnail)
    services = [
        AssetService(
            repository=ScreenAssetRepository(metadata_session_factory),
            assets_dir=tmp_path,
            limits=AssetLimits(total_bytes=total_size),
        )
        for _ in range(2)
    ]
    first, duplicate = await asyncio.gather(
        *(
            service.upload(filename="avatar.png", content_type="image/png", content=content)
            for service in services
        )
    )
    assert first.id == duplicate.id
    usage = await services[0].usage()
    assert usage.asset_count == 1
    assert usage.size_bytes == total_size
    with pytest.raises(AssetQuotaExceeded):
        await services[0].upload(
            filename="other.png", content_type="image/png", content=image_bytes(color="#f00000")
        )
    assert await services[0].get(first.id) == first


@pytest.mark.anyio
async def test_deployment_mime_allowlist_rejects_disabled_media(
    metadata_session_factory, tmp_path
) -> None:
    service = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory),
        assets_dir=tmp_path,
        limits=AssetLimits(allowed_mime_types=frozenset({"image/png"})),
    )

    with pytest.raises(AssetInvalid, match="deployment allowlist"):
        await service.upload(
            filename="voice.wav", content_type="audio/wav", content=wav_bytes(seconds=0.1)
        )

    image = await service.upload(
        filename="avatar.png", content_type="image/png", content=image_bytes()
    )
    assert image.mime_type == "image/png"


@pytest.mark.anyio
async def test_upload_exposes_a_rejecting_virus_scan_hook(
    metadata_session_factory, tmp_path
) -> None:
    scanned: list[tuple[str, str]] = []

    async def scanner(_content: bytes, mime_type: str, filename: str) -> bool:
        scanned.append((mime_type, filename))
        return False

    service = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory),
        assets_dir=tmp_path,
        scanner=scanner,
    )
    with pytest.raises(AssetScanRejected, match="virus scan"):
        await service.upload(
            filename="avatar.png", content_type="image/png", content=image_bytes()
        )
    assert scanned == [("image/png", "avatar.png")]
    assert await service.list() == ()


@pytest.mark.anyio
async def test_replacement_is_a_new_version_and_cannot_break_published_media(
    metadata_session_factory, screen_repository, tmp_path
) -> None:
    service = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory), assets_dir=tmp_path
    )
    old = await service.upload(
        filename="avatar.png", content_type="image/png", content=image_bytes()
    )
    screen = await screen_repository.create("Published avatar", picture_document(old.id))
    publishing = PublishingService(
        screen_repository=screen_repository,
        dataset_repository=DatasetLookup(),
        asset_service=service,
    )
    await publishing.publish(screen.id, 0)
    new = await service.upload(
        filename="updated.png",
        content_type="image/png",
        content=image_bytes(color="#f00000"),
        replaces=old.id,
    )
    assert new.id != old.id
    assert new.family_id == old.id and new.version == 2
    assert (await screen_repository.get(screen.id)).published_document == picture_document(old.id)
    await screen_repository.save_draft(
        screen.id, document=picture_document(new.id), expected_revision=0
    )
    refs = await service.references(old.id)
    assert refs[0].in_published and not refs[0].in_draft
    with pytest.raises(AssetInUse):
        await service.delete(old.id)
    with pytest.raises(AssetInvalid):
        await service.upload(
            filename="broken.png", content_type="image/png", content=b"broken", replaces=old.id
        )
    assert Path(old.storage_path).read_bytes() == image_bytes()


@pytest.mark.anyio
async def test_same_content_versions_share_files_until_the_last_reference_is_deleted(
    metadata_session_factory, tmp_path
) -> None:
    service = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory), assets_dir=tmp_path
    )
    old = await service.upload(
        filename="avatar.png", content_type="image/png", content=image_bytes()
    )
    new = await service.upload(
        filename="new.png", content_type="image/png", content=image_bytes(), replaces=old.id
    )
    assert new.id != old.id and new.storage_path == old.storage_path
    await service.delete(old.id)
    assert Path(new.storage_path).is_file()
    assert (await service.thumbnail(new.id)).is_file()
    await service.delete(new.id)
    assert not Path(new.storage_path).exists()
    assert not Path(new.thumbnail_path).exists()


@pytest.mark.anyio
async def test_version_order_does_not_depend_on_the_system_clock(
    metadata_session_factory, tmp_path
) -> None:
    service = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory), assets_dir=tmp_path
    )
    old = await service.upload(
        filename="avatar.png", content_type="image/png", content=image_bytes()
    )
    new = await service.upload(
        filename="next.png", content_type="image/png", content=image_bytes(), replaces=old.id
    )
    async with metadata_session_factory.begin() as session:
        await session.execute(
            update(ScreenAssetRecord)
            .where(ScreenAssetRecord.id == new.id)
            .values(created_at=datetime(2020, 1, 1, tzinfo=UTC))
        )
    latest = await service.upload(
        filename="latest.png", content_type="image/png", content=image_bytes(), replaces=old.id
    )
    assert latest.version == 3
    assert [asset.version for asset in await service.list(family_id=old.family_id)] == [3, 2, 1]


@pytest.mark.anyio
async def test_id_collision_never_deletes_an_existing_file(
    metadata_session_factory, tmp_path
) -> None:
    service = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory),
        assets_dir=tmp_path,
        id_factory=lambda: "same-id",
    )
    old = await service.upload(
        filename="avatar.png", content_type="image/png", content=image_bytes()
    )
    with pytest.raises(FileExistsError):
        await service.upload(
            filename="other.png", content_type="image/png", content=image_bytes(color="#f00000")
        )
    assert Path(old.storage_path).read_bytes() == image_bytes()


@pytest.mark.anyio
async def test_missing_files_and_wrong_media_types_fail_publication(
    metadata_session_factory, tmp_path
) -> None:
    service = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory), assets_dir=tmp_path
    )
    audio = await service.upload(
        filename="speech.wav", content_type="audio/wav", content=wav_bytes()
    )
    with pytest.raises(AssetInvalid, match="type"):
        await service.assert_references_exist(picture_document(audio.id))
    Path(audio.storage_path).unlink()
    with pytest.raises(AssetNotFound):
        await service.assert_references_exist(picture_document(audio.id))


@pytest.mark.anyio
async def test_publish_and_delete_share_a_mutation_guard(
    metadata_session_factory, screen_repository, tmp_path
) -> None:
    service = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory), assets_dir=tmp_path
    )
    asset = await service.upload(
        filename="avatar.png", content_type="image/png", content=image_bytes()
    )
    screen = await screen_repository.create("Race", picture_document(asset.id))
    entered, release = asyncio.Event(), asyncio.Event()

    class PausingRepository:
        get = screen_repository.get

        async def publish(self, *args, **kwargs):
            entered.set()
            await release.wait()
            return await screen_repository.publish(*args, **kwargs)

    publishing = PublishingService(
        screen_repository=PausingRepository(),
        dataset_repository=DatasetLookup(),
        asset_service=service,
    )
    task = asyncio.create_task(publishing.publish(screen.id, 0))
    await entered.wait()
    deletion = asyncio.create_task(service.delete(asset.id))
    await asyncio.sleep(0)
    assert not deletion.done()
    release.set()
    await task
    with pytest.raises(AssetInUse):
        await deletion
    assert Path(asset.storage_path).is_file()


def test_management_api_is_authenticated_and_keeps_paths_private(tmp_path) -> None:
    with build_test_app(tmp_path) as app:
        for path in (
            "usage",
            "expiring",
            "missing/metadata",
            "missing/references",
            "missing/thumbnail",
        ):
            assert app.client.get("/api/admin/assets/" + path).status_code == 401
        setup_admin(app)
        response = app.client.post(
            "/api/admin/assets",
            files={"file": ("avatar.png", image_bytes(), "image/png")},
            headers=mutation_headers(app),
        )
        assert response.status_code == 201
        asset = response.json()
        assert asset["media"]["width"] == 32 and asset["media"]["height"] == 24
        assert asset["uploaded_by"] == "admin"
        assert "storage_path" not in asset and "thumbnail_path" not in asset
        base = "/api/admin/assets/" + asset["id"]
        assert app.client.patch(base + "/metadata", json={"name": "Renamed"}).status_code == 403
        updated = app.client.patch(
            base + "/metadata",
            json={
                "name": "Renamed",
                "license_note": "Owned by test",
                "license_expires_at": "2028-01-01T00:00:00Z",
            },
            headers=mutation_headers(app),
        )
        assert updated.status_code == 200 and updated.json()["name"] == "Renamed"
        expiring = app.client.get(
            "/api/admin/assets/expiring?within_days=3650&limit=10"
        )
        assert expiring.status_code == 200
        assert [item["id"] for item in expiring.json()] == [asset["id"]]
        assert (
            app.client.get("/api/admin/assets?search=renamed&asset_type=image").json()[0]["id"]
            == asset["id"]
        )
        assert app.client.get("/api/admin/assets?search=%25").json() == []
        assert app.client.get("/api/admin/assets?asset_type=audio").json() == []
        assert app.client.get(base + "/thumbnail").headers["content-type"] == "image/png"
        assert app.client.get(base + "/references").json() == []
        audio_response = app.client.post(
            "/api/admin/assets",
            files={"file": ("speech.wav", wav_bytes(), "audio/wav")},
            headers=mutation_headers(app),
        )
        assert audio_response.status_code == 201
        audio_id = audio_response.json()["id"]
        preview = app.client.get(
            f"/api/admin/assets/{audio_id}/preview?normalize_loudness=true&trim_silence=true"
        )
        assert preview.status_code == 200
        assert preview.headers["content-type"].startswith("audio/mpeg")
        assert "storage_path" not in preview.text
        replacement = app.client.post(
            base + "/versions",
            files={"file": ("next.png", image_bytes(color="#f00000"), "image/png")},
            headers=mutation_headers(app),
        )
        assert replacement.status_code == 201 and replacement.json()["version"] == 2
        assert len(app.client.get("/api/admin/assets?family_id=" + asset["family_id"]).json()) == 2
        assert app.client.get("/api/admin/assets/usage").json()["asset_count"] == 3


@pytest.mark.parametrize(
    "payload",
    [{"name": " "}, {"name": "line\nbreak"}, {"license_expires_at": "2028-01-01T00:00:00"}],
)
def test_invalid_asset_labels_and_expiry_are_rejected(payload) -> None:
    with pytest.raises(ValueError):
        ScreenAssetPatch.model_validate(payload)


@pytest.mark.anyio
async def test_project_processing_limit_is_shared_with_other_worker_processes(
    metadata_session_factory, tmp_path
) -> None:
    service = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory),
        assets_dir=tmp_path,
        inspector=MediaInspector(MediaLimits(concurrency=1)),
    )
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        "import sys\nfrom filelock import FileLock\n"
        "with FileLock(sys.argv[1]):\n print('ready', flush=True)\n sys.stdin.read()\n",
        str(tmp_path / ".media-slot-0.lock"),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        assert await asyncio.wait_for(process.stdout.readline(), timeout=5) == b"ready\n"
        with pytest.raises(MediaBusy, match="project media processing"):
            await service.upload(
                filename="avatar.png", content_type="image/png", content=image_bytes()
            )
        process.stdin.close()
        await asyncio.wait_for(process.wait(), timeout=5)
        uploaded = await service.upload(
            filename="avatar.png", content_type="image/png", content=image_bytes()
        )
        assert uploaded.media.validated
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()


@pytest.mark.anyio
async def test_quota_counts_thumbnail_bytes_once_across_shared_versions(
    metadata_session_factory, tmp_path
) -> None:
    service = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory), assets_dir=tmp_path
    )
    first = await service.upload(
        filename="avatar.png", content_type="image/png", content=image_bytes()
    )
    expected = Path(first.storage_path).stat().st_size + Path(first.thumbnail_path).stat().st_size
    assert (await service.usage()).size_bytes == expected
    new = await service.upload(
        filename="next.png", content_type="image/png", content=image_bytes(), replaces=first.id
    )
    assert (await service.usage()).size_bytes == expected
    await service.delete(first.id)
    assert (await service.usage()).size_bytes == expected
    await service.delete(new.id)
    assert (await service.usage()).size_bytes == 0


@pytest.mark.anyio
@pytest.mark.parametrize(
    "limits", [AssetLimits(total_duration_seconds=0.4), AssetLimits(max_count=1)]
)
async def test_duration_and_record_quotas_are_enforced(
    metadata_session_factory, tmp_path, limits
) -> None:
    service = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory),
        assets_dir=tmp_path,
        limits=limits,
    )
    first = await service.upload(
        filename="speech.wav", content_type="audio/wav", content=wav_bytes()
    )
    with pytest.raises(AssetQuotaExceeded):
        await service.upload(
            filename="other.wav", content_type="audio/wav", content=wav_bytes(seconds=0.3)
        )
    assert (await service.usage()).asset_count == 1
    assert (await service.get(first.id)).media.duration_seconds == 0.25


@pytest.mark.anyio
async def test_legacy_assets_are_revalidated_and_unknown_mime_is_rejected(
    metadata_session_factory, tmp_path
) -> None:
    service = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory), assets_dir=tmp_path
    )
    asset = await service.upload(
        filename="avatar.png", content_type="image/png", content=image_bytes()
    )
    async with metadata_session_factory.begin() as session:
        await session.execute(
            update(ScreenAssetRecord).where(ScreenAssetRecord.id == asset.id).values(media_json={})
        )
    await service.assert_references_exist(picture_document(asset.id))
    async with metadata_session_factory.begin() as session:
        await session.execute(
            update(ScreenAssetRecord)
            .where(ScreenAssetRecord.id == asset.id)
            .values(mime_type="image/unsupported")
        )
    with pytest.raises(AssetInvalid, match="unsupported"):
        await service.assert_references_exist(picture_document(asset.id))
