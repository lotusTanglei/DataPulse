export type BaseUrl = string;
export type CircuitOpenUntil = string | null;
export type Configured = boolean;
export type ConsecutiveFailures = number;
export type CostPerMinute = number;
export type DefaultVoice = string;
export type Enabled = boolean;
export type HealthStatus = "unconfigured" | "disabled" | "healthy" | "degraded" | "open";
export type Id = string;
export type Language = string;
export type LastCheckedAt = string | null;
export type LastErrorCode = string | null;
export type LastLatencyMs = number | null;
export type Name = string;
export type ProviderType = "openai_compatible" | "azure" | "custom";
export type ProviderVersion = string;

export interface DigitalHumanProviderResponse {
  base_url: BaseUrl;
  circuit_open_until?: CircuitOpenUntil;
  configured: Configured;
  consecutive_failures: ConsecutiveFailures;
  cost_per_minute: CostPerMinute;
  default_voice: DefaultVoice;
  enabled: Enabled;
  health_status: HealthStatus;
  id: Id;
  language: Language;
  last_checked_at?: LastCheckedAt;
  last_error_code?: LastErrorCode;
  last_latency_ms?: LastLatencyMs;
  name: Name;
  provider_type: ProviderType;
  provider_version: ProviderVersion;
}
