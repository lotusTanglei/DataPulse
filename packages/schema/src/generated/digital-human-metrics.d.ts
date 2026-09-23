export type AverageSynthesisMs = number;
export type CacheHits = number;
export type CollectedAt = string;
export type SynthesisAttempts = number;
export type SynthesisFailures = number;
export type SynthesisTotalMs = number;
export type TasksCancelled = number;
export type TasksFailed = number;
export type TasksQueued = number;
export type TasksSucceeded = number;

export interface DigitalHumanMetricsResponse {
  average_synthesis_ms: AverageSynthesisMs;
  cache_hits: CacheHits;
  collected_at: CollectedAt;
  synthesis_attempts: SynthesisAttempts;
  synthesis_failures: SynthesisFailures;
  synthesis_total_ms: SynthesisTotalMs;
  tasks_cancelled: TasksCancelled;
  tasks_failed: TasksFailed;
  tasks_queued: TasksQueued;
  tasks_succeeded: TasksSucceeded;
}
