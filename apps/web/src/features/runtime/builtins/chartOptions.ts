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

function booleanProp(
  props: ComponentInstance["props"],
  name: string,
  fallback: boolean,
): boolean {
  const value = props?.[name];
  return typeof value === "boolean" ? value : fallback;
}

function baseOption(instance: ComponentInstance, theme: ChartTheme) {
  const visualTitle = visual(instance).title;
  const title =
    stringProp(instance.props, "title") ||
    (typeof visualTitle === "string" ? visualTitle : "");
  const textColor = themeColor(theme, "text_primary", "#e2e8f0");
  const mutedColor = themeColor(theme, "text_secondary", "#94a3b8");
  const borderColor = themeColor(
    theme,
    "chart_axis",
    themeColor(theme, "component_border", "#334155"),
  );
  const gridColor = themeColor(theme, "chart_grid", "rgba(148, 163, 184, 0.14)");
  const showLegend = booleanProp(instance.props, "show_legend", true);
  return {
    animation: booleanProp(instance.props, "animation", true),
    animationDuration: 500,
    color: palette(theme),
    textStyle: { color: textColor },
    title: title
      ? {
          text: title,
          left: 14,
          top: 12,
          textStyle: { color: textColor, fontSize: 14, fontWeight: 600 },
        }
      : undefined,
    tooltip: {
      trigger: "item" as const,
      backgroundColor: themeColor(theme, "panel_background_alt", "#10253a"),
      borderColor,
      textStyle: { color: textColor },
      confine: true,
    },
    legend: {
      show: showLegend,
      top: title ? 12 : 8,
      right: 14,
      textStyle: { color: mutedColor, fontSize: 11 },
      itemWidth: 12,
      itemHeight: 8,
    },
    grid: {
      left: 52,
      right: 24,
      top: title ? 58 : 38,
      bottom: 40,
      outerBoundsMode: "same" as const,
    },
    axisLine: { lineStyle: { color: borderColor } },
    axisLabel: { color: mutedColor, fontSize: 10 },
    splitLine: { lineStyle: { color: gridColor, type: "dashed" as const } },
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
          center: ["50%", "54%"],
          label: { color: base.textStyle.color, formatter: "{b}  {d}%" },
          labelLine: { lineStyle: { color: base.axisLine.lineStyle.color } },
          data: result.rows.map((row) => ({
            name: String(row[0] ?? ""),
            value: numericValue(row[1]) ?? 0,
          })),
        },
      ],
    };
  }

  if (instance.type === "builtin.radar") {
    const indicatorLabels = result.rows.map((row) => String(row[0] ?? ""));
    const maximum = Math.max(
      100,
      ...result.rows.flatMap((row) =>
        row.slice(1).map((value) => numericValue(value) ?? 0),
      ),
    );
    return {
      ...base,
      legend: { ...base.legend, bottom: 8, top: undefined },
      radar: {
        center: ["50%", "54%"],
        radius: "62%",
        indicator: indicatorLabels.map((name) => ({ name, max: maximum })),
        axisName: { color: base.textStyle.color, fontSize: 10 },
        splitLine: { lineStyle: { color: base.splitLine.lineStyle.color } },
        splitArea: {
          areaStyle: {
            color: [
              "rgba(38, 217, 193, 0.02)",
              "rgba(38, 217, 193, 0.06)",
            ],
          },
        },
      },
      series: measures.map((column, measureIndex) => ({
        type: "radar" as const,
        name: column.name,
        symbol: "circle",
        symbolSize: 5,
        lineStyle: { width: 2 },
        areaStyle: { opacity: 0.12 },
        data: [
          {
            value: result.rows.map(
              (row) => numericValue(row[measureIndex + 1]) ?? 0,
            ),
            name: column.name,
          },
        ],
      })),
    };
  }

  if (instance.type === "builtin.heatmap") {
    const xLabels = labels;
    const heatmapMeasures = measures.length > 0 ? measures : [{ name: "value" }];
    const heatmapData = heatmapMeasures.flatMap((column, measureIndex) =>
      result.rows.map((row, rowIndex) => [
        rowIndex,
        measureIndex,
        numericValue(row[measureIndex + 1]) ?? 0,
      ]),
    );
    return {
      ...base,
      grid: { ...base.grid, left: 64, bottom: 48 },
      xAxis: {
        type: "category" as const,
        data: xLabels,
        axisLabel: { color: base.axisLabel.color, rotate: xLabels.length > 8 ? 35 : 0 },
        axisLine: base.axisLine,
      },
      yAxis: {
        type: "category" as const,
        data: heatmapMeasures.map((column) => column.name),
        axisLabel: { color: base.axisLabel.color },
        axisLine: base.axisLine,
      },
      visualMap: {
        min: 0,
        max: Math.max(...heatmapData.map((item) => Number(item[2])), 1),
        calculable: true,
        orient: "horizontal" as const,
        left: "center",
        bottom: 4,
        textStyle: { color: base.textStyle.color, fontSize: 10 },
      },
      series: [{
        type: "heatmap" as const,
        data: heatmapData,
        label: { show: heatmapData.length < 50, color: base.textStyle.color, fontSize: 9 },
        itemStyle: { borderColor: themeColor(theme, "panel_background", "#0b1b2b"), borderWidth: 1 },
      }],
    };
  }

  if (instance.type === "builtin.scatter") {
    const xName = measures[0]?.name ?? "x";
    const yName = measures[1]?.name ?? measures[0]?.name ?? "y";
    return {
      ...base,
      tooltip: {
        ...base.tooltip,
        formatter: (params: unknown) => {
          if (!params || typeof params !== "object") return "";
          const value = (params as { value?: unknown }).value;
          return `${xName}: ${Array.isArray(value) ? value[0] ?? "—" : "—"}<br/>${yName}: ${Array.isArray(value) ? value[1] ?? "—" : "—"}`;
        },
      },
      xAxis: { type: "value" as const, name: xName, axisLine: base.axisLine, axisLabel: base.axisLabel, splitLine: base.splitLine },
      yAxis: { type: "value" as const, name: yName, axisLine: base.axisLine, axisLabel: base.axisLabel, splitLine: base.splitLine },
      series: [{
        type: "scatter" as const,
        symbolSize: 10,
        data: result.rows.map((row) => [
          numericValue(row[1]) ?? 0,
          numericValue(row[2] ?? row[1]) ?? 0,
          String(row[0] ?? ""),
        ]),
      }],
    };
  }

  if (instance.type === "builtin.funnel") {
    return {
      ...base,
      tooltip: { ...base.tooltip, trigger: "item" },
      series: [{
        type: "funnel" as const,
        left: "12%",
        top: titleOf(base) ? 58 : 20,
        bottom: 18,
        width: "76%",
        min: 0,
        max: Math.max(...result.rows.map((row) => numericValue(row[1]) ?? 0), 1),
        minSize: "18%",
        maxSize: "90%",
        sort: "descending" as const,
        gap: 3,
        label: { color: base.textStyle.color, position: "inside" as const, formatter: "{b}  {c}" },
        data: result.rows.map((row) => ({ name: String(row[0] ?? ""), value: numericValue(row[1]) ?? 0 })),
      }],
    };
  }

  const horizontal =
    instance.type === "builtin.bar" &&
    stringProp(instance.props, "orientation") === "horizontal";
  const valueAxis = {
    type: "value" as const,
    axisLine: base.axisLine,
    splitLine: base.splitLine,
    axisLabel: base.axisLabel,
  };
  const categoryAxis = {
    type: "category" as const,
    data: labels,
    axisLine: base.axisLine,
    axisLabel: base.axisLabel,
    splitLine: { show: false },
  };
  const isArea = visualType === "area";
  const interactive = (instance.interactions?.length ?? 0) > 0;
  const series = measures.map((column, measureIndex) => ({
    type: instance.type === "builtin.bar" ? ("bar" as const) : ("line" as const),
    name: column.name,
    data: measureData(result, measureIndex + 1),
    smooth: instance.type === "builtin.line",
    showSymbol: instance.type === "builtin.line" && interactive,
    ...(instance.type === "builtin.line" && interactive
      ? { symbolSize: 14, itemStyle: { opacity: 0 } }
      : {}),
    lineStyle: { width: 2 },
    ...(instance.type === "builtin.bar"
      ? { barMaxWidth: 28, itemStyle: { borderRadius: [4, 4, 0, 0] } }
      : {}),
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

function titleOf(option: ReturnType<typeof baseOption>): string {
  return typeof option.title?.text === "string" ? option.title.text : "";
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
