from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from datapulse.contracts.common import ContractModel, NonBlankStr

AssetType = Literal["image", "geojson", "audio", "video", "subtitle"]


class SubtitleCue(ContractModel):
    start: float = Field(ge=0, allow_inf_nan=False)
    end: float = Field(gt=0, allow_inf_nan=False)
    text: str = Field(min_length=1, max_length=2000)


class AssetMediaMetadata(ContractModel):
    validated: bool = False
    thumbnail_size_bytes: int = Field(default=0, ge=0)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    duration_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    sample_rate: int | None = Field(default=None, gt=0)
    channels: int | None = Field(default=None, gt=0)
    frame_rate: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    has_alpha: bool = False
    video_codec: str | None = None
    audio_codec: str | None = None
    cues: tuple[SubtitleCue, ...] = Field(default_factory=tuple, max_length=500)


class ScreenAssetResponse(ContractModel):
    id: NonBlankStr
    name: NonBlankStr
    original_name: NonBlankStr
    asset_type: AssetType
    mime_type: NonBlankStr
    sha256: str
    size_bytes: int = Field(ge=0)
    family_id: NonBlankStr
    version: int = Field(ge=1)
    media: AssetMediaMetadata = Field(default_factory=AssetMediaMetadata)
    has_thumbnail: bool = False
    license_note: str = ""
    license_expires_at: datetime | None = None
    uploaded_by: str = ""
    created_at: datetime


class ScreenAssetPatch(ContractModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    license_note: str | None = Field(default=None, max_length=2000)
    license_expires_at: datetime | None = None

    @field_validator("name", "license_note")
    @classmethod
    def safe_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if any(ord(char) < 32 for char in value):
            raise ValueError("Asset labels must not contain control characters.")
        return value

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("An asset name cannot be blank.")
        return value

    @field_validator("license_expires_at")
    @classmethod
    def aware_expiration(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("License expiry must include a timezone.")
        return value


class ScreenAssetReference(ContractModel):
    screen_id: str
    screen_name: str
    in_draft: bool
    in_published: bool


class ScreenAssetUsage(ContractModel):
    asset_count: int
    size_bytes: int
    duration_seconds: float
    max_total_bytes: int
    max_total_duration_seconds: float
    max_image_bytes: int
    max_media_bytes: int
    max_duration_seconds: float
