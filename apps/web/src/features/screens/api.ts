import { apiRequest } from "../../lib/api";
import type {
  Screen,
  ScreenCreatePayload,
  ScreenDraftUpdatePayload,
  ScreenSummary,
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

export function deleteScreen(screenId: string): Promise<void> {
  return apiRequest<void>(
    `${SCREENS_PATH}/${encodeURIComponent(screenId)}`,
    { method: "DELETE" },
  );
}
