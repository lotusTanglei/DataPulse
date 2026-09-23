import type { ScreenAssetPatch, ScreenAssetReference, ScreenAssetResponse, ScreenAssetUsage } from "@datapulse/schema";
import { apiRequest } from "../../../lib/api";

export type AssetType = ScreenAssetResponse["asset_type"];
export type { ScreenAssetResponse as ScreenAsset, ScreenAssetReference, ScreenAssetUsage };

const base = "/api/admin/assets";
export const assetUrl = (id: string): string => `${base}/${encodeURIComponent(id)}`;
export function assetPreviewUrl(id: string, options: { normalizeLoudness?: boolean; trimSilence?: boolean } = {}): string {
  const query = new URLSearchParams();
  if (options.normalizeLoudness) query.set("normalize_loudness", "true");
  if (options.trimSilence) query.set("trim_silence", "true");
  const suffix = query.toString();
  return `${assetUrl(id)}/preview${suffix ? `?${suffix}` : ""}`;
}

export function listAssets(options: {
  search?: string; assetType?: AssetType | ""; familyId?: string; offset?: number; limit?: number;
} = {}, signal?: AbortSignal): Promise<ScreenAssetResponse[]> {
  const query = new URLSearchParams({ offset: String(options.offset ?? 0), limit: String(options.limit ?? 25) });
  if (options.search) query.set("search", options.search);
  if (options.assetType) query.set("asset_type", options.assetType);
  if (options.familyId) query.set("family_id", options.familyId);
  return apiRequest(`${base}?${query}`, { signal });
}

export const getAsset = (id: string, signal?: AbortSignal): Promise<ScreenAssetResponse> =>
  apiRequest(`${assetUrl(id)}/metadata`, { signal });
export const getAssetUsage = (signal?: AbortSignal): Promise<ScreenAssetUsage> =>
  apiRequest(`${base}/usage`, { signal });
export const listExpiringAssets = (withinDays = 30, signal?: AbortSignal): Promise<ScreenAssetResponse[]> =>
  apiRequest(`${base}/expiring?within_days=${withinDays}&limit=100`, { signal });
export const getAssetReferences = (id: string, signal?: AbortSignal): Promise<ScreenAssetReference[]> =>
  apiRequest(`${assetUrl(id)}/references`, { signal });
export const patchAsset = (id: string, patch: ScreenAssetPatch, signal?: AbortSignal): Promise<ScreenAssetResponse> =>
  apiRequest(`${assetUrl(id)}/metadata`, { method: "PATCH", json: patch, signal });
export const deleteAsset = (id: string, signal?: AbortSignal): Promise<void> =>
  apiRequest(assetUrl(id), { method: "DELETE", signal });

export function uploadAsset(file: File, replaces?: string, signal?: AbortSignal): Promise<ScreenAssetResponse> {
  const body = new FormData();
  body.append("file", file);
  return apiRequest(replaces ? `${assetUrl(replaces)}/versions` : base, { method: "POST", body, signal });
}

export function formatAssetBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MiB`;
}
