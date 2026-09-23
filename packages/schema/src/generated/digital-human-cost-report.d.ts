export type PeriodEnd = string;
export type PeriodStart = string;
export type CachedCount = number;
export type EstimatedCost = number;
export type FailedCount = number;
export type GeneratedSeconds = number;
export type ProviderId = string;
export type ProviderName = string;
export type SucceededCount = number;
export type TaskCount = number;
export type Rows = DigitalHumanCostReportRow[];
export type TotalEstimatedCost = number;
export type TotalGeneratedSeconds = number;
export type TotalTaskCount = number;

export interface DigitalHumanCostReportResponse {
  period_end: PeriodEnd;
  period_start: PeriodStart;
  rows: Rows;
  total_estimated_cost: TotalEstimatedCost;
  total_generated_seconds: TotalGeneratedSeconds;
  total_task_count: TotalTaskCount;
}
export interface DigitalHumanCostReportRow {
  cached_count: CachedCount;
  estimated_cost: EstimatedCost;
  failed_count: FailedCount;
  generated_seconds: GeneratedSeconds;
  provider_id: ProviderId;
  provider_name: ProviderName;
  succeeded_count: SucceededCount;
  task_count: TaskCount;
}
