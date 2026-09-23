export type ErrorCode = string | null;
export type LatencyMs = number;
export type Ok = boolean;
export type Voices = string[];

export interface DigitalHumanProviderTestResponse {
  error_code?: ErrorCode;
  latency_ms: LatencyMs;
  ok: Ok;
  voices?: Voices;
}
