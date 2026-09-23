import { apiRequest } from "../../lib/api";

import type {
  AiAnalysisRequest,
  AiAnalysisResponse,
  AiChartRequest,
  AiChartResponse,
  AiEditRequest,
  AiEditResponse,
  AiScreenRequest,
  AiScreenEditRequest,
  AiScreenEditResponse,
  AiScreenResponse,
  AiHealth,
} from "./types";

const AI_PATH = "/api/admin/ai";

export function getAiStatus(signal?: AbortSignal): Promise<AiHealth> {
  return apiRequest<AiHealth>(`${AI_PATH}/status`, { signal });
}

export function analyzeAi(
  payload: AiAnalysisRequest,
  signal?: AbortSignal,
): Promise<AiAnalysisResponse> {
  return apiRequest<AiAnalysisResponse>(`${AI_PATH}/analyze`, {
    method: "POST",
    json: payload,
    signal,
  });
}

export function generateChart(
  payload: AiChartRequest,
  signal?: AbortSignal,
): Promise<AiChartResponse> {
  return apiRequest<AiChartResponse>(`${AI_PATH}/chart`, {
    method: "POST",
    json: payload,
    signal,
  });
}

export function generateScreen(
  payload: AiScreenRequest,
  signal?: AbortSignal,
): Promise<AiScreenResponse> {
  return apiRequest<AiScreenResponse>(`${AI_PATH}/screen`, {
    method: "POST",
    json: payload,
    signal,
  });
}

export function editScreen(
  payload: AiScreenEditRequest,
  signal?: AbortSignal,
): Promise<AiScreenEditResponse> {
  return apiRequest<AiScreenEditResponse>(`${AI_PATH}/screen/edit`, {
    method: "POST",
    json: payload,
    signal,
  });
}

export function editAi(
  payload: AiEditRequest,
  signal?: AbortSignal,
): Promise<AiEditResponse> {
  return apiRequest<AiEditResponse>(`${AI_PATH}/edit`, {
    method: "POST",
    json: payload,
    signal,
  });
}
