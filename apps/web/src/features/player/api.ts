import { ApiError, apiRequest } from "../../lib/api";
import type { JsonValue, QueryResult } from "../query/types";
import type { Screen } from "../screens/types";
import type { EmbedPlayerDocument, PlayerDocument } from "./types";

const ADMIN_SCREENS_PATH = "/api/admin/screens";
const PLAYER_SCREENS_PATH = "/api/player/screens";
const EMBED_SCREENS_PATH = "/api/embed/screens";

interface EmbedErrorEnvelope {
  error: {
    code: string;
    message: string;
    request_id: string;
    field_errors?: { field: string; message: string }[];
  };
}

function isEmbedErrorEnvelope(value: unknown): value is EmbedErrorEnvelope {
  if (typeof value !== "object" || value === null || !("error" in value)) {
    return false;
  }
  const error = value.error;
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    typeof error.code === "string" &&
    "message" in error &&
    typeof error.message === "string" &&
    "request_id" in error &&
    typeof error.request_id === "string"
  );
}

async function embedApiError(response: Response): Promise<ApiError> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (isEmbedErrorEnvelope(payload)) {
    return new ApiError({
      code: payload.error.code,
      message: payload.error.message,
      requestId: payload.error.request_id,
      fieldErrors: payload.error.field_errors,
      status: response.status,
    });
  }
  return new ApiError({
    code: "EMBED_REQUEST_FAILED",
    message: "嵌入大屏请求失败。",
    requestId: response.headers.get("X-Request-ID") ?? "",
    status: response.status,
  });
}

async function embedRequest<T>(
  input: string,
  ticket: string,
  options: {
    method?: "GET" | "POST";
    json?: unknown;
    signal?: AbortSignal;
  } = {},
): Promise<T> {
  const headers = new Headers({ Authorization: `Bearer ${ticket}` });
  let body: string | undefined;
  if (options.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.json);
  }
  const response = await fetch(input, {
    method: options.method ?? "GET",
    headers,
    body,
    credentials: "omit",
    signal: options.signal,
  });
  if (!response.ok) {
    throw await embedApiError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

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

export function exchangeStandaloneKey(
  screenId: string,
  key: string,
  signal?: AbortSignal,
): Promise<void> {
  return apiRequest<void>(
    `${PLAYER_SCREENS_PATH}/${encodeURIComponent(screenId)}/session`,
    {
      method: "POST",
      json: { key },
      signal,
      suppressAuthExpiredEvent: true,
    },
  );
}

export function getStandaloneDocument(
  screenId: string,
  signal?: AbortSignal,
): Promise<PlayerDocument> {
  return apiRequest<PlayerDocument>(
    `${PLAYER_SCREENS_PATH}/${encodeURIComponent(screenId)}`,
    { signal, suppressAuthExpiredEvent: true },
  );
}

export function queryStandaloneComponent(
  screenId: string,
  componentId: string,
  parameters: Record<string, JsonValue>,
  signal?: AbortSignal,
): Promise<QueryResult> {
  return apiRequest<QueryResult>(
    `${PLAYER_SCREENS_PATH}/${encodeURIComponent(screenId)}/query`,
    {
      method: "POST",
      json: { component_id: componentId, parameters },
      signal,
      suppressAuthExpiredEvent: true,
    },
  );
}

export async function loadStandaloneAsset(
  screenId: string,
  assetId: string,
  signal?: AbortSignal,
): Promise<string> {
  const response = await fetch(
    `${PLAYER_SCREENS_PATH}/${encodeURIComponent(screenId)}/assets/${encodeURIComponent(assetId)}`,
    { credentials: "same-origin", signal },
  );
  if (!response.ok) {
    throw new Error("Asset unavailable.");
  }
  return URL.createObjectURL(await response.blob());
}

export function getEmbedDocument(
  screenId: string,
  ticket: string,
  signal?: AbortSignal,
): Promise<EmbedPlayerDocument> {
  return embedRequest<EmbedPlayerDocument>(
    `${EMBED_SCREENS_PATH}/${encodeURIComponent(screenId)}`,
    ticket,
    { signal },
  );
}

export function queryEmbedComponent(
  screenId: string,
  componentId: string,
  parameters: Record<string, JsonValue>,
  ticket: string,
  signal?: AbortSignal,
): Promise<QueryResult> {
  return embedRequest<QueryResult>(
    `${EMBED_SCREENS_PATH}/${encodeURIComponent(screenId)}/query`,
    ticket,
    {
      method: "POST",
      json: { component_id: componentId, parameters },
      signal,
    },
  );
}

export async function loadEmbedAsset(
  screenId: string,
  assetId: string,
  ticket: string,
  signal?: AbortSignal,
): Promise<string> {
  const response = await fetch(
    `${EMBED_SCREENS_PATH}/${encodeURIComponent(screenId)}/assets/${encodeURIComponent(assetId)}`,
    {
      credentials: "omit",
      headers: { Authorization: `Bearer ${ticket}` },
      signal,
    },
  );
  if (!response.ok) {
    throw await embedApiError(response);
  }
  return URL.createObjectURL(await response.blob());
}
