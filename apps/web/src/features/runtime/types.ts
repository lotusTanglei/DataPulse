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
  | "builtin.panel"
  | "builtin.divider"
  | "builtin.digital_number"
  | "builtin.kpi"
  | "builtin.table"
  | "builtin.progress"
  | "builtin.gauge"
  | "builtin.status_matrix"
  | "builtin.line"
  | "builtin.bar"
  | "builtin.pie"
  | "builtin.radar"
  | "builtin.heatmap"
  | "builtin.scatter"
  | "builtin.funnel"
  | "builtin.ranking"
  | "builtin.alert_list"
  | "builtin.timeline"
  | "builtin.geo_map"
  | "builtin.digital_human";

export type DataCapability = "none" | "single" | "table" | "series" | "geo";
export type ComponentCategory =
  | "基础与装饰"
  | "指标与状态"
  | "图表"
  | "列表与分析"
  | "地图";
export type DemoDataKind =
  | "none"
  | "single"
  | "series"
  | "table"
  | "ranking"
  | "alerts"
  | "radar"
  | "geo";
export type RuntimeMode = "editor" | "preview" | "standalone" | "embed";

export type PropertyEditor = "text" | "number" | "select" | "boolean" | "color";

export interface PropertyOption {
  label: string;
  value: JsonValue;
}

export interface PropertyDefinition {
  name: string;
  label: string;
  editor: PropertyEditor;
  defaultValue?: JsonValue;
  min?: number;
  max?: number;
  step?: number;
  placeholder?: string;
  options?: PropertyOption[];
  wide?: boolean;
}

export interface PropertyGroup {
  id: string;
  label: string;
  properties: PropertyDefinition[];
}

export interface ComponentDefinition {
  type: string;
  label: string;
  category?: string;
  defaultFrame: { width: number; height: number };
  defaultProps: Record<string, JsonValue>;
  defaultStyle?: Record<string, JsonValue>;
  dataCapability: DataCapability;
  demoDataKind?: DemoDataKind;
  propertyGroups?: PropertyGroup[];
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
  updatedAt?: number;
}

export interface RuntimeInteraction {
  type: "set_parameter";
  name: string;
  value: JsonValue;
}
