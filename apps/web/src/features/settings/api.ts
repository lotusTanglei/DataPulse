import { apiRequest } from "../../lib/api";
import type {
  DigitalHumanProvider,
  DigitalHumanAudit,
  DigitalHumanProviderCreate,
  DigitalHumanProviderHealth,
  DigitalHumanProviderPatch,
  DigitalHumanProviderTest,
  DigitalHumanCostReport,
  DigitalHumanMetrics,
  DigitalHumanSettings,
  DigitalHumanSettingsPatch,
  DigitalHumanUsage,
  SpeechPlan,
  SpeechPlanRequest,
  SpeechTask,
} from "./types";

const base = "/api/admin/digital-human";

export const getDigitalHumanSettings = (
  signal?: AbortSignal,
): Promise<DigitalHumanSettings> => apiRequest(`${base}/settings`, { signal });

export const updateDigitalHumanSettings = (
  patch: DigitalHumanSettingsPatch,
): Promise<DigitalHumanSettings> =>
  apiRequest(`${base}/settings`, { method: "PATCH", json: patch });

export const listDigitalHumanProviders = (
  signal?: AbortSignal,
): Promise<DigitalHumanProvider[]> => apiRequest(`${base}/providers`, { signal });

export type { SpeechProviderOption as DigitalHumanProviderChoice } from "@datapulse/schema";
import type { SpeechProviderOption } from "@datapulse/schema";
export const listDigitalHumanProviderDirectory = (
  signal?: AbortSignal,
): Promise<SpeechProviderOption[]> => apiRequest(`${base}/provider-directory`, { signal });

export const createDigitalHumanProvider = (
  payload: DigitalHumanProviderCreate,
): Promise<DigitalHumanProvider> =>
  apiRequest(`${base}/providers`, { method: "POST", json: payload });

export const deleteDigitalHumanProvider = (id: string): Promise<void> =>
  apiRequest(`${base}/providers/${encodeURIComponent(id)}`, { method: "DELETE" });

export const updateDigitalHumanProvider = (
  id: string,
  patch: DigitalHumanProviderPatch,
): Promise<DigitalHumanProvider> =>
  apiRequest(`${base}/providers/${encodeURIComponent(id)}`, { method: "PATCH", json: patch });

export const testDigitalHumanProvider = (
  id: string,
): Promise<DigitalHumanProviderTest> =>
  apiRequest(`${base}/providers/${encodeURIComponent(id)}/test`, { method: "POST" });

export const listDigitalHumanVoices = (id: string): Promise<string[]> =>
  apiRequest(`${base}/providers/${encodeURIComponent(id)}/voices`);

export const listDigitalHumanProviderHealth = (
  id: string,
  signal?: AbortSignal,
): Promise<DigitalHumanProviderHealth[]> =>
  apiRequest(`${base}/providers/${encodeURIComponent(id)}/health?limit=50`, { signal });

export const getDigitalHumanUsage = (
  signal?: AbortSignal,
): Promise<DigitalHumanUsage> => apiRequest(`${base}/usage`, { signal });
export const getDigitalHumanMetrics = (
  signal?: AbortSignal,
): Promise<DigitalHumanMetrics> => apiRequest(`${base}/metrics`, { signal });

export const clearDigitalHumanCache = (): Promise<{ detached_task_count: number; deleted_asset_count: number }> =>
  apiRequest(`${base}/cache/clear`, { method: "POST" });

export const getDigitalHumanCostReport = (
  signal?: AbortSignal,
): Promise<DigitalHumanCostReport> => apiRequest(`${base}/usage/cost`, { signal });

export const listDigitalHumanTasks = (
  signal?: AbortSignal,
): Promise<SpeechTask[]> => apiRequest(`${base}/tasks?limit=50`, { signal });

export const createDigitalHumanSpeechPlan = (
  payload: SpeechPlanRequest,
  signal?: AbortSignal,
): Promise<SpeechPlan> => apiRequest(`${base}/plans/preview`, { method: "POST", json: payload, signal });

export const queueDigitalHumanSpeechTask = (planId: string, signal?: AbortSignal): Promise<SpeechTask> =>
  apiRequest(`${base}/plans/${encodeURIComponent(planId)}/tasks`, { method: "POST", signal });

export const getDigitalHumanSpeechTask = (
  taskId: string,
  signal?: AbortSignal,
): Promise<SpeechTask> => apiRequest(`${base}/tasks/${encodeURIComponent(taskId)}`, { signal });

export const retryDigitalHumanTask = (planId: string): Promise<SpeechTask> =>
  apiRequest(`${base}/plans/${encodeURIComponent(planId)}/tasks`, { method: "POST" });

export const listDigitalHumanAudit = (
  signal?: AbortSignal,
): Promise<DigitalHumanAudit[]> => apiRequest(`${base}/audit?limit=100`, { signal });
