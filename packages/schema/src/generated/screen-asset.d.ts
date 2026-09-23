export type AssetType = "image" | "geojson" | "audio" | "video" | "subtitle";
export type CreatedAt = string;
export type FamilyId = string;
export type HasThumbnail = boolean;
export type Id = string;
export type LicenseExpiresAt = string | null;
export type LicenseNote = string;
export type AudioCodec = string | null;
export type Channels = number | null;
export type End = number;
export type Start = number;
export type Text = string;
/**
 * @maxItems 500
 */
export type Cues = SubtitleCue[];
export type DurationSeconds = number | null;
export type FrameRate = number | null;
export type HasAlpha = boolean;
export type Height = number | null;
export type SampleRate = number | null;
export type ThumbnailSizeBytes = number;
export type Validated = boolean;
export type VideoCodec = string | null;
export type Width = number | null;
export type MimeType = string;
export type Name = string;
export type OriginalName = string;
export type Sha256 = string;
export type SizeBytes = number;
export type UploadedBy = string;
export type Version = number;

export interface ScreenAssetResponse {
  asset_type: AssetType;
  created_at: CreatedAt;
  family_id: FamilyId;
  has_thumbnail?: HasThumbnail;
  id: Id;
  license_expires_at?: LicenseExpiresAt;
  license_note?: LicenseNote;
  media?: AssetMediaMetadata;
  mime_type: MimeType;
  name: Name;
  original_name: OriginalName;
  sha256: Sha256;
  size_bytes: SizeBytes;
  uploaded_by?: UploadedBy;
  version: Version;
}
export interface AssetMediaMetadata {
  audio_codec?: AudioCodec;
  channels?: Channels;
  cues?: Cues;
  duration_seconds?: DurationSeconds;
  frame_rate?: FrameRate;
  has_alpha?: HasAlpha;
  height?: Height;
  sample_rate?: SampleRate;
  thumbnail_size_bytes?: ThumbnailSizeBytes;
  validated?: Validated;
  video_codec?: VideoCodec;
  width?: Width;
}
export interface SubtitleCue {
  end: End;
  start: Start;
  text: Text;
}
