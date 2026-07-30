export type ConnectorType = "sqlite" | "postgresql" | "mysql";
export type DatasourceStatus = "unknown" | "available" | "unavailable";

export interface SQLiteConfig {
  type: "sqlite";
  path: string;
}

export interface PostgreSQLConfig {
  type: "postgresql";
  host: string;
  port: number;
  database: string;
  username: string;
  ssl_mode:
    | "disable"
    | "allow"
    | "prefer"
    | "require"
    | "verify-ca"
    | "verify-full";
}

export interface MySQLConfig {
  type: "mysql";
  host: string;
  port: number;
  database: string;
  username: string;
  ssl_mode: "disabled" | "preferred" | "required";
}

export type DatasourceConfig =
  | SQLiteConfig
  | PostgreSQLConfig
  | MySQLConfig;

export interface Datasource {
  id: string;
  name: string;
  config: DatasourceConfig;
  status: DatasourceStatus;
  has_password: boolean;
  last_checked_at: string | null;
  last_latency_ms: number | null;
  last_error_code: string | null;
  created_at: string;
  updated_at: string;
}

export interface DatasourceCreatePayload {
  name: string;
  config: DatasourceConfig;
  password?: string;
}

export interface DatasourceUpdatePayload {
  name?: string;
  config?: DatasourceConfig;
  password?: string;
  clear_password?: boolean;
}

export interface NamespaceInfo {
  name: string | null;
}

export interface RelationInfo {
  namespace: string | null;
  name: string;
  kind: "table" | "view";
}

export interface RelationField {
  name: string;
  data_type: string;
  nullable: boolean;
}

export interface RelationSchema {
  namespace: string | null;
  name: string;
  kind: "table" | "view";
  fields: RelationField[];
}
