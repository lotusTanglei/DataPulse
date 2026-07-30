import type { EChartsOption } from "echarts";

import type { JsonValue, QueryResult } from "../../query/types";
import type { ComponentInstance } from "../types";
import { numericValue, stringProp } from "./format";

export type ChartTheme = Record<string, JsonValue>;

export interface GeoFeature {
  type: "Feature";
  properties: Record<string, JsonValue>;
  geometry: { type: string; coordinates?: JsonValue };
}

export interface GeoFeatureCollection {
  type: "FeatureCollection";
  features: GeoFeature[];
}

function chartSpec(instance: ComponentInstance): Record<string, JsonValue> {
  const value = instance.data_binding?.chart_spec;
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value
    : {};
}

function visual(instance: ComponentInstance): Record<string, JsonValue> {
  const value = chartSpec(instance).visual;
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value
    : {};
}

function palette(theme: ChartTheme): string[] {
  const colors = theme.chart_colors;
  if (Array.isArray(colors)) {
    const safeColors = colors.filter(
      (color): color is string => typeof color === "string",
    );
    if (safeColors.length > 0) {
      return safeColors;
    }
  }
  return ["#3b82f6", "#22c55e", "#f59e0b", "#a855f7", "#ef4444"];
}

function themeColor(
  theme: ChartTheme,
  name: string,
  fallback: string,
): string {
  const value = theme[name];
  return typeof value === "string" ? value : fallback;
}

function baseOption(instance: ComponentInstance, theme: ChartTheme) {
  const visualTitle = visual(instance).title;
  const title =
    stringProp(instance.props, "title") ||
    (typeof visualTitle === "string" ? visualTitle : "");
  const textColor = themeColor(theme, "text_primary", "#e2e8f0");
  const mutedColor = themeColor(theme, "text_secondary", "#94a3b8");
  const borderColor = themeColor(theme, "component_border", "#334155");
  return {
    animationDuration: 350,
    color: palette(theme),
    textStyle: { color: textColor },
    title: title
      ? { text: title, left: 12, top: 8, textStyle: { color: textColor } }
      : undefined,
    tooltip: { trigger: "item" as const },
    legend: { top: 10, right: 12, textStyle: { color: mutedColor } },
    grid: { left: 48, right: 24, top: title ? 56 : 36, bottom: 40 },
    axisLine: { lineStyle: { color: borderColor } },
  };
}

function categories(result: QueryResult): string[] {
  return result.rows.map((row) => String(row[0] ?? ""));
}

function measureData(result: QueryResult, columnIndex: number): Array<number | null> {
  return result.rows.map((row) => numericValue(row[columnIndex]));
}

export function buildChartOption(
  instance: ComponentInstance,
  result: QueryResult,
  theme: ChartTheme,
): EChartsOption {
  const base = baseOption(instance, theme);
  const labels = categories(result);
  const measures = result.columns.slice(1);
  const visualType = visual(instance).type;

  if (instance.type === "builtin.pie") {
    const donut = stringProp(instance.props, "variant") === "donut";
    return {
      ...base,
      tooltip: { trigger: "item" },
      series: [
        {
          type: "pie",
          name: measures[0]?.name ?? "value",
          radius: donut ? ["48%", "72%"] : "72%",
          data: result.rows.map((row) => ({
            name: String(row[0] ?? ""),
            value: numericValue(row[1]) ?? 0,
          })),
        },
      ],
    };
  }

  const horizontal =
    instance.type === "builtin.bar" &&
    stringProp(instance.props, "orientation") === "horizontal";
  const valueAxis = {
    type: "value" as const,
    axisLine: base.axisLine,
    splitLine: { lineStyle: { color: base.axisLine.lineStyle.color } },
  };
  const categoryAxis = {
    type: "category" as const,
    data: labels,
    axisLine: base.axisLine,
    axisLabel: { color: base.textStyle.color },
  };
  const isArea = visualType === "area";
  const series = measures.map((column, measureIndex) => ({
    type: instance.type === "builtin.bar" ? ("bar" as const) : ("line" as const),
    name: column.name,
    data: measureData(result, measureIndex + 1),
    ...(isArea ? { areaStyle: {} } : {}),
  }));

  return {
    ...base,
    tooltip: { trigger: "axis" },
    xAxis: horizontal ? valueAxis : categoryAxis,
    yAxis: horizontal ? categoryAxis : valueAxis,
    series,
  };
}

export function buildGeoMapOption(
  instance: ComponentInstance,
  result: QueryResult,
  mapName: string,
  geojson: GeoFeatureCollection,
  theme: ChartTheme,
): EChartsOption {
  const codeProperty = stringProp(
    instance.props,
    "region_code_property",
    "code",
  );
  const nameProperty = stringProp(
    instance.props,
    "region_name_property",
    "name",
  );
  const values = new Map(
    result.rows.map((row) => [String(row[0] ?? ""), numericValue(row[1])]),
  );
  return {
    ...baseOption(instance, theme),
    visualMap: {
      left: 16,
      bottom: 16,
      calculable: true,
      textStyle: {
        color: themeColor(theme, "text_secondary", "#94a3b8"),
      },
    },
    series: [
      {
        type: "map",
        map: mapName,
        data: geojson.features.map((feature) => {
          const code = String(feature.properties[codeProperty] ?? "");
          return {
            name: String(feature.properties[nameProperty] ?? code),
            value: values.get(code) ?? "-",
          };
        }),
      },
    ],
  };
}
