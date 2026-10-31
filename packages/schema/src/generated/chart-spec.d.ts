export type DatasetId = string;
export type Dimensions = string[];
export type LevelParameter = string;
/**
 * @minItems 2
 * @maxItems 8
 */
export type Levels =
  | [DrillDownLevel, DrillDownLevel]
  | [DrillDownLevel, DrillDownLevel, DrillDownLevel]
  | [DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel]
  | [DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel]
  | [DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel]
  | [DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel]
  | [
      DrillDownLevel,
      DrillDownLevel,
      DrillDownLevel,
      DrillDownLevel,
      DrillDownLevel,
      DrillDownLevel,
      DrillDownLevel,
      DrillDownLevel
    ];
export type Field = string;
export type SelectionParameter = string;
export type Field1 = string;
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
export type Field2 = string;
export type Measures = Measure[];
export type SchemaVersion = 1;
export type SortDirection = "asc" | "desc";
export type Field3 = string;
export type Sort = Sort1[];
/**
 * @maxItems 3
 */
export type TimeBuckets = [] | [TimeBucket] | [TimeBucket, TimeBucket] | [TimeBucket, TimeBucket, TimeBucket];
export type Field4 = string;
export type TimeGrain = "year" | "quarter" | "month" | "week" | "day" | "hour";
export type Parameter = string | null;
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
  drill_down?: DrillDownSpec | null;
  filters?: Filters;
  limit?: Limit;
  measures?: Measures;
  schema_version?: SchemaVersion;
  sort?: Sort;
  time_buckets?: TimeBuckets;
  visual: VisualSpec;
}
export interface DrillDownSpec {
  level_parameter: LevelParameter;
  levels: Levels;
}
export interface DrillDownLevel {
  field: Field;
  selection_parameter: SelectionParameter;
}
export interface Filter {
  field: Field1;
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
  field: Field2;
}
export interface Sort1 {
  direction?: SortDirection;
  field: Field3;
}
export interface TimeBucket {
  field: Field4;
  grain?: TimeGrain | null;
  parameter?: Parameter;
}
export interface VisualSpec {
  title?: Title;
  type: ChartType;
}
