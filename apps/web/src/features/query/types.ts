import type { ConnectorType } from "../datasources/types";

export type JsonPrimitive = string | number | boolean | null;
export type JsonValue =
  | JsonPrimitive
  | JsonValue[]
  | { [key: string]: JsonValue };

export type ParameterDataType =
  | "boolean"
  | "date"
  | "datetime"
  | "integer"
  | "number"
  | "string";

export interface QueryParameterInput {
  name: string;
  data_type: ParameterDataType;
  value: JsonValue;
}

export interface QueryColumn {
  name: string;
  data_type: string;
}

export interface QueryResult {
  request_id: string;
  columns: QueryColumn[];
  rows: JsonValue[][];
  row_count: number;
  truncated: boolean;
  duration_ms: number;
}

export interface QueryRequest {
  sql: string;
  parameters: Record<string, JsonValue>;
  max_rows: number;
  timeout_seconds: number;
}

export type SqlDialect = ConnectorType;
