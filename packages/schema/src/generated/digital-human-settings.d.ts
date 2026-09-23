export type AiContextLimit = number;
export type AiEnabled = boolean;
export type AiModel = string;
export type CooldownSeconds = number;
export type DailyAudioSecondsLimit = number;
export type DailyTaskLimit = number;
export type DataRetentionDays = number;
export type DefaultMuted = boolean;
export type DefaultSubtitles = boolean;
export type Enabled = boolean;
/**
 * @maxItems 200
 */
export type ForbiddenWords = string[];
export type ManualReviewRequired = boolean;
export type MaxSpeechSeconds = number;
/**
 * @maxItems 50
 */
export type SensitivePatterns = string[];
export type UpdatedAt = string;

export interface DigitalHumanSettingsResponse {
  ai_context_limit?: AiContextLimit;
  ai_enabled?: AiEnabled;
  ai_model?: AiModel;
  cooldown_seconds?: CooldownSeconds;
  daily_audio_seconds_limit?: DailyAudioSecondsLimit;
  daily_task_limit?: DailyTaskLimit;
  data_retention_days?: DataRetentionDays;
  default_muted?: DefaultMuted;
  default_subtitles?: DefaultSubtitles;
  enabled?: Enabled;
  forbidden_words?: ForbiddenWords;
  manual_review_required?: ManualReviewRequired;
  max_speech_seconds?: MaxSpeechSeconds;
  sensitive_patterns?: SensitivePatterns;
  updated_at: UpdatedAt;
}
