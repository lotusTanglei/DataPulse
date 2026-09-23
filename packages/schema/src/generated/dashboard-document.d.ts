export type JsonValue =
  | JsonValue[]
  | {
      [k: string]: JsonValue;
    }
  | string
  | boolean
  | number
  | null;
export type Height = number;
export type Width = number;
export type Height1 = number;
export type Width1 = number;
export type X = number;
export type Y = number;
export type ZIndex = number;
export type Id = string;
export type Action = "set_parameter";
export type Event = "click";
export type Field = string;
export type Parameter = string;
export type Interactions = ComponentInteraction[];
export type GroupId = string | null;
export type Hidden = boolean;
export type Locked = boolean;
export type Type = string;
export type Components = ComponentInstance[];
export type AllowedValues = JsonValue[];
export type DataType = "boolean" | "date" | "datetime" | "integer" | "number" | "string";
export type Id1 = string;
export type Mutable = boolean;
export type Name = string;
export type Parameters = DashboardParameter[];
export type Id2 = string;
export type Version = string;
export type PluginDependencies = PluginDependency[];
export type IntervalSeconds = (10 | 30 | 60 | 300) | null;
export type Mode = "disabled" | "interval";
export type SchemaVersion = 1;
export type Id3 = string;

export interface DashboardDocument {
  canvas: Canvas;
  components?: Components;
  parameters?: Parameters;
  plugin_dependencies?: PluginDependencies;
  refresh?: ScreenRefreshPolicy;
  schema_version?: SchemaVersion;
  theme?: Theme;
}
export interface Canvas {
  background?: Background;
  height: Height;
  width: Width;
}
export interface Background {
  [k: string]: JsonValue;
}
export interface ComponentInstance {
  data_binding?: DataBinding;
  frame: Frame;
  id: Id;
  interactions?: Interactions;
  props?: Props;
  state?: ComponentState;
  style?: Style;
  type: Type;
}
export interface DataBinding {
  [k: string]: JsonValue;
}
export interface Frame {
  height: Height1;
  width: Width1;
  x: X;
  y: Y;
  z_index?: ZIndex;
}
export interface ComponentInteraction {
  action: Action;
  event: Event;
  field: Field;
  parameter: Parameter;
}
export interface Props {
  [k: string]: JsonValue;
}
export interface ComponentState {
  group_id?: GroupId;
  hidden?: Hidden;
  locked?: Locked;
}
export interface Style {
  [k: string]: JsonValue;
}
export interface DashboardParameter {
  allowed_values?: AllowedValues;
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
  id: Id1;
  mutable?: Mutable;
  name: Name;
}
export interface PluginDependency {
  id: Id2;
  version: Version;
}
export interface ScreenRefreshPolicy {
  interval_seconds?: IntervalSeconds;
  mode?: Mode;
}
export interface Theme {
  id?: Id3;
  tokens?: Tokens;
}
export interface Tokens {
  [k: string]: JsonValue;
}
