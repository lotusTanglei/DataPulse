export type Assumptions = string[];
/**
 * @minItems 1
 */
export type DatasetIds = [string, ...string[]];
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
export type Aggregation = "sum" | "avg" | "min" | "max" | "count";
export type Field1 = string;
export type Measures = Measure[];
export type Question = string;
export type ChartType = "area" | "bar" | "gauge" | "kpi" | "line" | "map" | "pie" | "progress" | "table";
export type RequiresConfirmation = boolean;
export type SchemaVersion = 1;
export type SortDirection = "asc" | "desc";
export type Field2 = string;
export type Sort = Sort1[];

export interface AnalysisPlan {
  assumptions?: Assumptions;
  dataset_ids: DatasetIds;
  dimensions?: Dimensions;
  filters?: Filters;
  measures?: Measures;
  question: Question;
  recommended_chart: ChartType;
  requires_confirmation?: RequiresConfirmation;
  schema_version?: SchemaVersion;
  sort?: Sort;
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
