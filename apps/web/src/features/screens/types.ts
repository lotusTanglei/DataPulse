import type { DashboardDocument } from "../../contracts";

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
}

export interface ScreenCreatePayload {
  name: string;
  description?: string;
}

export interface ScreenDraftUpdatePayload {
  name?: string;
  description?: string;
  draft_document?: DashboardDocument;
  expected_revision?: number;
}
