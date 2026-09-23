export type Aggregations = string[];
export type DatasetId = string;
export type Fields = string[];
export type Filters = string[];
export type Code = string;
export type ComponentId = string | null;
export type Field = string;
export type Message = string;
export type Issues = GenerationIssue[];
export type RowCount = number;
export type Status = "ok" | "empty" | "error";
export type WidgetId = string;
export type Checks = WidgetSelfCheck[];
export type ExecutedCount = number;
export type FallbackCount = number;
export type Issues1 = GenerationIssue[];
export type Valid = boolean;
export type WidgetCount = number;

export interface GenerationSelfCheckReport {
  checks?: Checks;
  executed_count: ExecutedCount;
  fallback_count: FallbackCount;
  issues?: Issues1;
  valid: Valid;
  widget_count: WidgetCount;
}
export interface WidgetSelfCheck {
  aggregations?: Aggregations;
  dataset_id: DatasetId;
  fields?: Fields;
  filters?: Filters;
  issues?: Issues;
  row_count: RowCount;
  status: Status;
  widget_id: WidgetId;
}
export interface GenerationIssue {
  code: Code;
  component_id?: ComponentId;
  field: Field;
  message: Message;
}
