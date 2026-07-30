import type { Component } from "vue";

import type { DashboardDocument } from "../../contracts";
import type { JsonValue, QueryResult } from "../query/types";

export type ComponentInstance = NonNullable<
  DashboardDocument["components"]
>[number];
export type DataBinding = NonNullable<ComponentInstance["data_binding"]>;
export type RuntimeParameters = Record<string, JsonValue>;

export type BuiltinComponentType =
  | "builtin.text"
  | "builtin.image"
  | "builtin.kpi"
  | "builtin.table"
  | "builtin.progress"
  | "builtin.line"
  | "builtin.bar"
  | "builtin.pie"
  | "builtin.geo_map";

export type DataCapability = "none" | "single" | "table" | "series" | "geo";
export type RuntimeMode = "editor" | "standalone" | "embed";

export interface ComponentDefinition {
  type: BuiltinComponentType;
  label: string;
  defaultFrame: { width: number; height: number };
  defaultProps: Record<string, JsonValue>;
  dataCapability: DataCapability;
  component: Component;
}

export type QueryComponent = (
  componentId: string,
  parameters: RuntimeParameters,
  signal?: AbortSignal,
) => Promise<QueryResult>;

export type LoadAsset = (
  assetId: string,
  signal?: AbortSignal,
) => Promise<string>;

export type ComponentQueryStatus = "idle" | "loading" | "success" | "error";

export interface ComponentQueryState {
  status: ComponentQueryStatus;
  result: QueryResult | null;
  error: unknown | null;
}

export interface RuntimeInteraction {
  type: "set_parameter";
  name: string;
  value: JsonValue;
}
