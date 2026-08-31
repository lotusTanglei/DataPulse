import type { JsonValue, QueryColumn, QueryResult } from "../query/types";
import type { ComponentInstance, DataBinding, DemoDataKind } from "./types";

export interface MockDataConfig {
  schema_version?: 1;
  preset?: string;
  seed?: number;
  row_count?: number;
  series_count?: number;
  category_count?: number;
  value_min?: number;
  value_max?: number;
  trend?: "up" | "down" | "flat";
}

function record(value: JsonValue | undefined): Record<string, JsonValue> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value
    : {};
}

function numberValue(value: JsonValue | undefined, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function mockConfig(binding: DataBinding): MockDataConfig {
  const value = record(binding.mock_data);
  const valueMin = numberValue(value.value_min, 0);
  const valueMax = Math.max(valueMin, numberValue(value.value_max, 100));
  const trend = value.trend === "up" || value.trend === "down" || value.trend === "flat"
    ? value.trend
    : "up";
  return {
    preset: typeof value.preset === "string" ? value.preset : undefined,
    seed: Math.trunc(numberValue(value.seed, 42)),
    row_count: Math.min(100, Math.max(1, Math.trunc(numberValue(value.row_count, 8)))),
    series_count: Math.min(3, Math.max(1, Math.trunc(numberValue(value.series_count, 2)))),
    category_count: Math.min(10, Math.max(3, Math.trunc(numberValue(value.category_count, 6)))),
    value_min: valueMin,
    value_max: valueMax,
    trend,
  };
}

function hashSeed(seed: number, index: number): number {
  let value = (seed | 0) ^ Math.imul(index + 1, 0x45d9f3b);
  value = Math.imul(value ^ (value >>> 16), 0x45d9f3b);
  value = Math.imul(value ^ (value >>> 16), 0x45d9f3b);
  return (value ^ (value >>> 16)) >>> 0;
}

function variation(seed: number, index: number, spread = 1): number {
  return ((hashSeed(seed, index) % 1000) / 1000 - 0.5) * spread;
}

function column(name: string, dataType: string): QueryColumn {
  return { name, data_type: dataType };
}

function result(
  componentId: string,
  columns: QueryColumn[],
  rows: JsonValue[][],
): QueryResult {
  return {
    request_id: `mock:${componentId}`,
    columns,
    rows,
    row_count: rows.length,
    truncated: false,
    duration_ms: 0,
  };
}

const regions = ["区域-01", "区域-02", "区域-03", "区域-04", "区域-05", "区域-06"];
const alertTitles = ["指标波动", "数据延迟", "规则触发", "阈值接近", "状态变化"];
const alertLevels = ["high", "medium", "low"];

function scaledValue(config: MockDataConfig, seed: number, index: number): number {
  const min = config.value_min ?? 0;
  const max = Math.max(min, config.value_max ?? 100);
  const middle = min + (max - min) * 0.68;
  return Math.round(Math.min(max, Math.max(min, middle + variation(seed, index, (max - min) * 0.18))));
}

function singleResult(componentId: string, config: MockDataConfig): QueryResult {
  return result(componentId, [column("value", "number")], [[scaledValue(config, config.seed ?? 42, 0)]]);
}

function seriesResult(componentId: string, config: MockDataConfig): QueryResult {
  const seed = config.seed ?? 42;
  const rowCount = config.row_count ?? 8;
  const seriesCount = config.series_count ?? 2;
  const min = config.value_min ?? 0;
  const max = Math.max(min, config.value_max ?? 100);
  const span = max - min;
  const direction = config.trend === "down" ? -1 : config.trend === "flat" ? 0 : 1;
  const rows = Array.from({ length: rowCount }, (_, index) => {
    const progress = rowCount <= 1 ? 0 : index / (rowCount - 1);
    const values: JsonValue[] = [
      `08/${String(20 + index).padStart(2, "0")}`,
    ];
    for (let seriesIndex = 0; seriesIndex < seriesCount; seriesIndex += 1) {
      const seriesBase = min + span * (0.45 + seriesIndex * 0.08);
      const trendOffset = direction * span * 0.28 * progress;
      values.push(Math.round(Math.min(max, Math.max(min, seriesBase + trendOffset + variation(seed + seriesIndex * 19, index, span * 0.16)))));
    }
    return values;
  });
  const columns = [column("日期", "string")];
  for (let seriesIndex = 0; seriesIndex < seriesCount; seriesIndex += 1) {
    columns.push(column(`序列-${String(seriesIndex + 1).padStart(2, "0")}`, "number"));
  }
  return result(
    componentId,
    columns,
    rows,
  );
}

function tableResult(componentId: string, seed: number, rowCount: number): QueryResult {
  const rows = Array.from({ length: rowCount }, (_, index) => [
      `ID-${String(260831 + index).slice(-6)}`,
      `对象-${String((index % 4) + 1).padStart(2, "0")}`,
      ["进行中", "待确认", "已完成", "异常"][index % 4],
    Math.round(60 + variation(seed, index, 28)),
    `08/${String(20 + (index % 10)).padStart(2, "0")} ${String(8 + (index % 10)).padStart(2, "0")}:30`,
  ]);
  return result(
    componentId,
    [
      column("编号", "string"),
      column("对象", "string"),
      column("状态", "string"),
      column("完成率", "number"),
      column("更新时间", "datetime"),
    ],
    rows,
  );
}

function statusMatrixResult(componentId: string, seed: number, rowCount: number): QueryResult {
  const states = ["正常", "关注", "异常", "正常"];
  return result(
    componentId,
    [column("对象", "string"), column("状态", "string"), column("更新时间", "datetime")],
    Array.from({ length: rowCount }, (_, index) => [
      `对象-${String((index % 6) + 1).padStart(2, "0")}`,
      states[(index + Math.abs(seed)) % states.length]!,
      `08/${String(20 + (index % 10)).padStart(2, "0")} ${String(8 + (index % 10)).padStart(2, "0")}:30`,
    ]),
  );
}

function timelineResult(componentId: string, seed: number, rowCount: number): QueryResult {
  const events = ["状态更新", "数据同步", "规则触发", "配置变更", "任务完成"];
  return result(
    componentId,
    [column("时间", "datetime"), column("事件", "string"), column("详情", "string")],
    Array.from({ length: rowCount }, (_, index) => [
      `08/${String(20 + (index % 10)).padStart(2, "0")} ${String(8 + (index % 10)).padStart(2, "0")}:30`,
      events[(index + Math.abs(seed)) % events.length]!,
      `对象-${String((index % 4) + 1).padStart(2, "0")} 已更新`,
    ]),
  );
}

function rankingResult(componentId: string, seed: number, rowCount: number): QueryResult {
  return result(
    componentId,
    [column("分类", "string"), column("数值", "number"), column("变化", "number")],
    regions.slice(0, Math.min(regions.length, rowCount)).map((name, index) => [
      name,
      Math.round(980 - index * 92 + variation(seed, index, 45)),
      Math.round(18 - index * 4 + variation(seed, index + 9, 8)),
    ]),
  );
}

function alertResult(componentId: string, seed: number, rowCount: number): QueryResult {
  return result(
    componentId,
    [column("level", "string"), column("title", "string"), column("detail", "string"), column("time", "datetime"), column("status", "string")],
    Array.from({ length: rowCount }, (_, index) => [
      alertLevels[index % alertLevels.length]!,
      alertTitles[index % alertTitles.length]!,
      ["请安排现场确认", "责任人已接单", "建议在本班次处理"][index % 3]!,
      `2026-08-31 ${String(8 + index).padStart(2, "0")}:${String(12 + index * 3).padStart(2, "0")}`,
      index % 3 === 0 ? "待处理" : "跟进中",
    ]),
  );
}

function radarResult(componentId: string, seed: number): QueryResult {
  const axes = ["维度-01", "维度-02", "维度-03", "维度-04", "维度-05"];
  return result(
    componentId,
    [column("维度", "string"), column("当前", "number"), column("目标", "number")],
    axes.map((axis, index) => [axis, Math.round(65 + variation(seed, index, 20)), Math.round(78 + variation(seed + 3, index, 10))]),
  );
}

function geoResult(componentId: string, seed: number): QueryResult {
  return result(
    componentId,
    [column("code", "string"), column("name", "string"), column("value", "number")],
    regions.map((name, index) => [`region-${index + 1}`, name, Math.round(120 + variation(seed, index, 60))]),
  );
}

export function demoDataKindFor(type: string): DemoDataKind {
  if (["builtin.kpi", "builtin.progress", "builtin.digital_number", "builtin.gauge"].includes(type)) return "single";
  if (["builtin.line", "builtin.bar", "builtin.pie", "builtin.heatmap", "builtin.scatter", "builtin.funnel"].includes(type)) return "series";
  if (type === "builtin.radar") return "radar";
  if (type === "builtin.ranking") return "ranking";
  if (["builtin.alert_list", "builtin.timeline", "builtin.status_matrix", "builtin.table"].includes(type)) return "table";
  if (type === "builtin.geo_map") return "geo";
  return "none";
}

export function createMockBinding(
  type: string,
  seed = 42,
  overrides: Partial<MockDataConfig> = {},
): DataBinding {
  const kind = demoDataKindFor(type);
  const mockData: Record<string, JsonValue> = {
    schema_version: 1,
    preset: kind,
    seed,
    row_count: kind === "series" ? 10 : kind === "table" || kind === "alerts" ? 8 : 6,
    value_min: 0,
    value_max: 100,
    trend: "up",
  };
  if (kind === "series") mockData.series_count = 2;
  if (kind === "ranking") mockData.category_count = 6;
  for (const [key, value] of Object.entries(overrides)) {
    if (value !== undefined) mockData[key] = value as JsonValue;
  }
  return {
    source: "mock",
    mock_data: mockData,
  };
}

export function resolveLocalResult(
  component: Pick<ComponentInstance, "id" | "type">,
  binding: DataBinding,
): QueryResult | null {
  const source = binding.source;
  const staticValue = record(binding.static_data);
  if (source === "static" || Object.keys(staticValue).length > 0) {
    const columnsValue = staticValue.columns;
    const rowsValue = staticValue.rows;
    if (!Array.isArray(columnsValue) || !Array.isArray(rowsValue)) {
      throw new Error("静态数据格式无效。");
    }
    const columns = columnsValue.map((item) => {
      const value = record(item);
      if (typeof value.name !== "string" || typeof value.data_type !== "string") {
        throw new Error("静态数据字段无效。");
      }
      return column(value.name, value.data_type);
    });
    const rows = rowsValue.map((row) => {
      if (!Array.isArray(row) || row.length !== columns.length) {
        throw new Error("静态数据行与字段数量不一致。");
      }
      return row;
    });
    if (columns.length === 0 || columns.length > 20 || rows.length > 500) {
      throw new Error("静态数据超出允许范围。");
    }
    return result(component.id, columns, rows);
  }
  const mockValue = record(binding.mock_data);
  if (source !== "mock" && Object.keys(mockValue).length === 0) return null;
  const config = mockConfig(binding);
  const kind = demoDataKindFor(component.type);
  if (kind === "single") return singleResult(component.id, config);
  if (kind === "series") return seriesResult(component.id, config);
  if (kind === "ranking") return rankingResult(component.id, config.seed ?? 42, Math.min(config.category_count ?? 6, config.row_count ?? 8));
  if (kind === "radar") return radarResult(component.id, config.seed ?? 42);
  if (kind === "geo") return geoResult(component.id, config.seed ?? 42);
  if (kind === "table") {
    if (component.type === "builtin.alert_list") return alertResult(component.id, config.seed ?? 42, config.row_count ?? 8);
    if (component.type === "builtin.status_matrix") return statusMatrixResult(component.id, config.seed ?? 42, config.row_count ?? 8);
    if (component.type === "builtin.timeline") return timelineResult(component.id, config.seed ?? 42, config.row_count ?? 8);
    return tableResult(component.id, config.seed ?? 42, config.row_count ?? 8);
  }
  throw new Error("该组件暂不支持演示数据。");
}
