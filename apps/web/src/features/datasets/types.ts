import type {
  JsonValue,
  ParameterDataType,
  QueryResult,
} from "../query/types";

export interface DatasetField {
  name: string;
  data_type: ParameterDataType;
}

export type DatasetFieldRole =
  | "identifier"
  | "dimension"
  | "measure"
  | "geography"
  | "temporal"
  | "text"
  | "boolean"
  | "unknown";

export interface DatasetFieldProfile {
  name: string;
  data_type: ParameterDataType;
  role: DatasetFieldRole;
  nullable: boolean;
  null_count: number;
  null_rate?: number;
  unique_count: number;
  cardinality: number;
  uniqueness_ratio: number;
  min?: JsonValue | null;
  max?: JsonValue | null;
  top_values?: Array<{ value: JsonValue; count: number }>;
  sample_values: JsonValue[];
  default_aggregation?: DatasetAggregation | null;
  unit?: string | null;
  display_name?: string | null;
}

export type DatasetAggregation = "sum" | "avg" | "min" | "max" | "count";

export interface DatasetProfile {
  dataset_id: string;
  name: string;
  row_count: number;
  sampled: boolean;
  fields: DatasetFieldProfile[];
}

export interface DatasetProfilePatch {
  fields: Array<{
    name: string;
    data_type?: ParameterDataType;
    role?: DatasetFieldRole;
    default_aggregation?: DatasetAggregation;
    unit?: string;
    display_name?: string;
  }>;
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
  profile_overrides?: Array<{
    name: string;
    data_type: ParameterDataType | null;
    role: DatasetFieldRole | null;
    default_aggregation?: DatasetAggregation | null;
    unit?: string | null;
    display_name?: string | null;
  }>;
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
