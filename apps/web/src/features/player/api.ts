import { apiRequest } from "../../lib/api";
import type { JsonValue, QueryResult } from "../query/types";
import type { Screen } from "../screens/types";
import type { PlayerDocument } from "./types";

const ADMIN_SCREENS_PATH = "/api/admin/screens";

export async function getPreviewDocument(
  screenId: string,
  signal?: AbortSignal,
): Promise<PlayerDocument> {
  const screen = await apiRequest<Screen>(
    `${ADMIN_SCREENS_PATH}/${encodeURIComponent(screenId)}`,
    { signal },
  );
  return {
    id: screen.id,
    name: screen.name,
    document: screen.draft_document,
  };
}

export function queryPreviewComponent(
  screenId: string,
  componentId: string,
  parameters: Record<string, JsonValue>,
  signal?: AbortSignal,
): Promise<QueryResult> {
  return apiRequest<QueryResult>(
    `${ADMIN_SCREENS_PATH}/${encodeURIComponent(screenId)}/query`,
    {
      method: "POST",
      json: { component_id: componentId, parameters },
      signal,
    },
  );
}

export async function loadPreviewAsset(
  assetId: string,
  signal?: AbortSignal,
): Promise<string> {
  const response = await fetch(
    `/api/admin/assets/${encodeURIComponent(assetId)}`,
    { credentials: "same-origin", signal },
  );
  if (!response.ok) {
    throw new Error("Asset unavailable.");
  }
  return URL.createObjectURL(await response.blob());
}
