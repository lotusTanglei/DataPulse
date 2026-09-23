import hashlib
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath, PureWindowsPath
from uuid import uuid4

from filelock import AsyncFileLock, Timeout
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from datapulse.contracts.dashboard import DashboardDocument
from datapulse.contracts.digital_human import DigitalHumanSpec
from datapulse.contracts.screen_asset import (
    AssetMediaMetadata,
    AssetType,
    ScreenAssetPatch,
    ScreenAssetReference,
    ScreenAssetResponse,
    ScreenAssetUsage,
)
from datapulse.errors import DataPulseError
from datapulse.metadata import DigitalHumanAuditRecord, ScreenAssetRecord, ScreenRecord
from datapulse.metadata.models import utc_now
from datapulse.screen.media import InspectedMedia, MediaBusy, MediaInspector, MediaInvalid

MAX_ASSET_BYTES = 5 * 1024 * 1024
ASSET_REFERENCE_KEYS = {
    "asset_id",
    "avatar_asset_id",
    "speaking_asset_id",
    "audio_asset_id",
    "subtitle_asset_id",
}
_FORMATS: dict[str, tuple[AssetType, str, set[str]]] = {
    "image/png": ("image", ".png", {".png"}),
    "image/jpeg": ("image", ".jpg", {".jpg", ".jpeg"}),
    "image/webp": ("image", ".webp", {".webp"}),
    "application/geo+json": ("geojson", ".geojson", {".geojson", ".json"}),
    "application/json": ("geojson", ".geojson", {".geojson", ".json"}),
    "audio/mpeg": ("audio", ".mp3", {".mp3"}),
    "audio/ogg": ("audio", ".ogg", {".ogg", ".oga"}),
    "audio/wav": ("audio", ".wav", {".wav"}),
    "video/mp4": ("video", ".mp4", {".mp4"}),
    "video/webm": ("video", ".webm", {".webm"}),
    "text/vtt": ("subtitle", ".vtt", {".vtt"}),
}


class AssetNotFound(LookupError):
    pass


AssetInvalid = MediaInvalid


class AssetTooLarge(ValueError):
    code = "ASSET_TOO_LARGE"


class AssetInUse(ValueError):
    code = "ASSET_IN_USE"


class AssetQuotaExceeded(ValueError):
    code = "ASSET_QUOTA_EXCEEDED"


class AssetScanRejected(AssetInvalid):
    code = "ASSET_SCAN_REJECTED"


AssetScanner = Callable[[bytes, str, str], Awaitable[bool]]


@dataclass(frozen=True)
class AssetLimits:
    image_bytes: int = MAX_ASSET_BYTES
    media_bytes: int = 100 * 1024 * 1024
    total_bytes: int = 1024 * 1024 * 1024
    total_duration_seconds: float = 36_000
    max_count: int = 10_000
    allowed_mime_types: frozenset[str] | None = field(default=None)


class StoredScreenAsset(ScreenAssetResponse):
    storage_path: str
    thumbnail_path: str | None = None

    def public(self) -> ScreenAssetResponse:
        return ScreenAssetResponse.model_validate(
            self.model_dump(exclude={"storage_path", "thumbnail_path"})
        )


def collect_asset_references(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key in ASSET_REFERENCE_KEYS:
            asset_id = value.get(key)
            if isinstance(asset_id, str) and asset_id:
                found.add(asset_id)
        for item in value.values():
            found.update(collect_asset_references(item))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            found.update(collect_asset_references(item))
    return found


class ScreenAssetRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _to_asset(record: ScreenAssetRecord) -> StoredScreenAsset:
        return StoredScreenAsset(
            id=record.id,
            name=record.name or record.id,
            original_name=record.original_name or record.id,
            asset_type=record.asset_type,
            mime_type=record.mime_type,
            sha256=record.sha256,
            size_bytes=record.size_bytes,
            storage_path=record.storage_path,
            thumbnail_path=record.thumbnail_path,
            family_id=record.family_id,
            version=record.version,
            media=AssetMediaMetadata.model_validate(record.media_json),
            has_thumbnail=bool(record.thumbnail_path),
            license_note=record.license_note,
            license_expires_at=record.license_expires_at,
            uploaded_by=record.uploaded_by,
            created_at=record.created_at,
        )

    async def create(self, **values: object) -> StoredScreenAsset:
        record = ScreenAssetRecord(**values)
        async with self._session_factory.begin() as session:
            session.add(record)
            await session.flush()
            session.add(
                DigitalHumanAuditRecord(
                    created_at=utc_now(),
                    actor="system",
                    action="asset.created",
                    resource_type="asset",
                    resource_id=record.id,
                    details_json={"asset_type": record.asset_type, "version": str(record.version)},
                )
            )
        return self._to_asset(record)

    async def get(self, asset_id: str) -> StoredScreenAsset:
        async with self._session_factory() as session:
            record = await session.get(ScreenAssetRecord, asset_id)
        if record is None:
            raise AssetNotFound(asset_id)
        return self._to_asset(record)

    async def find_hash(self, sha256: str, mime_type: str) -> StoredScreenAsset | None:
        async with self._session_factory() as session:
            record = await session.scalar(
                select(ScreenAssetRecord)
                .where(
                    ScreenAssetRecord.sha256 == sha256,
                    ScreenAssetRecord.mime_type == mime_type,
                )
                .order_by(ScreenAssetRecord.created_at, ScreenAssetRecord.id)
                .limit(1)
            )
        return self._to_asset(record) if record else None

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        search: str = "",
        asset_type: AssetType | None = None,
        family_id: str | None = None,
        visible_ids: set[str] | None = None,
    ) -> tuple[StoredScreenAsset, ...]:
        statement = select(ScreenAssetRecord)
        if visible_ids is not None:
            statement = statement.where(ScreenAssetRecord.id.in_(visible_ids))
        if search:
            statement = statement.where(ScreenAssetRecord.name.icontains(search, autoescape=True))
        if asset_type:
            statement = statement.where(ScreenAssetRecord.asset_type == asset_type)
        if family_id:
            statement = statement.where(ScreenAssetRecord.family_id == family_id)
            statement = statement.order_by(ScreenAssetRecord.version.desc())
        statement = (
            statement.order_by(
                ScreenAssetRecord.created_at.desc(),
                ScreenAssetRecord.version.desc(),
                ScreenAssetRecord.id,
            )
            .offset(offset)
            .limit(limit)
        )
        async with self._session_factory() as session:
            records = await session.scalars(statement)
            return tuple(self._to_asset(record) for record in records)

    async def expiring(
        self, *, cutoff: datetime, limit: int = 100, visible_ids: set[str] | None = None
    ) -> tuple[StoredScreenAsset, ...]:
        statement = (
            select(ScreenAssetRecord)
            .where(
                ScreenAssetRecord.license_expires_at.is_not(None),
                ScreenAssetRecord.license_expires_at <= cutoff,
            )
            .order_by(ScreenAssetRecord.license_expires_at, ScreenAssetRecord.id)
            .limit(limit)
        )
        if visible_ids is not None:
            statement = statement.where(ScreenAssetRecord.id.in_(visible_ids))
        async with self._session_factory() as session:
            records = await session.scalars(statement)
            return tuple(self._to_asset(record) for record in records)

    async def usage(self, *, visible_ids: set[str] | None = None) -> tuple[int, int, float]:
        async with self._session_factory() as session:
            records = (
                await session.execute(
                    select(
                        ScreenAssetRecord.storage_path,
                        ScreenAssetRecord.thumbnail_path,
                        ScreenAssetRecord.size_bytes,
                        ScreenAssetRecord.media_json,
                    ).where(True if visible_ids is None else ScreenAssetRecord.id.in_(visible_ids))
                )
            ).all()
        unique = {record.storage_path: record for record in records}
        thumbnails = {record.thumbnail_path: record for record in records if record.thumbnail_path}
        return (
            len(records),
            sum(record.size_bytes for record in unique.values())
            + sum(
                int(record.media_json.get("thumbnail_size_bytes") or 0)
                for record in thumbnails.values()
            ),
            sum(
                float(record.media_json.get("duration_seconds") or 0) for record in unique.values()
            ),
        )

    async def stored_paths(self) -> set[str]:
        async with self._session_factory() as session:
            records = await session.execute(
                select(ScreenAssetRecord.storage_path, ScreenAssetRecord.thumbnail_path)
            )
        return {
            str(path)
            for record in records.all()
            for path in record
            if path
        }

    @staticmethod
    async def _references(session: AsyncSession, asset_id: str) -> tuple[ScreenAssetReference, ...]:
        records = await session.scalars(select(ScreenRecord).order_by(ScreenRecord.name))
        references = []
        for record in records:
            draft = asset_id in collect_asset_references(record.draft_document)
            published = asset_id in collect_asset_references(record.published_document)
            if draft or published:
                references.append(
                    ScreenAssetReference(
                        screen_id=record.id,
                        screen_name=record.name,
                        in_draft=draft,
                        in_published=published,
                    )
                )
        return tuple(references)

    async def references(self, asset_id: str) -> tuple[ScreenAssetReference, ...]:
        async with self._session_factory() as session:
            return await self._references(session, asset_id)

    async def update(self, asset_id: str, patch: ScreenAssetPatch) -> StoredScreenAsset:
        async with self._session_factory.begin() as session:
            record = await session.get(ScreenAssetRecord, asset_id)
            if record is None:
                raise AssetNotFound(asset_id)
            for name, value in patch.model_dump(exclude_unset=True).items():
                if value is not None or name == "license_expires_at":
                    setattr(record, name, value)
            await session.flush()
            session.add(
                DigitalHumanAuditRecord(
                    created_at=utc_now(),
                    actor="system",
                    action="asset.updated",
                    resource_type="asset",
                    resource_id=asset_id,
                    details_json={"fields": ",".join(patch.model_dump(exclude_unset=True))},
                )
            )
        return self._to_asset(record)

    async def delete(self, asset_id: str) -> None:
        async with self._session_factory.begin() as session:
            record = await session.get(ScreenAssetRecord, asset_id)
            if record is None:
                raise AssetNotFound(asset_id)
            if await self._references(session, asset_id):
                raise AssetInUse(asset_id)
            session.add(
                DigitalHumanAuditRecord(
                    created_at=utc_now(),
                    actor="system",
                    action="asset.deleted",
                    resource_type="asset",
                    resource_id=asset_id,
                    details_json={},
                )
            )
            await session.delete(record)

    async def path_in_use(self, path: str) -> bool:
        async with self._session_factory() as session:
            return (
                await session.scalar(
                    select(ScreenAssetRecord.id)
                    .where(
                        (ScreenAssetRecord.storage_path == path)
                        | (ScreenAssetRecord.thumbnail_path == path),
                    )
                    .limit(1)
                )
                is not None
            )


class AssetService:
    def __init__(
        self,
        *,
        repository: ScreenAssetRepository,
        assets_dir: Path,
        id_factory: Callable[[], str] | None = None,
        limits: AssetLimits | None = None,
        inspector: MediaInspector | None = None,
        scanner: AssetScanner | None = None,
    ) -> None:
        self._repository = repository
        self._assets_dir = assets_dir.resolve()
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self.limits = limits or AssetLimits()
        self._inspector = inspector or MediaInspector()
        self._scanner = scanner

    def _lock(self) -> AsyncFileLock:
        self._assets_dir.mkdir(parents=True, exist_ok=True)
        return AsyncFileLock(str(self._assets_dir / ".asset-mutations.lock"), timeout=10)

    def publication_guard(self) -> AsyncFileLock:
        return self._lock()

    async def _inspect(self, content: bytes, mime_type: str, extension: str) -> InspectedMedia:
        self._assets_dir.mkdir(parents=True, exist_ok=True)
        # OS locks bound processing across all workers sharing this project's asset directory.
        for slot in range(self._inspector.limits.concurrency):
            lock = AsyncFileLock(str(self._assets_dir / f".media-slot-{slot}.lock"), timeout=0)
            try:
                await lock.acquire()
            except Timeout:
                continue
            try:
                return await self._inspector.inspect(content, mime_type, extension)
            finally:
                await lock.release()
        raise MediaBusy("The project media processing limit has been reached. Retry shortly.")

    def upload_limit(self, content_type: str) -> int:
        return (
            self.limits.media_bytes
            if content_type.partition(";")[0].strip().lower().startswith(("audio/", "video/"))
            else self.limits.image_bytes
        )

    def _path(self, value: str) -> Path:
        path = Path(value).resolve()
        if not path.is_relative_to(self._assets_dir) or path == self._assets_dir:
            raise AssetInvalid("The stored asset path is invalid.")
        return path

    async def upload(
        self,
        *,
        filename: str,
        content_type: str,
        content: bytes,
        replaces: str | None = None,
        uploaded_by: str = "",
        reuse_existing: bool = True,
    ) -> StoredScreenAsset:
        original_name = PurePosixPath(PureWindowsPath(filename).as_posix()).name
        if (
            not original_name
            or len(original_name) > 255
            or any(ord(char) < 32 for char in original_name)
        ):
            raise AssetInvalid("The asset filename is invalid.")
        mime_type = content_type.partition(";")[0].strip().lower()
        mime_type = {"audio/x-wav": "audio/wav", "application/json": "application/geo+json"}.get(
            mime_type, mime_type
        )
        if (
            self.limits.allowed_mime_types is not None
            and mime_type not in self.limits.allowed_mime_types
        ):
            raise AssetInvalid("The asset MIME type is disabled by the deployment allowlist.")
        file_format = _FORMATS.get(mime_type)
        if file_format is None:
            raise AssetInvalid("Use PNG/JPEG/WebP, MP4/WebM, MP3/OGG/WAV, WebVTT or GeoJSON.")
        asset_type, extension, suffixes = file_format
        if PurePosixPath(original_name).suffix.lower() not in suffixes:
            raise AssetInvalid("The filename extension does not match the media type.")
        if len(content) > self.upload_limit(mime_type):
            raise AssetTooLarge("The asset exceeds the configured upload limit.")
        if not content:
            raise AssetInvalid("The asset is empty.")
        if self._scanner is not None:
            try:
                clean = await self._scanner(content, mime_type, original_name)
            except DataPulseError:
                raise
            except Exception as error:
                raise AssetInvalid("The asset virus scan is unavailable.") from error
            if not clean:
                raise AssetScanRejected("The asset was rejected by the virus scan.")
        inspected = await self._inspect(content, mime_type, extension)
        sha256 = hashlib.sha256(content).hexdigest()
        try:
            async with self._lock():
                previous = await self._repository.get(replaces) if replaces else None
                if previous and previous.asset_type != asset_type:
                    raise AssetInvalid("A replacement must have the same asset type.")
                duplicate = await self._repository.find_hash(sha256, mime_type)
                if duplicate and not self._path(duplicate.storage_path).is_file():
                    duplicate = None
                if (
                    duplicate
                    and hashlib.sha256(self._path(duplicate.storage_path).read_bytes()).hexdigest()
                    != sha256
                ):
                    raise AssetInvalid("The stored duplicate failed its integrity check.")
                if duplicate and not previous and reuse_existing:
                    return duplicate
                count, size, duration = await self._repository.usage()
                extra_size = 0 if duplicate else len(content) + len(inspected.thumbnail or b"")
                extra_duration = 0 if duplicate else (inspected.metadata.duration_seconds or 0)
                if (
                    count >= self.limits.max_count
                    or size + extra_size > self.limits.total_bytes
                    or duration + extra_duration > self.limits.total_duration_seconds
                ):
                    raise AssetQuotaExceeded("The project asset quota has been reached.")
                asset_id = self._id_factory()
                family_id = previous.family_id if previous else asset_id
                versions = await self._repository.list(family_id=family_id, limit=1)
                version = (versions[0].version + 1) if versions else 1
                storage_path = (
                    self._path(duplicate.storage_path)
                    if duplicate
                    else self._path(str(self._assets_dir / f"{asset_id}{extension}"))
                )
                thumbnail_path = duplicate.thumbnail_path if duplicate else None
                created: list[Path] = []
                try:
                    if not duplicate:
                        with storage_path.open("xb") as file:
                            created.append(storage_path)
                            file.write(content)
                        if inspected.thumbnail:
                            thumbnail = self._path(
                                str(self._assets_dir / f"{asset_id}.preview.png")
                            )
                            with thumbnail.open("xb") as file:
                                created.append(thumbnail)
                                file.write(inspected.thumbnail)
                            thumbnail_path = str(thumbnail)
                    return await self._repository.create(
                        id=asset_id,
                        name=previous.name if previous else original_name,
                        original_name=original_name,
                        asset_type=asset_type,
                        mime_type=mime_type,
                        sha256=sha256,
                        size_bytes=len(content),
                        storage_path=str(storage_path),
                        thumbnail_path=thumbnail_path,
                        family_id=family_id,
                        version=version,
                        media_json=inspected.metadata.model_dump(mode="json"),
                        license_note=previous.license_note if previous else "",
                        license_expires_at=previous.license_expires_at if previous else None,
                        uploaded_by=uploaded_by,
                    )
                except BaseException:
                    for path in created:
                        path.unlink(missing_ok=True)
                    raise
        except Timeout as error:
            raise MediaBusy("Asset storage is busy. Retry shortly.") from error

    async def get(self, asset_id: str) -> StoredScreenAsset:
        asset = await self._repository.get(asset_id)
        if not self._path(asset.storage_path).is_file():
            raise AssetNotFound(asset_id)
        return asset

    async def thumbnail(self, asset_id: str) -> Path:
        asset = await self.get(asset_id)
        if not asset.thumbnail_path or not self._path(asset.thumbnail_path).is_file():
            raise AssetNotFound(asset_id)
        return self._path(asset.thumbnail_path)

    async def preview(
        self,
        asset_id: str,
        *,
        normalize_loudness: bool = False,
        trim_silence: bool = False,
    ) -> tuple[bytes, str]:
        asset = await self.get(asset_id)
        extension = Path(asset.storage_path).suffix or ".media"
        return await self._inspector.preview(
            self._path(asset.storage_path).read_bytes(),
            asset.mime_type,
            extension,
            normalize_loudness=normalize_loudness,
            trim_silence=trim_silence,
        )

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        search: str = "",
        asset_type: AssetType | None = None,
        family_id: str | None = None,
        visible_ids: set[str] | None = None,
    ) -> tuple[StoredScreenAsset, ...]:
        return await self._repository.list(
            offset=offset, limit=limit, search=search, asset_type=asset_type, family_id=family_id,
            visible_ids=visible_ids,
        )

    async def expiring(
        self, *, within_days: int = 30, limit: int = 100, visible_ids: set[str] | None = None
    ) -> tuple[StoredScreenAsset, ...]:
        cutoff = datetime.now(UTC) + timedelta(days=within_days)
        return await self._repository.expiring(cutoff=cutoff, limit=limit, visible_ids=visible_ids)

    async def references(self, asset_id: str) -> tuple[ScreenAssetReference, ...]:
        await self._repository.get(asset_id)
        return await self._repository.references(asset_id)

    async def usage(self, *, visible_ids: set[str] | None = None) -> ScreenAssetUsage:
        count, size, duration = await self._repository.usage(visible_ids=visible_ids)
        return ScreenAssetUsage(
            asset_count=count,
            size_bytes=size,
            duration_seconds=duration,
            max_total_bytes=self.limits.total_bytes,
            max_total_duration_seconds=self.limits.total_duration_seconds,
            max_image_bytes=self.limits.image_bytes,
            max_media_bytes=self.limits.media_bytes,
            max_duration_seconds=self._inspector.limits.max_duration_seconds,
        )

    async def reconcile_storage(self, *, grace_seconds: float = 3600) -> int:
        """Remove old files left behind by a crash before metadata commit."""
        cutoff = datetime.now(UTC).timestamp() - max(0, grace_seconds)
        try:
            async with self._lock():
                referenced = await self._repository.stored_paths()
                removed = 0
                if not self._assets_dir.exists():
                    return 0
                for candidate in self._assets_dir.iterdir():
                    if candidate.name.startswith(".") or not (
                        candidate.is_file() or candidate.is_symlink()
                    ):
                        continue
                    resolved = candidate.resolve(strict=False)
                    if (
                        not resolved.is_relative_to(self._assets_dir)
                        or str(resolved) in referenced
                    ):
                        continue
                    try:
                        if candidate.lstat().st_mtime > cutoff:
                            continue
                        candidate.unlink()
                    except FileNotFoundError:
                        continue
                    removed += 1
                return removed
        except Timeout as error:
            raise MediaBusy("Asset storage is busy. Retry shortly.") from error

    async def update(self, asset_id: str, patch: ScreenAssetPatch) -> StoredScreenAsset:
        return await self._repository.update(asset_id, patch)

    async def delete(self, asset_id: str) -> None:
        try:
            async with self._lock():
                asset = await self._repository.get(asset_id)
                paths = [
                    self._path(value)
                    for value in (asset.storage_path, asset.thumbnail_path)
                    if value
                ]
                await self._repository.delete(asset_id)
                for path in paths:
                    if not await self._repository.path_in_use(str(path)):
                        path.unlink(missing_ok=True)
        except Timeout as error:
            raise MediaBusy("Asset storage is busy. Retry shortly.") from error

    async def assert_references_exist(self, document: DashboardDocument) -> None:
        assets = {
            asset_id: await self.get(asset_id)
            for asset_id in collect_asset_references(document.model_dump(mode="json"))
        }
        for asset in assets.values():
            content = self._path(asset.storage_path).read_bytes()
            if hashlib.sha256(content).hexdigest() != asset.sha256:
                raise AssetInvalid("A referenced asset has changed on disk.")
            if not asset.media.validated:
                file_format = _FORMATS.get(asset.mime_type)
                if file_format is None:
                    raise AssetInvalid("A referenced asset has an unsupported media type.")
                await self._inspect(content, asset.mime_type, file_format[1])
        for component in document.components:
            slots: dict[str, str] = {}
            if component.type == "builtin.image":
                slots["asset_id"] = "image"
            elif component.type == "builtin.geo_map":
                slots["asset_id"] = "geojson"
            elif component.type == "builtin.digital_human":
                config = DigitalHumanSpec.model_validate(component.props)
                recording = config.recording
                media_id = (
                    config.speaking_asset_id
                    if config.speech_source == "video"
                    else config.audio_asset_id
                    if config.speech_source != "browser"
                    else ""
                )
                if (
                    config.speech_source in {"audio", "video"}
                    and not media_id
                    and not config.recordings
                ):
                    raise AssetInvalid("The selected speech source requires a media asset.")
                if media_id and recording is None and not config.recordings:
                    raise AssetInvalid("Prerecorded speech requires a confirmed transcript.")
                recordings = ([recording] if recording is not None else []) + list(
                    config.recordings
                )
                for confirmed in recordings:
                    media = assets[confirmed.asset_id]
                    expected_type = "video" if config.speech_source == "video" else "audio"
                    if (
                        (confirmed is recording and media_id != confirmed.asset_id)
                        or media.asset_type != expected_type
                        or media.sha256 != confirmed.sha256
                        or not media.media.validated
                        or media.media.duration_seconds is None
                        or abs(media.media.duration_seconds - confirmed.duration_seconds) > 0.001
                        or not media.media.audio_codec
                    ):
                        raise AssetInvalid(
                            "The confirmed recording does not match the speech media."
                        )
                    if confirmed.subtitle_asset_id:
                        subtitle = assets[confirmed.subtitle_asset_id]
                        if (
                            subtitle.asset_type != "subtitle"
                            or subtitle.sha256 != confirmed.subtitle_sha256
                            or not subtitle.media.validated
                            or subtitle.media.cues != confirmed.cues
                        ):
                            raise AssetInvalid("The confirmed subtitle does not match its asset.")
                for action in config.actions:
                    action_asset = assets[action.asset_id]
                    if action_asset.asset_type != action.asset_kind:
                        raise AssetInvalid(
                            "Digital human action resource type does not match its declaration."
                        )
                    if not action_asset.media.validated:
                        raise AssetInvalid("Digital human action resource is not validated.")
                slots = {
                    "avatar_asset_id": str(component.props.get("avatar_kind", "image")),
                    "speaking_asset_id": str(component.props.get("speaking_kind", "image")),
                    "audio_asset_id": "audio",
                    "subtitle_asset_id": "subtitle",
                }
            for key, expected in slots.items():
                asset_id = component.props.get(key)
                if (
                    isinstance(asset_id, str)
                    and asset_id
                    and assets[asset_id].asset_type != expected
                ):
                    raise AssetInvalid(
                        f"Asset type does not match component slot: {component.id}.{key}"
                    )


__all__ = [
    "MAX_ASSET_BYTES",
    "AssetInUse",
    "AssetInvalid",
    "AssetLimits",
    "AssetNotFound",
    "AssetQuotaExceeded",
    "AssetScanRejected",
    "AssetScanner",
    "AssetService",
    "AssetTooLarge",
    "collect_asset_references",
    "ScreenAssetRepository",
    "ScreenAssetResponse",
    "StoredScreenAsset",
]
