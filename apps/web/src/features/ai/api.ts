import { apiRequest } from "../../lib/api";

import type {
  AiAnalysisRequest,
  AiAnalysisResponse,
  AiChartRequest,
  AiChartResponse,
  AiScreenRequest,
  AiScreenResponse,
} from "./types";

const AI_PATH = "/api/admin/ai";

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
