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

export async function fetchPlayerPluginModule(
  mode: "preview" | "standalone" | "embed", screenId:string, pluginId:string,
  version:string, entry:string, ticket:string, signal?:AbortSignal,
):Promise<unknown> {
  const { importPluginResponse } = await import("../ecosystem/plugins");
  const encodedId=encodeURIComponent(pluginId), encodedVersion=encodeURIComponent(version);
  const root=mode==="preview"
    ? `/api/admin/ecosystem/packages/plugin/${encodedId}/${encodedVersion}`
    : `/api/${mode==="standalone"?"player":"embed"}/screens/${encodeURIComponent(screenId)}/plugins/${encodedId}/${encodedVersion}`;
  const response=await fetch(`${root}/files/${entry.split("/").map(encodeURIComponent).join("/")}`,{
    credentials:mode==="embed"?"omit":"same-origin",
    ...(mode==="embed"?{headers:{Authorization:`Bearer ${ticket}`}}:{}),signal,
  });
  if (!response.ok && mode==="embed") throw await embedApiError(response);
  return importPluginResponse(response);
}

export async function loadPlayerPlugins(
  mode: "preview" | "standalone" | "embed", screenId:string, ticket:string,
  dependencies:ReadonlyArray<{id:string;version:string}>, signal?:AbortSignal,
) {
  const { createPluginRegistry } = await import("../ecosystem/plugins");
  const { getPackage } = await import("../ecosystem/api");
  type CatalogPackage = import("../ecosystem/types").CatalogPackage;
  let packages:CatalogPackage[]=[];
  try {
    if (mode==="preview") {
      packages=await Promise.all(dependencies.map(item=>getPackage("plugin",item.id,item.version,signal)));
    } else if (mode==="standalone") {
      packages=await apiRequest<CatalogPackage[]>(`${PLAYER_SCREENS_PATH}/${encodeURIComponent(screenId)}/plugins`,
        {signal,suppressAuthExpiredEvent:true});
    } else {
      packages=await embedRequest<CatalogPackage[]>(`${EMBED_SCREENS_PATH}/${encodeURIComponent(screenId)}/plugins`,ticket,{signal});
    }
  } catch {
    // Missing packages become the existing per-component fallback. Builtins still render.
  }
  return createPluginRegistry(packages.filter(item=>dependencies.some(dep=>dep.id===item.id&&dep.version===item.version)),
    item=>fetchPlayerPluginModule(mode,screenId,item.id,item.version,item.manifest.entry,ticket,signal));
}
