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
export type Value = ParameterRef | LiteralValue;
export type Kind = "parameter";
export type Name = string;
export type Kind1 = "literal";
export type JsonValue =
  | JsonValue[]
  | {
      [k: string]: JsonValue;
    }
  | string
  | boolean
  | number
  | null;
export type Filters = Filter[];
export type Limit = number;
export type Aggregation = "sum" | "avg" | "min" | "max" | "count";
export type Field1 = string;
export type Measures = Measure[];
export type SchemaVersion = 1;
export type SortDirection = "asc" | "desc";
export type Field2 = string;
export type Sort = Sort1[];
export type Title = string;
export type ChartType =
  | "area"
  | "bar"
  | "funnel"
  | "gauge"
  | "heatmap"
  | "kpi"
  | "line"
  | "map"
  | "pie"
  | "progress"
  | "radar"
  | "scatter"
  | "table";

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
  value?: Value;
}
export interface ParameterRef {
  kind?: Kind;
  name: Name;
}
export interface LiteralValue {
  kind?: Kind1;
  value?:
    | JsonValue[]
    | {
        [k: string]: JsonValue;
      }
    | string
    | boolean
    | number
    | null;
}
export interface Measure {
  aggregation: Aggregation;
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
