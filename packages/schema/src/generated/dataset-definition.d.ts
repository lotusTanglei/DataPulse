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
export type DefaultAggregation = ("sum" | "avg" | "min" | "max" | "count") | null;
export type DisplayName = string | null;
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
  data_type?: DataType | null;
  default_aggregation?: DefaultAggregation;
  display_name?: DisplayName;
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
