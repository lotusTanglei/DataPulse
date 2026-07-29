export type Height = number;
export type Width = number;
export type JsonValue = unknown;
export type Height1 = number;
export type Rotation = number;
export type Width1 = number;
export type X = number;
export type Y = number;
export type ZIndex = number;
export type Id = string;
export type Id1 = string;
export type Version = string;
export type Type = string;
export type Components = ComponentInstance[];
export type Action = string;
export type Event = string;
export type Id2 = string;
export type Parameter = string | null;
export type SourceComponentId = string;
export type TargetComponentId = string | null;
export type Interactions = Interaction[];
export type Id3 = string;
export type Name = string;
export type Parameters = DashboardParameter[];
export type SchemaVersion = 1;

export interface DashboardDocument {
  canvas: Canvas;
  components?: Components;
  interactions?: Interactions;
  parameters?: Parameters;
  schema_version?: SchemaVersion;
  theme?: Theme;
}
export interface Canvas {
  height: Height;
  width: Width;
}
export interface ComponentInstance {
  data_binding?: DataBinding;
  geometry: Geometry;
  id: Id;
  plugin: PluginRef;
  properties?: Properties;
  style?: Style;
  type: Type;
}
export interface DataBinding {
  [k: string]: JsonValue;
}
export interface Geometry {
  height: Height1;
  rotation?: Rotation;
  width: Width1;
  x: X;
  y: Y;
  z_index?: ZIndex;
}
export interface PluginRef {
  id: Id1;
  version: Version;
}
export interface Properties {
  [k: string]: JsonValue;
}
export interface Style {
  [k: string]: JsonValue;
}
export interface Interaction {
  action: Action;
  event: Event;
  id: Id2;
  parameter?: Parameter;
  source_component_id: SourceComponentId;
  target_component_id?: TargetComponentId;
}
export interface DashboardParameter {
  id: Id3;
  name: Name;
  value?: {
    [k: string]: unknown;
  };
}
export interface Theme {
  variables?: Variables;
}
export interface Variables {
  [k: string]: JsonValue;
}
