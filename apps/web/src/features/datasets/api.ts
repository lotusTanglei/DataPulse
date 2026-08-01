import { apiRequest } from "../../lib/api";
import type {
  Dataset,
  DatasetCreatePayload,
  DatasetPreviewPayload,
  DatasetUpdatePayload,
  QueryResult,
} from "./types";

const DATASETS_PATH = "/api/admin/datasets";

export function listDatasets(signal?: AbortSignal): Promise<Dataset[]> {
  return apiRequest<Dataset[]>(DATASETS_PATH, { signal });
}

export function getDataset(
  datasetId: string,
  signal?: AbortSignal,
): Promise<Dataset> {
  return apiRequest<Dataset>(
    `${DATASETS_PATH}/${encodeURIComponent(datasetId)}`,
    { signal },
  );
}

export function createDataset(
  payload: DatasetCreatePayload,
): Promise<Dataset> {
  return apiRequest<Dataset>(DATASETS_PATH, {
    method: "POST",
    json: payload,
  });
}

export function createFileDataset(payload: {
  name: string;
  file_asset_id: string;
  sheet_name?: string | null;
  max_rows: number;
  timeout_seconds: number;
}): Promise<Dataset> {
  return apiRequest<Dataset>(`${DATASETS_PATH}/files`, {
    method: "POST",
    json: payload,
  });
}

export function updateDataset(
  datasetId: string,
  payload: DatasetUpdatePayload,
): Promise<Dataset> {
  return apiRequest<Dataset>(
    `${DATASETS_PATH}/${encodeURIComponent(datasetId)}`,
    {
      method: "PATCH",
      json: payload,
    },
  );
}

export function previewDataset(
  datasetId: string,
  payload: DatasetPreviewPayload,
  signal?: AbortSignal,
): Promise<QueryResult> {
  return apiRequest<QueryResult>(
    `${DATASETS_PATH}/${encodeURIComponent(datasetId)}/preview`,
    {
      method: "POST",
      json: payload,
      signal,
    },
  );
}

export function deleteDataset(datasetId: string): Promise<void> {
  return apiRequest<void>(
    `${DATASETS_PATH}/${encodeURIComponent(datasetId)}`,
    { method: "DELETE" },
  );
}
