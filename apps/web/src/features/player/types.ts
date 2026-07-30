import type { DashboardDocument } from "../../contracts";

export type PlayerMode = "preview" | "standalone" | "embed";

export interface PlayerDocument {
  id: string;
  name: string;
  document: DashboardDocument;
}
