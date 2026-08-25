import type {
  AiEditResponse as GeneratedAiEditResponse,
  AnalysisPlan,
  ChartSpec,
  DashboardDocument,
} from "../../contracts";
import type { QueryResult } from "../query/types";

export interface AiAnalysisRequest {
  question: string;
  dataset_ids: string[];
  mode?: "analysis" | "chart";
}

export interface AiAnalysisResponse {
  plan: AnalysisPlan;
  narrative: string;
  chart_spec: ChartSpec | null;
  preview: QueryResult;
  warnings: string[];
}

export interface AiChartRequest {
  question: string;
  dataset_id: string;
  target_component_type?: ChartSpec["visual"]["type"];
}

export interface AiChartResponse {
  chart_spec: ChartSpec;
  explanation: string;
  preview: QueryResult;
  warnings: string[];
}

export interface AiScreenRequest {
  question: string;
  dataset_ids: string[];
  canvas_width?: number;
  canvas_height?: number;
  theme?: "dark" | "light";
}

export interface AiScreenResponse {
  document: DashboardDocument;
  explanation: string;
  warnings: string[];
}

export type AiEditCommand = GeneratedAiEditResponse["commands"][number];

export interface AiEditRequest {
  question: string;
  document: DashboardDocument;
  selected_component_ids: string[];
  dataset_ids?: string[];
}

export type AiEditResponse = GeneratedAiEditResponse;
