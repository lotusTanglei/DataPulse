import type { DashboardDocument } from "../../contracts";
import type { JsonValue } from "../query/types";

export type PlayerMode = "preview" | "standalone" | "embed";

export interface PlayerDocument {
  id: string;
  name: string;
  document: DashboardDocument;
}

export interface EmbedPlayerDocument extends PlayerDocument {
  allowed_origin: string;
  parameters: Record<string, JsonValue>;
  mutable_parameters: string[];
  expires_at: string;
}
