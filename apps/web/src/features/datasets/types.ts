import type {
  JsonValue,
  ParameterDataType,
  QueryResult,
} from "../query/types";

export interface DatasetField {
  name: string;
  data_type: ParameterDataType;
}

export interface DatasetParameter {
  name: string;
  data_type: ParameterDataType;
  required: boolean;
  default: JsonValue;
}

export interface DatasetDefinition {
  schema_version: 1;
  id: string;
  name: string;
  data_source_id: string | null;
  query:
    | { kind: "sql"; sql: string }
    | { kind: "table"; table: string; schema_name: string | null }
    | {
        kind: "file";
        asset_id: string;
        format: "csv" | "excel" | "json" | "parquet";
        sheet_name: string | null;
      }
    | {
        kind: "rest";
        method: "GET" | "POST";
        url: string;
        query: Record<string, JsonValue>;
        body: JsonValue | null;
        response_path: string | null;
      };
  fields: DatasetField[];
  parameters: DatasetParameter[];
  cache: {
    mode: "disabled" | "ttl" | "scheduled";
    ttl_seconds: number | null;
  };
  refresh: {
    mode: "manual" | "interval" | "cron";
    interval_seconds: number | null;
    cron: string | null;
  };
  max_rows: number;
  timeout_seconds: number;
}

export interface Dataset {
  id: string;
  name: string;
  data_source_id: string | null;
  definition: DatasetDefinition;
  created_at: string;
  updated_at: string;
}

export interface DatasetCreatePayload {
  name: string;
  data_source_id: string;
  sql?: string;
  query?: {
    kind: "rest";
    method: "GET" | "POST";
    url: string;
    query: Record<string, JsonValue>;
    body: JsonValue | null;
    response_path: string | null;
  };
  parameters: DatasetParameter[];
  max_rows: number;
  timeout_seconds: number;
}

export interface DatasetUpdatePayload {
  name?: string;
  sql?: string;
  query?: DatasetCreatePayload["query"];
  parameters?: DatasetParameter[];
  max_rows?: number;
  timeout_seconds?: number;
}

export interface DatasetPreviewPayload {
  parameters: Record<string, JsonValue>;
}

export type { QueryResult };
