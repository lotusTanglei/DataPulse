import type { EChartsOption } from "echarts";

import type { QueryResult } from "../../query/types";
import type { ComponentInstance } from "../types";
import { numericValue, stringProp } from "./format";

function colors(theme: Record<string, unknown>): string[] {
  const value = theme.chart_colors;
  return Array.isArray(value) && value.every((item) => typeof item === "string")
    ? value
    : ["#26d9c1", "#4da3ff", "#f3b638", "#f16d75", "#9d7cff"];
}

function textColor(theme: Record<string, unknown>): string {
  return typeof theme.text_primary === "string" ? theme.text_primary : "#eaf4ff";
}

function base(
  instance: ComponentInstance,
  theme: Record<string, unknown>,
): EChartsOption {
  const title = stringProp(instance.props, "title");
  return {
    animation: instance.props?.animation !== false,
    color: colors(theme),
    title: title
      ? { text: title, left: 14, top: 12, textStyle: { color: textColor(theme), fontSize: 14 } }
      : undefined,
    tooltip: { trigger: "item", confine: true },
    textStyle: { color: textColor(theme) },
  };
}

function graphOption(
  instance: ComponentInstance,
  result: QueryResult,
  theme: Record<string, unknown>,
): EChartsOption {
  const nodes = new Map<string, number>();
  const links = result.rows.flatMap((row) => {
    const source = String(row[0] ?? "").trim();
    const target = String(row[1] ?? "").trim();
    if (!source || !target) return [];
    const value = numericValue(row[2]) ?? 1;
    nodes.set(source, (nodes.get(source) ?? 0) + value);
    nodes.set(target, (nodes.get(target) ?? 0) + value);
    return [{ source, target, value }];
  });
  return {
    ...base(instance, theme),
    series: [
      {
        type: "graph",
        layout: instance.type === "builtin.org_chart" ? "circular" : "force",
        roam: true,
        draggable: true,
        label: { show: true, color: textColor(theme), fontSize: 10 },
        edgeSymbol: ["none", "arrow"],
        edgeSymbolSize: 7,
        force: { repulsion: 170, edgeLength: [45, 120] },
        lineStyle: { color: "source", curveness: 0.12, opacity: 0.65 },
        data: [...nodes].map(([name, value]) => ({
          name,
          value,
          symbolSize: Math.min(48, 16 + Math.sqrt(value) * 3),
        })),
        links,
      },
    ],
  } as EChartsOption;
}

function sankeyOption(
  instance: ComponentInstance,
  result: QueryResult,
  theme: Record<string, unknown>,
): EChartsOption {
  const names = new Set<string>();
  const links = result.rows.flatMap((row) => {
    const source = String(row[0] ?? "").trim();
    const target = String(row[1] ?? "").trim();
    if (!source || !target || source === target) return [];
    names.add(source);
    names.add(target);
    return [{ source, target, value: Math.max(0, numericValue(row[2]) ?? 1) }];
  });
  return {
    ...base(instance, theme),
    series: [
      {
        type: "sankey",
        left: 24,
        right: 24,
        top: stringProp(instance.props, "title") ? 56 : 20,
        bottom: 20,
        nodeWidth: 14,
        nodeGap: 12,
        emphasis: { focus: "adjacency" },
        label: { color: textColor(theme), fontSize: 10 },
        lineStyle: { color: "gradient", curveness: 0.5, opacity: 0.55 },
        data: [...names].map((name) => ({ name })),
        links,
      },
    ],
  } as EChartsOption;
}

function calendarOption(
  instance: ComponentInstance,
  result: QueryResult,
  theme: Record<string, unknown>,
): EChartsOption {
  const data: Array<[string, number]> = result.rows.flatMap((row) => {
    const date = String(row[0] ?? "").slice(0, 10);
    const value = numericValue(row[1]);
    return /^\d{4}-\d{2}-\d{2}$/.test(date) && value !== null
      ? [[date, value] as [string, number]]
      : [];
  });
  const year = data[0]?.[0].slice(0, 4) ?? String(new Date().getUTCFullYear());
  return {
    ...base(instance, theme),
    visualMap: {
      min: Math.min(...data.map((item) => item[1]), 0),
      max: Math.max(...data.map((item) => item[1]), 1),
      orient: "horizontal",
      left: "center",
      bottom: 8,
      textStyle: { color: textColor(theme) },
    },
    calendar: {
      range: year,
      top: stringProp(instance.props, "title") ? 64 : 34,
      left: 42,
      right: 24,
      bottom: 54,
      cellSize: ["auto", 16],
      itemStyle: { color: "#102b3e", borderWidth: 2, borderColor: "#071522" },
      splitLine: { lineStyle: { color: "#31506a", width: 0.5 } },
      dayLabel: { color: textColor(theme) },
      monthLabel: { color: textColor(theme) },
      yearLabel: { show: false },
    },
    series: [{ type: "heatmap", coordinateSystem: "calendar", data }],
  } as EChartsOption;
}

function polarOption(
  instance: ComponentInstance,
  result: QueryResult,
  theme: Record<string, unknown>,
): EChartsOption {
  return {
    ...base(instance, theme),
    angleAxis: {
      type: "category",
      data: result.rows.map((row) => String(row[0] ?? "")),
      axisLabel: { color: textColor(theme) },
    },
    radiusAxis: { axisLabel: { color: textColor(theme) } },
    polar: { radius: [24, "68%"] },
    series: [
      {
        type: "bar",
        coordinateSystem: "polar",
        roundCap: true,
        barWidth: 14,
        data: result.rows.map((row) => numericValue(row[1]) ?? 0),
      },
    ],
  } as EChartsOption;
}

export function buildAdvancedChartOption(
  instance: ComponentInstance,
  result: QueryResult,
  theme: Record<string, unknown>,
): EChartsOption {
  if (instance.type === "builtin.sankey") return sankeyOption(instance, result, theme);
  if (instance.type === "builtin.calendar_heatmap") {
    return calendarOption(instance, result, theme);
  }
  if (instance.type === "builtin.polar_bar") return polarOption(instance, result, theme);
  return graphOption(instance, result, theme);
}
