import pytest

from datapulse.contracts.dashboard import DashboardDocument
from datapulse.screen.assets import (
    AssetInUse,
    AssetService,
    ScreenAssetRepository,
    collect_asset_references,
)
from datapulse.screen.publishing import PublishingService, PublishValidationError
from datapulse.screen.repository import ScreenRepository
from tests.screen.test_publishing import DatasetLookup
from tests.support.media import image_bytes, wav_bytes

pytestmark = pytest.mark.anyio


def document(source_id: str = "kpi", variable: str = "sales.value") -> DashboardDocument:
    return DashboardDocument.model_validate(
        {
            "canvas": {"width": 1920, "height": 1080},
            "components": [
                {
                    "id": "kpi",
                    "type": "builtin.kpi",
                    "frame": {"x": 0, "y": 0, "width": 300, "height": 200},
                    "data_binding": {
                        "source": "static",
                        "static_data": {
                            "columns": [{"name": "amount", "data_type": "number"}],
                            "rows": [[1234]],
                        },
                    },
                },
                {
                    "id": "speaker",
                    "type": "builtin.digital_human",
                    "frame": {"x": 400, "y": 0, "width": 320, "height": 420},
                    "props": {"speech_template": "{{sales.value | number}}"},
                    "data_binding": {
                        "source": "components",
                        "variables": [
                            {"name": variable, "component_id": source_id, "field": "amount"},
                        ],
                    },
                },
            ],
        }
    )


async def test_published_digital_human_is_a_snapshot_with_validated_references(
    screen_repository: ScreenRepository,
    metadata_session_factory,
    tmp_path,
) -> None:
    assets = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory), assets_dir=tmp_path / "assets"
    )
    service = PublishingService(
        screen_repository=screen_repository,
        dataset_repository=DatasetLookup(),
        asset_service=assets,
    )
    created = await screen_repository.create("Broadcast", document())
    published = await service.publish(created.id, 0)
    assert published.published_document == document()
    await screen_repository.save_draft(
        created.id, document=document("missing"), expected_revision=0
    )
    with pytest.raises(PublishValidationError, match="source component"):
        await service.publish(created.id, 1)
    assert (
        await screen_repository.get(created.id)
    ).published_document == published.published_document


@pytest.mark.parametrize(
    ("source_id", "variable"),
    [
        ("speaker", "sales.value"),
        ("kpi", "unbound"),
        ("missing", "sales.value"),
    ],
)
async def test_invalid_dependencies_fail_before_publication(
    screen_repository: ScreenRepository,
    metadata_session_factory,
    tmp_path,
    source_id: str,
    variable: str,
) -> None:
    assets = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory), assets_dir=tmp_path / "assets"
    )
    service = PublishingService(
        screen_repository=screen_repository,
        dataset_repository=DatasetLookup(),
        asset_service=assets,
    )
    created = await screen_repository.create("Broadcast", document(source_id, variable))
    with pytest.raises(PublishValidationError):
        await service.publish(created.id, 0)


async def test_condition_group_variables_must_be_bound_before_publication(
    screen_repository: ScreenRepository,
    metadata_session_factory,
    tmp_path,
) -> None:
    assets = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory), assets_dir=tmp_path / "assets"
    )
    service = PublishingService(
        screen_repository=screen_repository,
        dataset_repository=DatasetLookup(),
        asset_service=assets,
    )
    draft = document().model_dump(mode="json")
    draft["components"][1]["props"] = {
        "speech_template": "{{sales.value}}",
        "trigger": {
            "kind": "threshold",
            "conditions": [{"variable": "not_bound", "operator": "gt", "value": 1}],
        },
    }
    screen = await screen_repository.create("Conditions", DashboardDocument.model_validate(draft))
    with pytest.raises(PublishValidationError, match="condition variable"):
        await service.publish(screen.id, 0)


async def test_all_digital_human_media_references_are_protected(
    screen_repository: ScreenRepository,
    metadata_session_factory,
    tmp_path,
) -> None:
    assets = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory), assets_dir=tmp_path / "assets"
    )
    image = await assets.upload(
        filename="avatar.png", content_type="image/png", content=image_bytes()
    )
    draft = document().model_dump(mode="json")
    draft["components"][1]["props"]["avatar_asset_id"] = image.id
    screen = await screen_repository.create("Broadcast", DashboardDocument.model_validate(draft))
    await screen_repository.publish(screen.id, document=screen.draft_document, expected_revision=0)
    await screen_repository.save_draft(screen.id, document=document(), expected_revision=0)
    with pytest.raises(AssetInUse):
        await assets.delete(image.id)
    assert collect_asset_references(
        {
            "avatar_asset_id": "avatar",
            "speaking_asset_id": "speaking",
            "audio_asset_id": "audio",
            "nested": {"asset_id": "old"},
            "empty": {"asset_id": ""},
        }
    ) == {"avatar", "speaking", "audio", "old"}


@pytest.mark.parametrize(
    "fault", [None, "unconfirmed", "hash", "duration", "subtitle", "source", "wrong_id"]
)
async def test_publication_validates_recorded_media_and_subtitle_snapshot(
    screen_repository,
    metadata_session_factory,
    tmp_path,
    fault,
) -> None:
    assets = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory), assets_dir=tmp_path / "assets"
    )
    audio = await assets.upload(
        filename="voice.wav", content_type="audio/wav", content=wav_bytes(2)
    )
    subtitle = await assets.upload(
        filename="captions.vtt",
        content_type="text/vtt",
        content=b"WEBVTT\n\n00:00.125 --> 00:01.500\nHello\n",
    )
    recording = {
        "asset_id": audio.id,
        "sha256": audio.sha256,
        "transcript": "Hello",
        "duration_seconds": audio.media.duration_seconds,
        "subtitle_asset_id": subtitle.id,
        "subtitle_sha256": subtitle.sha256,
        "cues": [cue.model_dump() for cue in subtitle.media.cues],
    }
    if fault == "hash":
        recording["sha256"] = "0" * 64
    elif fault == "duration":
        recording["duration_seconds"] = 3
    elif fault == "subtitle":
        recording["cues"][0]["start"] = 0.25
    elif fault == "wrong_id":
        recording["asset_id"] = subtitle.id
    draft = document().model_dump(mode="json")
    draft["components"][1]["data_binding"] = {}
    draft["components"][1]["props"] = {
        "speech_template": "Hello",
        "audio_asset_id": audio.id,
        "speech_source": "video" if fault == "source" else "audio",
        "recording": None if fault == "unconfirmed" else recording,
    }
    service = PublishingService(
        screen_repository=screen_repository,
        dataset_repository=DatasetLookup(),
        asset_service=assets,
    )
    screen = await screen_repository.create("Recorded", DashboardDocument.model_validate(draft))
    if fault:
        with pytest.raises(PublishValidationError):
            await service.publish(screen.id, 0)
        assert (await screen_repository.get(screen.id)).published_document is None
    else:
        published = await service.publish(screen.id, 0)
        assert published.published_document.components[1].props["recording"] == recording
        await screen_repository.save_draft(screen.id, document=document(), expected_revision=0)
        with pytest.raises(AssetInUse):
            await assets.delete(subtitle.id)


async def test_condition_mapped_recordings_are_published_and_protected(
    screen_repository,
    metadata_session_factory,
    tmp_path,
) -> None:
    assets = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory), assets_dir=tmp_path / "assets"
    )
    low = await assets.upload(
        filename="low.wav", content_type="audio/wav", content=wav_bytes(1)
    )
    high = await assets.upload(
        filename="high.wav", content_type="audio/wav", content=wav_bytes(2, rate=8000)
    )
    draft = document().model_dump(mode="json")
    draft["components"][1]["props"] = {
        "speech_template": "{{sales.value | number}}",
        "speech_source": "audio",
        "recordings": [
            {
                "asset_id": low.id,
                "sha256": low.sha256,
                "transcript": "低",
                "duration_seconds": low.media.duration_seconds,
                "conditions": [{"variable": "sales.value", "operator": "lt", "value": 100}],
            },
            {
                "asset_id": high.id,
                "sha256": high.sha256,
                "transcript": "高",
                "duration_seconds": high.media.duration_seconds,
                "conditions": [{"variable": "sales.value", "operator": "gte", "value": 100}],
            },
        ],
    }
    draft["components"][1]["data_binding"]["variables"][0]["field"] = "amount"
    screen = await screen_repository.create(
        "Mapped recordings", DashboardDocument.model_validate(draft)
    )
    service = PublishingService(
        screen_repository=screen_repository,
        dataset_repository=DatasetLookup(),
        asset_service=assets,
    )
    published = await service.publish(screen.id, 0)
    assert len(published.published_document.components[1].props["recordings"]) == 2
    with pytest.raises(AssetInUse):
        await assets.delete(low.id)
