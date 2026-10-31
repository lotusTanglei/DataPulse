export type Audience = string;
/**
 * @minItems 1
 * @maxItems 8
 */
export type DatasetIds =
  | [string]
  | [string, string]
  | [string, string, string]
  | [string, string, string, string]
  | [string, string, string, string, string]
  | [string, string, string, string, string, string]
  | [string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string];
export type Density = "comfortable" | "compact";
export type GridColumns = 12 | 24;
export type Template = "executive-overview" | "trend-focus" | "comparison-board" | "status-wall" | "analysis-lab";
export type Theme = "dark" | "light";
export type Narrative = string;
/**
 * @maxItems 12
 */
export type Parameters =
  | []
  | [DashboardParameter]
  | [DashboardParameter, DashboardParameter]
  | [DashboardParameter, DashboardParameter, DashboardParameter]
  | [DashboardParameter, DashboardParameter, DashboardParameter, DashboardParameter]
  | [DashboardParameter, DashboardParameter, DashboardParameter, DashboardParameter, DashboardParameter]
  | [
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter
    ]
  | [
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter
    ]
  | [
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter
    ]
  | [
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter
    ]
  | [
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter
    ]
  | [
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter
    ]
  | [
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter,
      DashboardParameter
    ];
export type JsonValue =
  | JsonValue[]
  | {
      [k: string]: JsonValue;
    }
  | string
  | boolean
  | number
  | number
  | null;
export type AllowedValues = JsonValue[];
export type DataType = "boolean" | "date" | "datetime" | "integer" | "number" | "string";
export type Id = string;
export type Mutable = boolean;
export type Name = string;
/**
 * @minItems 1
 * @maxItems 12
 */
export type Regions =
  | [PlanRegion]
  | [PlanRegion, PlanRegion]
  | [PlanRegion, PlanRegion, PlanRegion]
  | [PlanRegion, PlanRegion, PlanRegion, PlanRegion]
  | [PlanRegion, PlanRegion, PlanRegion, PlanRegion, PlanRegion]
  | [PlanRegion, PlanRegion, PlanRegion, PlanRegion, PlanRegion, PlanRegion]
  | [PlanRegion, PlanRegion, PlanRegion, PlanRegion, PlanRegion, PlanRegion, PlanRegion]
  | [PlanRegion, PlanRegion, PlanRegion, PlanRegion, PlanRegion, PlanRegion, PlanRegion, PlanRegion]
  | [PlanRegion, PlanRegion, PlanRegion, PlanRegion, PlanRegion, PlanRegion, PlanRegion, PlanRegion, PlanRegion]
  | [
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion
    ]
  | [
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion
    ]
  | [
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion,
      PlanRegion
    ];
export type Id1 = string;
export type Kind = "header" | "summary" | "main" | "secondary" | "sidebar" | "footer";
export type Order = number;
export type Title = string;
export type SchemaVersion = 1;
export type Title1 = string;
/**
 * @minItems 1
 * @maxItems 40
 */
export type Widgets = [PlanWidget, ...PlanWidget[]];
export type ChartType =
  | "area"
  | "bar"
  | "funnel"
  | "gauge"
  | "heatmap"
  | "kpi"
  | "line"
  | "map"
  | "pie"
  | "progress"
  | "radar"
  | "scatter"
  | "table";
export type DatasetId = string;
/**
 * @maxItems 3
 */
export type Dimensions = [] | [string] | [string, string] | [string, string, string];
export type LevelParameter = string;
/**
 * @minItems 2
 * @maxItems 8
 */
export type Levels =
  | [DrillDownLevel, DrillDownLevel]
  | [DrillDownLevel, DrillDownLevel, DrillDownLevel]
  | [DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel]
  | [DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel]
  | [DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel]
  | [DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel, DrillDownLevel]
  | [
      DrillDownLevel,
      DrillDownLevel,
      DrillDownLevel,
      DrillDownLevel,
      DrillDownLevel,
      DrillDownLevel,
      DrillDownLevel,
      DrillDownLevel
    ];
export type Field = string;
export type SelectionParameter = string;
/**
 * @maxItems 12
 */
export type Filters =
  | []
  | [Filter]
  | [Filter, Filter]
  | [Filter, Filter, Filter]
  | [Filter, Filter, Filter, Filter]
  | [Filter, Filter, Filter, Filter, Filter]
  | [Filter, Filter, Filter, Filter, Filter, Filter]
  | [Filter, Filter, Filter, Filter, Filter, Filter, Filter]
  | [Filter, Filter, Filter, Filter, Filter, Filter, Filter, Filter]
  | [Filter, Filter, Filter, Filter, Filter, Filter, Filter, Filter, Filter]
  | [Filter, Filter, Filter, Filter, Filter, Filter, Filter, Filter, Filter, Filter]
  | [Filter, Filter, Filter, Filter, Filter, Filter, Filter, Filter, Filter, Filter, Filter]
  | [Filter, Filter, Filter, Filter, Filter, Filter, Filter, Filter, Filter, Filter, Filter, Filter];
export type Field1 = string;
export type FilterOperator =
  | "equals"
  | "not_equals"
  | "greater_than"
  | "greater_than_or_equal"
  | "less_than"
  | "less_than_or_equal"
  | "in"
  | "not_in"
  | "contains"
  | "between"
  | "is_null"
  | "is_not_null";
export type Value = ParameterRef | LiteralValue;
export type Kind1 = "parameter";
export type Name1 = string;
export type Kind2 = "literal";
export type Id2 = string;
export type Intent = string;
/**
 * @maxItems 8
 */
export type Interactions =
  | []
  | [ComponentInteraction]
  | [ComponentInteraction, ComponentInteraction]
  | [ComponentInteraction, ComponentInteraction, ComponentInteraction]
  | [ComponentInteraction, ComponentInteraction, ComponentInteraction, ComponentInteraction]
  | [ComponentInteraction, ComponentInteraction, ComponentInteraction, ComponentInteraction, ComponentInteraction]
  | [
      ComponentInteraction,
      ComponentInteraction,
      ComponentInteraction,
      ComponentInteraction,
      ComponentInteraction,
      ComponentInteraction
    ]
  | [
      ComponentInteraction,
      ComponentInteraction,
      ComponentInteraction,
      ComponentInteraction,
      ComponentInteraction,
      ComponentInteraction,
      ComponentInteraction
    ]
  | [
      ComponentInteraction,
      ComponentInteraction,
      ComponentInteraction,
      ComponentInteraction,
      ComponentInteraction,
      ComponentInteraction,
      ComponentInteraction,
      ComponentInteraction
    ];
export type Action = "set_parameter";
export type Event = "click";
export type Field2 = string;
export type Parameter = string;
export type Limit = number;
/**
 * @maxItems 4
 */
export type Measures =
  [] | [Measure] | [Measure, Measure] | [Measure, Measure, Measure] | [Measure, Measure, Measure, Measure];
export type Aggregation = "sum" | "avg" | "min" | "max" | "count";
export type Field3 = string;
export type RegionId = string;
/**
 * @maxItems 4
 */
export type Sort = [] | [Sort1] | [Sort1, Sort1] | [Sort1, Sort1, Sort1] | [Sort1, Sort1, Sort1, Sort1];
export type SortDirection = "asc" | "desc";
export type Field4 = string;
/**
 * @maxItems 3
 */
export type TimeBuckets = [] | [TimeBucket] | [TimeBucket, TimeBucket] | [TimeBucket, TimeBucket, TimeBucket];
export type Field5 = string;
export type TimeGrain = "year" | "quarter" | "month" | "week" | "day" | "hour";
export type Parameter1 = string | null;
export type Title2 = string;

export interface DashboardPlan {
  audience: Audience;
  dataset_ids: DatasetIds;
  layout?: PlanLayout;
  narrative: Narrative;
  parameters?: Parameters;
  regions: Regions;
  schema_version?: SchemaVersion;
  title: Title1;
  widgets: Widgets;
}
export interface PlanLayout {
  density?: Density;
  grid_columns?: GridColumns;
  template?: Template;
  theme?: Theme;
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
    | number
    | null;
  id: Id;
  mutable?: Mutable;
  name: Name;
}
export interface PlanRegion {
  id: Id1;
  kind: Kind;
  order?: Order;
  title?: Title;
}
export interface PlanWidget {
  chart_type: ChartType;
  dataset_id: DatasetId;
  dimensions?: Dimensions;
  drill_down?: DrillDownSpec | null;
  filters?: Filters;
  id: Id2;
  intent: Intent;
  interactions?: Interactions;
  limit?: Limit;
  measures?: Measures;
  region_id: RegionId;
  sort?: Sort;
  time_buckets?: TimeBuckets;
  title: Title2;
}
export interface DrillDownSpec {
  level_parameter: LevelParameter;
  levels: Levels;
}
export interface DrillDownLevel {
  field: Field;
  selection_parameter: SelectionParameter;
}
export interface Filter {
  field: Field1;
  operator: FilterOperator;
  value?: Value;
}
export interface ParameterRef {
  kind?: Kind1;
  name: Name1;
}
export interface LiteralValue {
  kind?: Kind2;
  value?:
    | JsonValue[]
    | {
        [k: string]: JsonValue;
      }
    | string
    | boolean
    | number
    | number
    | null;
}
export interface ComponentInteraction {
  action: Action;
  event: Event;
  field: Field2;
  parameter: Parameter;
}
export interface Measure {
  aggregation: Aggregation;
  field: Field3;
}
export interface Sort1 {
  direction?: SortDirection;
  field: Field4;
}
export interface TimeBucket {
  field: Field5;
  grain?: TimeGrain | null;
  parameter?: Parameter1;
}
