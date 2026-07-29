export type Mode = "disabled" | "ttl" | "scheduled";
export type TtlSeconds = number | null;
export type DataSourceId = string | null;
export type DataType = "boolean" | "date" | "datetime" | "integer" | "number" | "string";
export type Name = string;
export type Fields = DatasetField[];
export type Id = string;
export type MaxRows = number;
export type Name1 = string;
export type Name2 = string;
export type Required = boolean;
export type Parameters = DatasetParameter[];
export type Query = TableQuery | SqlQuery | FileQuery | RestQuery;
export type Kind = "table";
export type SchemaName = string | null;
export type Table = string;
export type Kind1 = "sql";
export type Sql = string;
export type AssetId = string;
export type FileFormat = "csv" | "excel" | "json" | "parquet";
export type Kind2 = "file";
export type Kind3 = "rest";
export type Method = "GET" | "POST";
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
  default?: {
    [k: string]: unknown;
  };
  name: Name2;
  required?: Required;
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
}
export interface RestQuery {
  kind?: Kind3;
  method?: Method;
  url: Url;
}
export interface RefreshPolicy {
  cron?: Cron;
  interval_seconds?: IntervalSeconds;
  mode?: Mode1;
}
