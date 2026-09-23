import { apiRequest } from "../../lib/api";
import type { DashboardDocument } from "../../contracts";
import type { JsonValue, QueryResult } from "../query/types";
import type {
  Screen,
  ScreenCreatePayload,
  ScreenDraftUpdatePayload,
  ScreenAccessPolicy,
  ScreenSummary,
  DashboardPlanCompilePayload,
  DashboardPlanCompileResponse,
} from "./types";

const SCREENS_PATH = "/api/admin/screens";

export function listScreens(signal?: AbortSignal): Promise<ScreenSummary[]> {
  return apiRequest<ScreenSummary[]>(SCREENS_PATH, { signal });
}

export function getScreen(
  screenId: string,
  signal?: AbortSignal,
): Promise<Screen> {
  return apiRequest<Screen>(
    `${SCREENS_PATH}/${encodeURIComponent(screenId)}`,
    { signal },
  );
}

export function createScreen(payload: ScreenCreatePayload): Promise<Screen> {
  return apiRequest<Screen>(SCREENS_PATH, {
    method: "POST",
    json: payload,
  });
}

export function compileDashboardPlan(
  payload: DashboardPlanCompilePayload,
): Promise<DashboardPlanCompileResponse> {
  return apiRequest<DashboardPlanCompileResponse>(`${SCREENS_PATH}/plan/compile`, {
    method: "POST",
    json: payload,
  });
}

export function queryScreenDocument(
  document: DashboardDocument,
  componentId: string,
  parameters: Record<string, JsonValue>,
  signal?: AbortSignal,
): Promise<QueryResult> {
  return apiRequest<QueryResult>(`${SCREENS_PATH}/query-document`, {
    method: "POST",
    json: {
      document,
      component_id: componentId,
      parameters,
    },
    signal,
  });
}

export function updateScreen(
  screenId: string,
  payload: ScreenDraftUpdatePayload,
): Promise<Screen> {
  return apiRequest<Screen>(
    `${SCREENS_PATH}/${encodeURIComponent(screenId)}`,
    {
      method: "PATCH",
      json: payload,
    },
  );
}

export function copyScreen(screenId: string): Promise<Screen> {
  return apiRequest<Screen>(
    `${SCREENS_PATH}/${encodeURIComponent(screenId)}/copy`,
    { method: "POST" },
  );
}

export function publishScreen(
  screenId: string,
  expectedRevision: number,
): Promise<Screen> {
  return apiRequest<Screen>(
    `${SCREENS_PATH}/${encodeURIComponent(screenId)}/publish`,
    {
      method: "POST",
      json: { expected_revision: expectedRevision },
    },
  );
}

export interface DisplayKeyResponse {
  screen_id: string;
  key_version: number;
  key: string;
}

export function generateDisplayKey(screenId: string): Promise<DisplayKeyResponse> {
  return apiRequest<DisplayKeyResponse>(
    `${SCREENS_PATH}/${encodeURIComponent(screenId)}/display-key`,
    { method: "POST" },
  );
}

export function updateScreenAccessPolicy(
  screenId: string,
  policy: ScreenAccessPolicy,
): Promise<Screen> {
  return apiRequest<Screen>(
    `${SCREENS_PATH}/${encodeURIComponent(screenId)}/access-policy`,
    {
      method: "PATCH",
      json: policy,
    },
  );
}

export function deleteScreen(screenId: string): Promise<void> {
  return apiRequest<void>(
    `${SCREENS_PATH}/${encodeURIComponent(screenId)}`,
    { method: "DELETE" },
  );
}
