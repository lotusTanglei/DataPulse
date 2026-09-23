export type AssetCount = number;
export type DurationSeconds = number;
export type MaxDurationSeconds = number;
export type MaxImageBytes = number;
export type MaxMediaBytes = number;
export type MaxTotalBytes = number;
export type MaxTotalDurationSeconds = number;
export type SizeBytes = number;

export interface ScreenAssetUsage {
  asset_count: AssetCount;
  duration_seconds: DurationSeconds;
  max_duration_seconds: MaxDurationSeconds;
  max_image_bytes: MaxImageBytes;
  max_media_bytes: MaxMediaBytes;
  max_total_bytes: MaxTotalBytes;
  max_total_duration_seconds: MaxTotalDurationSeconds;
  size_bytes: SizeBytes;
}
