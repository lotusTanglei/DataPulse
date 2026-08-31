import type { ChartSpec } from "../../../contracts";
import type { JsonValue } from "../../query/types";
import { defaultComponentRegistry } from "../../runtime/registry";
import type {
  BuiltinComponentType,
  ComponentInstance,
} from "../../runtime/types";

const COMPONENT_TYPE_BY_CHART: Record<
  ChartSpec["visual"]["type"],
  BuiltinComponentType
> = {
  area: "builtin.line",
  bar: "builtin.bar",
  funnel: "builtin.funnel",
  gauge: "builtin.progress",
  heatmap: "builtin.heatmap",
  kpi: "builtin.kpi",
  line: "builtin.line",
  map: "builtin.geo_map",
  pie: "builtin.pie",
  progress: "builtin.progress",
  radar: "builtin.radar",
  scatter: "builtin.scatter",
  table: "builtin.table",
};

const CHART_TYPE_BY_COMPONENT: Partial<
  Record<BuiltinComponentType, ChartSpec["visual"]["type"]>
> = {
  "builtin.bar": "bar",
  "builtin.funnel": "funnel",
  "builtin.geo_map": "map",
  "builtin.heatmap": "heatmap",
  "builtin.kpi": "kpi",
  "builtin.line": "line",
  "builtin.pie": "pie",
  "builtin.progress": "progress",
  "builtin.radar": "radar",
  "builtin.scatter": "scatter",
  "builtin.table": "table",
  "builtin.digital_number": "kpi",
  "builtin.gauge": "gauge",
  "builtin.ranking": "table",
  "builtin.alert_list": "table",
  "builtin.status_matrix": "table",
  "builtin.timeline": "table",
};

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function pickString(
  props: Record<string, JsonValue> | undefined,
  key: string,
): string | undefined {
  const value = props?.[key];
  return typeof value === "string" ? value : undefined;
}

function pickNumber(
  props: Record<string, JsonValue> | undefined,
  key: string,
): number | undefined {
  const value = props?.[key];
  return typeof value === "number" ? value : undefined;
}

export function chartSpecToComponentType(
  chartType: ChartSpec["visual"]["type"],
): BuiltinComponentType {
  return COMPONENT_TYPE_BY_CHART[chartType];
}

export function componentTypeToChartType(
  componentType: string,
): ChartSpec["visual"]["type"] | null {
  return CHART_TYPE_BY_COMPONENT[componentType as BuiltinComponentType] ?? null;
}

export function buildChartSuggestionProps(
  chartSpec: ChartSpec,
  currentProps?: Record<string, JsonValue>,
): Record<string, JsonValue> {
  const componentType = chartSpecToComponentType(chartSpec.visual.type);
  const definition = defaultComponentRegistry.get(componentType);
  const nextProps = structuredClone(definition?.defaultProps ?? {});
  const title = (chartSpec.visual.title ?? "").trim();
  const emptyText = pickString(currentProps, "empty_text");
  if (emptyText) {
    nextProps.empty_text = emptyText;
  }

  if (
    componentType === "builtin.kpi" ||
    componentType === "builtin.progress" ||
    componentType === "builtin.digital_number" ||
    componentType === "builtin.gauge"
  ) {
    nextProps.label = title || pickString(currentProps, "label") || definition?.label || "";
    const precision = pickNumber(currentProps, "precision");
    if (precision !== undefined) {
      nextProps.precision = precision;
    }
    const prefix = pickString(currentProps, "prefix");
    if (prefix !== undefined) {
      nextProps.prefix = prefix;
    }
    const suffix = pickString(currentProps, "suffix");
    if (suffix !== undefined) {
      nextProps.suffix = suffix;
    }
  } else if (
    componentType === "builtin.line" ||
    componentType === "builtin.bar" ||
    componentType === "builtin.pie" ||
    componentType === "builtin.radar" ||
    componentType === "builtin.heatmap" ||
    componentType === "builtin.scatter" ||
    componentType === "builtin.funnel" ||
    componentType === "builtin.ranking" ||
    componentType === "builtin.alert_list" ||
    componentType === "builtin.status_matrix" ||
    componentType === "builtin.timeline" ||
    componentType === "builtin.geo_map"
  ) {
    if (title) {
      nextProps.title = title;
    }
  }

  if (componentType === "builtin.geo_map") {
    const assetId = pickString(currentProps, "asset_id");
    if (assetId !== undefined) {
      nextProps.asset_id = assetId;
    }
    const regionCodeProperty = pickString(currentProps, "region_code_property");
    if (regionCodeProperty !== undefined) {
      nextProps.region_code_property = regionCodeProperty;
    }
    const regionNameProperty = pickString(currentProps, "region_name_property");
    if (regionNameProperty !== undefined) {
      nextProps.region_name_property = regionNameProperty;
    }
  }

  if (componentType === "builtin.table") {
    const maxRows = pickNumber(currentProps, "max_rows");
    if (maxRows !== undefined) {
      nextProps.max_rows = maxRows;
    }
  }

  return nextProps;
}

export function createSuggestedComponent(
  component: ComponentInstance,
  chartSpec: ChartSpec,
): ComponentInstance {
  return {
    ...cloneJson(component),
    type: chartSpecToComponentType(chartSpec.visual.type),
    props: buildChartSuggestionProps(
      chartSpec,
      (component.props ?? {}) as Record<string, JsonValue>,
    ),
    data_binding: {
      ...(component.data_binding ?? {}),
      chart_spec: cloneJson(chartSpec) as unknown as JsonValue,
    },
  };
}

export function createChartSuggestionPreviewInstance(
  chartSpec: ChartSpec,
  currentProps?: Record<string, JsonValue>,
): ComponentInstance {
  const componentType = chartSpecToComponentType(chartSpec.visual.type);
  const definition = defaultComponentRegistry.get(componentType);
  const frame = definition?.defaultFrame ?? { width: 640, height: 360 };
  return {
    id: "ai-chart-preview",
    type: componentType,
    frame: { x: 0, y: 0, width: frame.width, height: frame.height, z_index: 0 },
    props: buildChartSuggestionProps(chartSpec, currentProps),
    style: {},
    state: { locked: false, hidden: false },
    data_binding: {
      chart_spec: cloneJson(chartSpec) as unknown as JsonValue,
    },
    interactions: [],
  };
}
