export type CheckedAt = string;
export type ErrorCode = string | null;
export type LatencyMs = number;
export type Ok = boolean;
export type ProviderId = string;

export interface DigitalHumanProviderHealthResponse {
  checked_at: CheckedAt;
  error_code?: ErrorCode;
  latency_ms: LatencyMs;
  ok: Ok;
  provider_id: ProviderId;
}
