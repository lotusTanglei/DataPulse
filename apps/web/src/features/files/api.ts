import { apiRequest } from "../../lib/api";
import type { FileAsset, FilePreviewResponse } from "./types";

const FILES_PATH = "/api/admin/files";

export function listFileAssets(signal?: AbortSignal): Promise<FileAsset[]> {
  return apiRequest<FileAsset[]>(FILES_PATH, { signal });
}

export function uploadFileAsset(file: File): Promise<FileAsset> {
  const body = new FormData();
  body.append("file", file);
  return apiRequest<FileAsset>(FILES_PATH, {
    method: "POST",
    body,
  });
}

export function previewFileAsset(
  assetId: string,
  sheetName?: string,
  signal?: AbortSignal,
): Promise<FilePreviewResponse> {
  const query = sheetName
    ? `?sheet_name=${encodeURIComponent(sheetName)}`
    : "";
  return apiRequest<FilePreviewResponse>(
    `${FILES_PATH}/${encodeURIComponent(assetId)}/preview${query}`,
    { signal },
  );
}

export function deleteFileAsset(assetId: string): Promise<void> {
  return apiRequest<void>(`${FILES_PATH}/${encodeURIComponent(assetId)}`, {
    method: "DELETE",
  });
}
