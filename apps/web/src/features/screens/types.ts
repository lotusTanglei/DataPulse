import type {
  DashboardDocument,
  DashboardPlan,
  GenerationSelfCheckReport,
} from "../../contracts";

export interface ScreenAccessPolicy {
  allowed_origins: string[];
  allowed_ips: string[];
}

export interface ScreenSummary {
  id: string;
  name: string;
  description: string;
  draft_revision: number;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Screen extends ScreenSummary {
  draft_document: DashboardDocument;
  published_document: DashboardDocument | null;
  access_policy?: ScreenAccessPolicy;
}

export interface ScreenCreatePayload {
  name: string;
  description?: string;
  draft_document?: DashboardDocument;
}

export interface ScreenDraftUpdatePayload {
  name?: string;
  description?: string;
  draft_document?: DashboardDocument;
  expected_revision?: number;
}

export interface DashboardPlanCompilePayload {
  plan: DashboardPlan;
  canvas_width?: number;
  canvas_height?: number;
}

export interface DashboardPlanCompileResponse {
  plan: DashboardPlan;
  document: DashboardDocument;
  report: GenerationSelfCheckReport | null;
  warnings: string[];
}
