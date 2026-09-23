export type AssetId = string;
export type ComponentId = string;
export type CreatedAt = string;
export type ErrorCode = string | null;
export type FinishedAt = string | null;
export type ProviderId = string;
export type ScreenId = string;
export type Source = string;
export type StartedAt = string | null;
export type Status = "queued" | "running" | "succeeded" | "failed" | "cancelled";
export type TaskId = string;

export interface DigitalHumanPlaybackDiagnosticResponse {
  asset_id: AssetId;
  component_id: ComponentId;
  created_at: CreatedAt;
  error_code?: ErrorCode;
  finished_at?: FinishedAt;
  provider_id: ProviderId;
  screen_id: ScreenId;
  source: Source;
  started_at?: StartedAt;
  status: Status;
  task_id: TaskId;
}
