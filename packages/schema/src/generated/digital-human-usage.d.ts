export type CachedCount = number;
export type EstimatedCost = number;
export type FailedCount = number;
export type GeneratedSeconds = number;
export type PeriodStart = string;
export type SucceededCount = number;
export type TaskCount = number;

export interface DigitalHumanUsageResponse {
  cached_count: CachedCount;
  estimated_cost?: EstimatedCost;
  failed_count: FailedCount;
  generated_seconds: GeneratedSeconds;
  period_start: PeriodStart;
  succeeded_count: SucceededCount;
  task_count: TaskCount;
}
