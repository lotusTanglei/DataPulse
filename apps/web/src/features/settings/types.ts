export interface DigitalHumanSettings {
  enabled: boolean;
  default_muted: boolean;
  default_subtitles: boolean;
  max_speech_seconds: number;
  cooldown_seconds: number;
  daily_task_limit: number;
  daily_audio_seconds_limit: number;
  ai_enabled: boolean;
  ai_model: string;
  ai_context_limit: number;
  data_retention_days: number;
  forbidden_words: string[];
  sensitive_patterns: string[];
  manual_review_required: boolean;
  updated_at: string;
}

export interface DigitalHumanSettingsPatch {
  enabled?: boolean;
  default_muted?: boolean;
  default_subtitles?: boolean;
  max_speech_seconds?: number;
  cooldown_seconds?: number;
  daily_task_limit?: number;
  daily_audio_seconds_limit?: number;
  ai_enabled?: boolean;
  ai_model?: string;
  ai_context_limit?: number;
  data_retention_days?: number;
  forbidden_words?: string[];
  sensitive_patterns?: string[];
  manual_review_required?: boolean;
}

export type ProviderType = "openai_compatible" | "azure" | "custom";

export interface DigitalHumanProvider {
  id: string;
  name: string;
  provider_type: ProviderType;
  base_url: string;
  default_voice: string;
  language: string;
  enabled: boolean;
  configured: boolean;
  cost_per_minute: number;
  provider_version: string;
  health_status: "unconfigured" | "disabled" | "healthy" | "degraded" | "open";
  consecutive_failures: number;
  circuit_open_until: string | null;
  last_checked_at: string | null;
  last_latency_ms: number | null;
  last_error_code: string | null;
}

export interface DigitalHumanProviderCreate {
  name: string;
  provider_type: ProviderType;
  base_url: string;
  api_key?: string;
  default_voice: string;
  language: string;
  enabled: boolean;
  cost_per_minute: number;
  provider_version: string;
}

export type DigitalHumanProviderPatch = Partial<DigitalHumanProviderCreate> & {
  clear_api_key?: boolean;
};

export interface DigitalHumanProviderTest {
  ok: boolean;
  latency_ms: number;
  error_code: string | null;
  voices: string[];
}

export interface DigitalHumanUsage {
  period_start: string;
  task_count: number;
  succeeded_count: number;
  failed_count: number;
  generated_seconds: number;
  cached_count: number;
  estimated_cost: number;
}

export interface DigitalHumanMetrics {
  collected_at: string;
  tasks_queued: number;
  tasks_succeeded: number;
  tasks_failed: number;
  tasks_cancelled: number;
  cache_hits: number;
  synthesis_attempts: number;
  synthesis_failures: number;
  synthesis_total_ms: number;
  average_synthesis_ms: number;
}

export interface DigitalHumanProviderHealth {
  provider_id: string;
  checked_at: string;
  ok: boolean;
  latency_ms: number;
  error_code: string | null;
}

export interface DigitalHumanCostReportRow {
  provider_id: string;
  provider_name: string;
  task_count: number;
  succeeded_count: number;
  failed_count: number;
  cached_count: number;
  generated_seconds: number;
  estimated_cost: number;
}

export interface DigitalHumanCostReport {
  period_start: string;
  period_end: string;
  rows: DigitalHumanCostReportRow[];
  total_task_count: number;
  total_generated_seconds: number;
  total_estimated_cost: number;
}

export interface DigitalHumanCacheClearResponse {
  detached_task_count: number;
  deleted_asset_count: number;
}

export interface DigitalHumanAudit {
  id: string;
  created_at: string;
  actor: string;
  action: string;
  resource_type: string;
  resource_id: string;
  request_id: string | null;
  details: Record<string, string>;
}

export type SpeechTaskStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export interface SpeechTask {
  id: string;
  plan_id: string;
  status: SpeechTaskStatus;
  provider_id: string;
  asset_id: string;
  error_code: string | null;
  source: string;
  priority: number;
  created_at: string;
  expires_at: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface SpeechPlanRequest {
  screen_id: string;
  component_id: string;
  text: string;
  language: string;
  provider_id: string;
  voice: string;
  rate: number;
  pitch: number;
  volume: number;
  data_fingerprint: string;
}

export interface SpeechPlan {
  id: string;
  screen_id: string;
  component_id: string;
  text: string;
  language: string;
  provider_id: string;
  voice: string;
  rate: number;
  pitch: number;
  volume: number;
  provider_version: string;
  content_hash: string;
  created_at: string;
}
