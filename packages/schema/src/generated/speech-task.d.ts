export type AssetId = string;
export type CreatedAt = string;
export type ErrorCode = string | null;
export type ExpiresAt = string | null;
export type FinishedAt = string | null;
export type Id = string;
export type PlanId = string;
export type Priority = number;
export type ProviderId = string;
export type Source = string;
export type StartedAt = string | null;
export type Status = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export interface SpeechTaskResponse {
  asset_id: AssetId;
  created_at: CreatedAt;
  error_code?: ErrorCode;
  expires_at?: ExpiresAt;
  finished_at?: FinishedAt;
  id: Id;
  plan_id: PlanId;
  priority?: Priority;
  provider_id: ProviderId;
  source?: Source;
  started_at?: StartedAt;
  status: Status;
}
