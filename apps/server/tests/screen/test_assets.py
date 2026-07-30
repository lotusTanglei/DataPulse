import hashlib
from collections.abc import Iterator
from pathlib import Path

import pytest

from datapulse.contracts.dashboard import ComponentInstance, DashboardDocument, Frame
from datapulse.screen.assets import (
    MAX_ASSET_BYTES,
    AssetInUse,
    AssetInvalid,
    AssetNotFound,
    AssetService,
    AssetTooLarge,
    ScreenAssetRepository,
)
from datapulse.screen.repository import ScreenRepository
from tests.support.app import AppClient, build_test_app

pytestmark = pytest.mark.anyio

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"safe-png"
JPEG_BYTES = b"\xff\xd8\xff" + b"safe-jpeg"
WEBP_BYTES = b"RIFF\x08\x00\x00\x00WEBP" + b"safe-webp"
GEOJSON_BYTES = b'{"type":"FeatureCollection","features":[]}'


@pytest.fixture
def assets_dir(tmp_path: Path) -> Path:
    return tmp_path / "assets"


@pytest.fixture
def asset_service(metadata_session_factory, assets_dir: Path) -> AssetService:
    return AssetService(
        repository=ScreenAssetRepository(metadata_session_factory),
        assets_dir=assets_dir,
        id_factory=lambda: "asset-1",
    )


async def test_upload_accepts_supported_assets_and_uses_generated_path(
    asset_service: AssetService,
    assets_dir: Path,
) -> None:
    uploaded = await asset_service.upload(
        filename="../../logo.png",
        content_type="image/png",
        content=PNG_BYTES,
    )

    assert uploaded.id == "asset-1"
    assert uploaded.asset_type == "image"
    assert uploaded.mime_type == "image/png"
    assert uploaded.size_bytes == len(PNG_BYTES)
    assert uploaded.sha256 == hashlib.sha256(PNG_BYTES).hexdigest()
    assert Path(uploaded.storage_path).parent == assets_dir.resolve()
    assert Path(uploaded.storage_path).name == "asset-1.png"
    assert ".." not in Path(uploaded.storage_path).parts
    assert Path(uploaded.storage_path).read_bytes() == PNG_BYTES
    assert await asset_service.get(uploaded.id) == uploaded


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("photo.jpg", "image/jpeg", JPEG_BYTES),
        ("texture.webp", "image/webp", WEBP_BYTES),
        ("regions.geojson", "application/geo+json", GEOJSON_BYTES),
    ],
)
async def test_upload_accepts_each_supported_format(
    metadata_session_factory,
    assets_dir: Path,
    filename: str,
    content_type: str,
    content: bytes,
) -> None:
    service = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory),
        assets_dir=assets_dir,
    )
    uploaded = await service.upload(
        filename=filename,
        content_type=content_type,
        content=content,
    )
    assert Path(uploaded.storage_path).is_file()


async def test_geojson_upload_rejects_non_feature_collection(
    asset_service: AssetService,
) -> None:
    with pytest.raises(AssetInvalid, match="FeatureCollection"):
        await asset_service.upload(
            filename="../../map.geojson",
            content_type="application/geo+json",
            content=b'{"type":"Point","coordinates":[0,0]}',
        )


async def test_upload_rejects_spoofed_images_and_svg(
    asset_service: AssetService,
) -> None:
    with pytest.raises(AssetInvalid):
        await asset_service.upload(
            filename="fake.png",
            content_type="image/png",
            content=b"<svg></svg>",
        )
    with pytest.raises(AssetInvalid):
        await asset_service.upload(
            filename="logo.svg",
            content_type="image/svg+xml",
            content=b"<svg></svg>",
        )


async def test_upload_enforces_five_mib_boundary(
    metadata_session_factory,
    assets_dir: Path,
) -> None:
    service = AssetService(
        repository=ScreenAssetRepository(metadata_session_factory),
        assets_dir=assets_dir,
    )
    exact = PNG_BYTES + bytes(MAX_ASSET_BYTES - len(PNG_BYTES))
    uploaded = await service.upload(
        filename="large.png",
        content_type="image/png",
        content=exact,
    )
    assert uploaded.size_bytes == MAX_ASSET_BYTES

    with pytest.raises(AssetTooLarge):
        await service.upload(
            filename="too-large.png",
            content_type="image/png",
            content=exact + b"x",
        )


async def test_delete_rejects_assets_referenced_by_screen_documents(
    asset_service: AssetService,
    screen_repository: ScreenRepository,
) -> None:
    uploaded = await asset_service.upload(
        filename="logo.png",
        content_type="image/png",
        content=PNG_BYTES,
    )
    document = DashboardDocument(
        canvas={"width": 1920, "height": 1080},
        components=(
            ComponentInstance(
                id="image-1",
                type="builtin.image",
                frame=Frame(x=0, y=0, width=320, height=180),
                props={"asset_id": uploaded.id},
            ),
        ),
    )
    await screen_repository.create("Operations", document)

    with pytest.raises(AssetInUse):
        await asset_service.delete(uploaded.id)


async def test_assert_references_exist_and_delete_unreferenced_asset(
    asset_service: AssetService,
) -> None:
    uploaded = await asset_service.upload(
        filename="logo.png",
        content_type="image/png",
        content=PNG_BYTES,
    )
    document = DashboardDocument(
        canvas={"width": 1920, "height": 1080},
        components=(
            ComponentInstance(
                id="image-1",
                type="builtin.image",
                frame=Frame(x=0, y=0, width=320, height=180),
                props={"asset_id": uploaded.id},
            ),
        ),
    )
    await asset_service.assert_references_exist(document)

    missing = document.model_copy(
        update={
            "components": (
                document.components[0].model_copy(update={"props": {"asset_id": "missing"}}),
            )
        }
    )
    with pytest.raises(AssetNotFound):
        await asset_service.assert_references_exist(missing)

    empty = DashboardDocument(canvas={"width": 1920, "height": 1080})
    await asset_service.assert_references_exist(empty)
    await asset_service.delete(uploaded.id)
    assert not Path(uploaded.storage_path).exists()
    with pytest.raises(AssetNotFound):
        await asset_service.get(uploaded.id)


@pytest.fixture
def asset_app(tmp_path: Path) -> Iterator[AppClient]:
    with build_test_app(tmp_path) as app_client:
        yield app_client


def setup_admin(app_client: AppClient) -> None:
    response = app_client.client.post(
        "/api/auth/setup",
        json={
            "code": app_client.setup_code,
            "username": "admin",
            "password": "long-enough-password",
        },
        headers={"Origin": app_client.origin},
    )
    assert response.status_code == 201


def mutation_headers(app_client: AppClient) -> dict[str, str]:
    return {
        "Origin": app_client.origin,
        "X-CSRF-Token": app_client.client.cookies["datapulse_csrf"],
    }


def test_asset_api_upload_get_delete_and_security_headers(asset_app: AppClient) -> None:
    assert asset_app.client.get("/api/admin/assets/missing").status_code == 401
    setup_admin(asset_app)

    created = asset_app.client.post(
        "/api/admin/assets",
        files={"file": ("../../logo.png", PNG_BYTES, "image/png")},
        headers=mutation_headers(asset_app),
    )
    assert created.status_code == 201
    payload = created.json()
    assert "storage_path" not in payload

    fetched = asset_app.client.get(f"/api/admin/assets/{payload['id']}")
    assert fetched.status_code == 200
    assert fetched.content == PNG_BYTES
    assert fetched.headers["content-type"] == "image/png"
    assert fetched.headers["content-disposition"].startswith("inline")
    assert fetched.headers["x-content-type-options"] == "nosniff"
    assert fetched.headers["etag"] == f'"{payload["sha256"]}"'

    deleted = asset_app.client.delete(
        f"/api/admin/assets/{payload['id']}",
        headers=mutation_headers(asset_app),
    )
    assert deleted.status_code == 204
    assert asset_app.client.get(f"/api/admin/assets/{payload['id']}").status_code == 404


def test_asset_api_rejects_oversized_upload(asset_app: AppClient) -> None:
    setup_admin(asset_app)
    oversized = PNG_BYTES + bytes(MAX_ASSET_BYTES + 1 - len(PNG_BYTES))

    response = asset_app.client.post(
        "/api/admin/assets",
        files={"file": ("large.png", oversized, "image/png")},
        headers=mutation_headers(asset_app),
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "ASSET_TOO_LARGE"
