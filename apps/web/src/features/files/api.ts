import { apiRequest } from "../../lib/api";
import type { FileAsset } from "./types";

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
