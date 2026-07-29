export type DatasetId = string;
export type Dimensions = string[];
export type Field = string;
export type FilterOperator =
  | "equals"
  | "not_equals"
  | "greater_than"
  | "greater_than_or_equal"
  | "less_than"
  | "less_than_or_equal"
  | "in"
  | "not_in"
  | "contains"
  | "between"
  | "is_null"
  | "is_not_null";
export type Filters = Filter[];
export type Limit = number;
export type Aggregation = "none" | "sum" | "average" | "minimum" | "maximum" | "count" | "count_distinct";
export type Field1 = string;
export type Measures = Measure[];
export type SchemaVersion = 1;
export type SortDirection = "asc" | "desc";
export type Field2 = string;
export type Sort = Sort1[];
export type Title = string;
export type ChartType = "area" | "bar" | "funnel" | "gauge" | "line" | "map" | "pie" | "radar" | "scatter" | "table";

export interface ChartSpec {
  dataset_id: DatasetId;
  dimensions?: Dimensions;
  filters?: Filters;
  limit?: Limit;
  measures?: Measures;
  schema_version?: SchemaVersion;
  sort?: Sort;
  visual: VisualSpec;
}
export interface Filter {
  field: Field;
  operator: FilterOperator;
  value?: {
    [k: string]: unknown;
  };
}
export interface Measure {
  aggregation?: Aggregation;
  field: Field1;
}
export interface Sort1 {
  direction?: SortDirection;
  field: Field2;
}
export interface VisualSpec {
  title?: Title;
  type: ChartType;
}
