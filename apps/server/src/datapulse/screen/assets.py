import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from datapulse.contracts.dashboard import DashboardDocument
from datapulse.metadata import ScreenAssetRecord, ScreenRecord

MAX_ASSET_BYTES = 5 * 1024 * 1024

_FORMATS = {
    "image/png": ("image", ".png"),
    "image/jpeg": ("image", ".jpg"),
    "image/webp": ("image", ".webp"),
    "application/geo+json": ("geojson", ".geojson"),
    "application/json": ("geojson", ".geojson"),
}


class AssetNotFound(LookupError):
    pass


class AssetInvalid(ValueError):
    code = "ASSET_INVALID"


class AssetTooLarge(ValueError):
    code = "ASSET_TOO_LARGE"


class AssetInUse(ValueError):
    code = "ASSET_IN_USE"


class StoredScreenAsset(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    asset_type: Literal["image", "geojson"]
    mime_type: str
    sha256: str
    size_bytes: int
    storage_path: str
    created_at: datetime


class ScreenAssetResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    asset_type: Literal["image", "geojson"]
    mime_type: str
    sha256: str
    size_bytes: int
    created_at: datetime

    @classmethod
    def from_stored(cls, asset: StoredScreenAsset) -> "ScreenAssetResponse":
        return cls.model_validate(asset.model_dump(exclude={"storage_path"}))


def _contains_asset_reference(value: object, asset_id: str) -> bool:
    if isinstance(value, Mapping):
        if value.get("asset_id") == asset_id:
            return True
        return any(_contains_asset_reference(item, asset_id) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_asset_reference(item, asset_id) for item in value)
    return False


def _collect_asset_references(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        asset_id = value.get("asset_id")
        if isinstance(asset_id, str):
            found.add(asset_id)
        for item in value.values():
            found.update(_collect_asset_references(item))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            found.update(_collect_asset_references(item))
    return found


class ScreenAssetRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _to_asset(record: ScreenAssetRecord) -> StoredScreenAsset:
        return StoredScreenAsset(
            id=record.id,
            asset_type=record.asset_type,
            mime_type=record.mime_type,
            sha256=record.sha256,
            size_bytes=record.size_bytes,
            storage_path=record.storage_path,
            created_at=record.created_at,
        )

    async def create(
        self,
        *,
        asset_id: str,
        asset_type: str,
        mime_type: str,
        sha256: str,
        size_bytes: int,
        storage_path: str,
    ) -> StoredScreenAsset:
        record = ScreenAssetRecord(
            id=asset_id,
            asset_type=asset_type,
            mime_type=mime_type,
            sha256=sha256,
            size_bytes=size_bytes,
            storage_path=storage_path,
        )
        async with self._session_factory.begin() as session:
            session.add(record)
            await session.flush()
        return self._to_asset(record)

    async def get(self, asset_id: str) -> StoredScreenAsset:
        async with self._session_factory() as session:
            record = await session.get(ScreenAssetRecord, asset_id)
        if record is None:
            raise AssetNotFound(asset_id)
        return self._to_asset(record)

    async def existing_ids(self, asset_ids: set[str]) -> set[str]:
        if not asset_ids:
            return set()
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(ScreenAssetRecord.id).where(ScreenAssetRecord.id.in_(asset_ids))
            )
            return set(rows)

    async def is_referenced(self, asset_id: str) -> bool:
        async with self._session_factory() as session:
            records = (
                await session.scalars(
                    select(ScreenRecord).where(
                        (ScreenRecord.draft_document.is_not(None))
                        | (ScreenRecord.published_document.is_not(None))
                    )
                )
            ).all()
        return any(
            _contains_asset_reference(record.draft_document, asset_id)
            or _contains_asset_reference(record.published_document, asset_id)
            for record in records
        )

    async def delete(self, asset_id: str) -> None:
        async with self._session_factory.begin() as session:
            result = await session.execute(
                delete(ScreenAssetRecord).where(ScreenAssetRecord.id == asset_id)
            )
            if not result.rowcount:
                raise AssetNotFound(asset_id)


def _validate_content(mime_type: str, content: bytes) -> None:
    if mime_type == "image/png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise AssetInvalid("The file is not a valid PNG image.")
    if mime_type == "image/jpeg" and not content.startswith(b"\xff\xd8\xff"):
        raise AssetInvalid("The file is not a valid JPEG image.")
    if mime_type == "image/webp" and not (
        len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    ):
        raise AssetInvalid("The file is not a valid WebP image.")
    if mime_type in {"application/geo+json", "application/json"}:
        try:
            payload = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AssetInvalid("The file is not valid GeoJSON.") from error
        if payload.get("type") != "FeatureCollection" or not isinstance(
            payload.get("features"), list
        ):
            raise AssetInvalid("GeoJSON must be a FeatureCollection.")


class AssetService:
    def __init__(
        self,
        *,
        repository: ScreenAssetRepository,
        assets_dir: Path,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._assets_dir = assets_dir.resolve()
        self._id_factory = id_factory or (lambda: str(uuid4()))

    async def upload(
        self,
        *,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> StoredScreenAsset:
        del filename
        mime_type = content_type.partition(";")[0].strip().lower()
        file_format = _FORMATS.get(mime_type)
        if file_format is None:
            raise AssetInvalid("The asset format is not supported.")
        if len(content) > MAX_ASSET_BYTES:
            raise AssetTooLarge("Assets cannot exceed 5 MiB.")
        _validate_content(mime_type, content)

        asset_type, extension = file_format
        asset_id = self._id_factory()
        self._assets_dir.mkdir(parents=True, exist_ok=True)
        storage_path = (self._assets_dir / f"{asset_id}{extension}").resolve()
        if not storage_path.is_relative_to(self._assets_dir):
            raise AssetInvalid("The generated asset path is invalid.")
        try:
            with storage_path.open("xb") as file:
                file.write(content)
            return await self._repository.create(
                asset_id=asset_id,
                asset_type=asset_type,
                mime_type=mime_type,
                sha256=hashlib.sha256(content).hexdigest(),
                size_bytes=len(content),
                storage_path=str(storage_path),
            )
        except Exception:
            storage_path.unlink(missing_ok=True)
            raise

    async def get(self, asset_id: str) -> StoredScreenAsset:
        asset = await self._repository.get(asset_id)
        if not Path(asset.storage_path).is_file():
            raise AssetNotFound(asset_id)
        return asset

    async def delete(self, asset_id: str) -> None:
        asset = await self._repository.get(asset_id)
        if await self._repository.is_referenced(asset_id):
            raise AssetInUse(asset_id)
        await self._repository.delete(asset_id)
        Path(asset.storage_path).unlink(missing_ok=True)

    async def assert_references_exist(self, document: DashboardDocument) -> None:
        references = _collect_asset_references(document.model_dump(mode="json"))
        existing = await self._repository.existing_ids(references)
        missing = references - existing
        if missing:
            raise AssetNotFound(sorted(missing)[0])


__all__ = [
    "MAX_ASSET_BYTES",
    "AssetInUse",
    "AssetInvalid",
    "AssetNotFound",
    "AssetService",
    "AssetTooLarge",
    "ScreenAssetRepository",
    "ScreenAssetResponse",
    "StoredScreenAsset",
]
