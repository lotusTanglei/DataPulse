export type Mode = "disabled" | "ttl" | "scheduled";
export type TtlSeconds = number | null;
export type DataSourceId = string | null;
export type DataType = "boolean" | "date" | "datetime" | "integer" | "number" | "string";
export type Name = string;
export type Fields = DatasetField[];
export type Id = string;
export type MaxRows = number;
export type Name1 = string;
export type JsonValue =
  | JsonValue[]
  | {
      [k: string]: JsonValue;
    }
  | string
  | boolean
  | number
  | null;
export type Name2 = string;
export type Required = boolean;
export type Parameters = DatasetParameter[];
export type Aliases = string[];
export type DefaultAggregation = ("sum" | "avg" | "min" | "max" | "count") | null;
export type DisplayName = string | null;
export type Format = string | null;
export type Name3 = string;
export type Role =
  ("identifier" | "dimension" | "measure" | "geography" | "temporal" | "text" | "boolean" | "unknown") | null;
export type Unit = string | null;
export type ProfileOverrides = DatasetFieldOverride[];
export type Query = TableQuery | SqlQuery | FileQuery | RestQuery;
export type Kind = "table";
export type SchemaName = string | null;
export type Table = string;
export type Kind1 = "sql";
export type Sql = string;
export type AssetId = string;
export type FileFormat = "csv" | "excel" | "json" | "parquet";
export type Kind2 = "file";
export type SheetName = string | null;
export type Kind3 = "rest";
export type Method = "GET" | "POST";
export type ResponsePath = string | null;
export type Url = string;
export type Cron = string | null;
export type IntervalSeconds = number | null;
export type Mode1 = "manual" | "interval" | "cron";
export type SchemaVersion = 1;
export type Constant = number | null;
export type LeftField = string;
export type CalculationOperator = "add" | "subtract" | "multiply" | "divide";
export type RightField = string | null;
export type Format1 = string | null;
export type Label = string;
export type Name4 = string;
export type Unit1 = string | null;
export type CalculatedFields = DatasetCalculatedField[];
export type Kind4 = "dimension" | "time";
export type Label1 = string;
/**
 * @minItems 2
 */
export type Levels = [DatasetHierarchyLevel, DatasetHierarchyLevel, ...DatasetHierarchyLevel[]];
export type Field = string;
export type Label2 = string;
export type TimeGrain = "year" | "quarter" | "month" | "week" | "day" | "hour";
export type Name5 = string;
export type Hierarchies = DatasetHierarchy[];
export type Aggregation = "sum" | "avg" | "min" | "max" | "count";
export type Description = string | null;
export type Format2 = string | null;
export type Label3 = string;
export type Name6 = string;
export type SourceField = string;
export type Unit2 = string | null;
export type Metrics = DatasetMetric[];
export type Cardinality = "one_to_one" | "one_to_many" | "many_to_one";
export type LocalField = string;
export type Name7 = string;
export type TargetDatasetId = string;
export type TargetField = string;
export type Relationships = DatasetRelationship[];
export type TimeoutSeconds = number;

export interface DatasetDefinition {
  cache?: CachePolicy;
  data_source_id?: DataSourceId;
  fields?: Fields;
  id: Id;
  max_rows?: MaxRows;
  name: Name1;
  parameters?: Parameters;
  profile_overrides?: ProfileOverrides;
  query: Query;
  refresh?: RefreshPolicy;
  schema_version?: SchemaVersion;
  semantics?: DatasetSemantics;
  timeout_seconds?: TimeoutSeconds;
}
export interface CachePolicy {
  mode?: Mode;
  ttl_seconds?: TtlSeconds;
}
export interface DatasetField {
  data_type: DataType;
  name: Name;
}
export interface DatasetParameter {
  data_type: DataType;
  default?:
    | JsonValue[]
    | {
        [k: string]: JsonValue;
      }
    | string
    | boolean
    | number
    | null;
  name: Name2;
  required?: Required;
}
export interface DatasetFieldOverride {
  aliases?: Aliases;
  data_type?: DataType | null;
  default_aggregation?: DefaultAggregation;
  display_name?: DisplayName;
  format?: Format;
  name: Name3;
  role?: Role;
  unit?: Unit;
}
export interface TableQuery {
  kind?: Kind;
  schema_name?: SchemaName;
  table: Table;
}
export interface SqlQuery {
  kind?: Kind1;
  sql: Sql;
}
export interface FileQuery {
  asset_id: AssetId;
  format: FileFormat;
  kind?: Kind2;
  sheet_name?: SheetName;
}
export interface RestQuery {
  body?: JsonValue | null;
  kind?: Kind3;
  method?: Method;
  query?: Query1;
  response_path?: ResponsePath;
  url: Url;
}
export interface Query1 {
  [k: string]: JsonValue;
}
export interface RefreshPolicy {
  cron?: Cron;
  interval_seconds?: IntervalSeconds;
  mode?: Mode1;
}
export interface DatasetSemantics {
  calculated_fields?: CalculatedFields;
  hierarchies?: Hierarchies;
  metrics?: Metrics;
  relationships?: Relationships;
}
export interface DatasetCalculatedField {
  data_type: DataType;
  expression: CalculatedFieldExpression;
  format?: Format1;
  label: Label;
  name: Name4;
  unit?: Unit1;
}
export interface CalculatedFieldExpression {
  constant?: Constant;
  left_field: LeftField;
  operator: CalculationOperator;
  right_field?: RightField;
}
export interface DatasetHierarchy {
  kind: Kind4;
  label: Label1;
  levels: Levels;
  name: Name5;
}
export interface DatasetHierarchyLevel {
  field: Field;
  label: Label2;
  time_grain?: TimeGrain | null;
}
export interface DatasetMetric {
  aggregation: Aggregation;
  description?: Description;
  format?: Format2;
  label: Label3;
  name: Name6;
  source_field: SourceField;
  unit?: Unit2;
}
export interface DatasetRelationship {
  cardinality: Cardinality;
  local_field: LocalField;
  name: Name7;
  target_dataset_id: TargetDatasetId;
  target_field: TargetField;
}
