import type { DashboardDocument, DashboardPlan } from "../../contracts";
import type { Dataset } from "../datasets/types";
import { createMockBinding } from "../runtime/mockData";

type TemplateComponent = NonNullable<DashboardDocument["components"]>[number];

export interface ScreenTemplate {
  id: string;
  planTemplate: NonNullable<DashboardPlan["layout"]>["template"];
  name: string;
  description: string;
  category: string;
  createDocument: () => DashboardDocument;
}

const darkCanvas = {
  width: 1920,
  height: 1080,
  background: { color: "#08111f" },
};

const surfaceStyle = {
  background_color: "var(--screen-panel-background, #0b1b2b)",
  border_color: "var(--screen-panel-border, #1b4160)",
  border_width: 1,
  border_radius: 8,
};

function component(
  id: string,
  type: string,
  frame: TemplateComponent["frame"],
  props: Record<string, unknown>,
  style: Record<string, unknown> = surfaceStyle,
  seed = 42,
): TemplateComponent {
  const hasData = ![
    "builtin.text",
    "builtin.image",
    "builtin.panel",
    "builtin.divider",
  ].includes(type);
  return {
    id,
    type,
    frame,
    state: { locked: false, hidden: false },
    props,
    style,
    data_binding: hasData ? createMockBinding(type, seed) : {},
    interactions: [],
  } as TemplateComponent;
}

function title(text: string, subtitle: string): TemplateComponent[] {
  return [
    component(
      "title",
      "builtin.text",
      { x: 40, y: 28, width: 1500, height: 54, z_index: 10 },
      { text, align: "left", font_size: 34, font_weight: 700 },
      { text_color: "#f8fafc" },
    ),
    component(
      "subtitle",
      "builtin.text",
      { x: 42, y: 88, width: 1400, height: 28, z_index: 10 },
      { text: subtitle, align: "left", font_size: 15, font_weight: 500 },
      { text_color: "#8da2bf" },
    ),
  ];
}

function kpi(
  id: string,
  x: number,
  label: string,
  accent: string,
  seed: number,
): TemplateComponent {
  return component(
    id,
    "builtin.kpi",
    { x, y: 146, width: 260, height: 150, z_index: 2 },
    { label, precision: 0, empty_text: "暂无数据" },
    { ...surfaceStyle, border_color: accent },
    seed,
  );
}

function digital(
  id: string,
  x: number,
  label: string,
  unit: string,
  seed: number,
): TemplateComponent {
  return component(
    id,
    "builtin.digital_number",
    { x, y: 146, width: 300, height: 150, z_index: 2 },
    { label, unit, precision: 0 },
    { ...surfaceStyle, border_color: "var(--screen-accent, #26d9c1)" },
    seed,
  );
}

function chart(
  id: string,
  type:
    | "builtin.line"
    | "builtin.bar"
    | "builtin.pie"
    | "builtin.radar"
    | "builtin.heatmap"
    | "builtin.scatter"
    | "builtin.funnel"
    | "builtin.table"
    | "builtin.ranking"
    | "builtin.alert_list"
    | "builtin.status_matrix"
    | "builtin.timeline",
  frame: TemplateComponent["frame"],
  titleText: string,
  seed: number,
): TemplateComponent {
  return component(
    id,
    type,
    frame,
    {
      title: titleText,
      ...(type === "builtin.bar" ? { orientation: "vertical" } : {}),
      ...(type === "builtin.pie" ? { variant: "donut" } : {}),
      ...(type === "builtin.table" ? { max_rows: 8 } : {}),
      empty_text: "暂无数据",
    },
    surfaceStyle,
    seed,
  );
}

function progress(
  id: string,
  x: number,
  label: string,
  seed: number,
): TemplateComponent {
  return component(
    id,
    "builtin.progress",
    { x, y: 146, width: 260, height: 150, z_index: 2 },
    { label, precision: 1, empty_text: "暂无数据" },
    surfaceStyle,
    seed,
  );
}

function documentOf(components: TemplateComponent[]): DashboardDocument {
  return {
    schema_version: 1,
    canvas: darkCanvas,
    theme: {
      id: "datapulse-dark",
      tokens: { screen_accent: "#26d9c1" },
    },
    refresh: { mode: "disabled", interval_seconds: null },
    parameters: [],
    components,
  };
}

const templates: ScreenTemplate[] = [
  {
    id: "overview-grid",
    planTemplate: "executive-overview",
    name: "总览网格",
    category: "总览布局",
    description: "标题、核心指标、趋势、排行和明细表的通用起始布局。",
    createDocument: () =>
      documentOf([
        ...title("数据总览", "用统一的视觉层级组织核心指标与明细信息"),
        kpi("kpi-a", 40, "核心指标", "#26d9c1", 42),
        kpi("kpi-b", 330, "完成数量", "#3b8df4", 43),
        kpi("kpi-c", 620, "平均效率", "#f3b638", 44),
        kpi("kpi-d", 910, "异常数量", "#f16d75", 45),
        chart("trend", "builtin.line", { x: 40, y: 332, width: 920, height: 360, z_index: 1 }, "趋势变化", 50),
        chart("ranking", "builtin.ranking", { x: 990, y: 332, width: 890, height: 360, z_index: 1 }, "分类排行", 51),
        chart("details", "builtin.table", { x: 40, y: 732, width: 1840, height: 298, z_index: 1 }, "明细数据", 52),
      ]),
  },
  {
    id: "trend-focus",
    planTemplate: "trend-focus",
    name: "趋势聚焦",
    category: "趋势分析",
    description: "大数字、进度、折线与雷达组合，适合观察变化和目标达成。",
    createDocument: () =>
      documentOf([
        ...title("趋势聚焦", "通过趋势、目标和多维指标建立视觉焦点"),
        digital("value", 40, "当前值", "单位", 60),
        digital("target", 360, "目标值", "单位", 61),
        progress("progress-a", 680, "目标达成", 62),
        progress("progress-b", 970, "状态健康", 63),
        chart("trend", "builtin.line", { x: 40, y: 332, width: 1120, height: 360, z_index: 1 }, "多序列趋势", 64),
        chart("radar", "builtin.radar", { x: 1190, y: 332, width: 690, height: 360, z_index: 1 }, "多维对比", 65),
        chart("events", "builtin.timeline", { x: 40, y: 732, width: 900, height: 298, z_index: 1 }, "最近事件", 66),
        chart("alerts", "builtin.alert_list", { x: 970, y: 732, width: 910, height: 298, z_index: 1 }, "状态提醒", 67),
      ]),
  },
  {
    id: "comparison-board",
    planTemplate: "comparison-board",
    name: "对比分析",
    category: "对比分析",
    description: "柱状、环图、漏斗和表格组合，适合比较结构、阶段和明细。",
    createDocument: () =>
      documentOf([
        ...title("对比分析", "在同一画布中同时呈现分类、结构和阶段转化"),
        kpi("metric-a", 40, "总量", "#60a5fa", 70),
        kpi("metric-b", 330, "平均值", "#26d9c1", 71),
        kpi("metric-c", 620, "达成率", "#f3b638", 72),
        kpi("metric-d", 910, "变化率", "#a5d85b", 73),
        chart("bar", "builtin.bar", { x: 40, y: 332, width: 780, height: 360, z_index: 1 }, "分类对比", 74),
        chart("mix", "builtin.pie", { x: 850, y: 332, width: 430, height: 360, z_index: 1 }, "结构占比", 75),
        chart("funnel", "builtin.funnel", { x: 1310, y: 332, width: 570, height: 360, z_index: 1 }, "阶段转化", 76),
        chart("details", "builtin.table", { x: 40, y: 732, width: 1840, height: 298, z_index: 1 }, "比较明细", 77),
      ]),
  },
  {
    id: "status-wall",
    planTemplate: "status-wall",
    name: "状态墙",
    category: "状态布局",
    description: "仪表盘、状态矩阵、告警和时间线组合，突出状态与异常层级。",
    createDocument: () =>
      documentOf([
        ...title("状态墙", "用状态、告警和时间顺序保持信息持续可读"),
        digital("online", 40, "在线总量", "项", 80),
        digital("active", 360, "活跃数量", "项", 81),
        progress("availability", 680, "可用率", 82),
        component("gauge", "builtin.gauge", { x: 970, y: 132, width: 260, height: 178, z_index: 2 }, { label: "综合状态", precision: 1 }, surfaceStyle, 83),
        component("matrix", "builtin.status_matrix", { x: 1270, y: 132, width: 610, height: 178, z_index: 2 }, { title: "对象状态" }, surfaceStyle, 84),
        chart("alerts", "builtin.alert_list", { x: 40, y: 342, width: 620, height: 688, z_index: 1 }, "告警列表", 85),
        chart("timeline", "builtin.timeline", { x: 690, y: 342, width: 590, height: 688, z_index: 1 }, "事件时间线", 86),
        chart("status-trend", "builtin.line", { x: 1310, y: 342, width: 570, height: 688, z_index: 1 }, "状态趋势", 87),
      ]),
  },
  {
    id: "analysis-lab",
    planTemplate: "analysis-lab",
    name: "分析工作台",
    category: "分析布局",
    description: "热力、散点、排行和表格组合，适合搭建高密度分析工作台。",
    createDocument: () =>
      documentOf([
        ...title("分析工作台", "把分布、关系、排行与明细放在同一套视觉系统中"),
        kpi("signal-a", 40, "样本数量", "#3b8df4", 90),
        kpi("signal-b", 330, "集中趋势", "#26d9c1", 91),
        kpi("signal-c", 620, "关联强度", "#f3b638", 92),
        kpi("signal-d", 910, "高风险项", "#f16d75", 93),
        chart("heatmap", "builtin.heatmap", { x: 40, y: 332, width: 900, height: 360, z_index: 1 }, "分布热力", 94),
        chart("scatter", "builtin.scatter", { x: 970, y: 332, width: 910, height: 360, z_index: 1 }, "关系分布", 95),
        chart("ranking", "builtin.ranking", { x: 40, y: 732, width: 600, height: 298, z_index: 1 }, "重点排行", 96),
        chart("details", "builtin.table", { x: 670, y: 732, width: 1210, height: 298, z_index: 1 }, "分析明细", 97),
      ]),
  },
];

export const screenTemplates: readonly ScreenTemplate[] = templates;

const businessMeasureTerms = [
  "amount",
  "revenue",
  "sales",
  "value",
  "target",
  "count",
  "total",
  "金额",
  "销售额",
  "数量",
  "收入",
];

const nonMeasureTerms = [
  "month",
  "year",
  "date",
  "time",
  "id",
  "code",
  "月份",
  "年份",
  "日期",
  "编号",
];

function includesAnyTerm(name: string, terms: readonly string[]): boolean {
  const normalized = name.toLocaleLowerCase();
  return terms.some((term) => normalized.includes(term));
}

export function createTemplateDocument(templateId: string): DashboardDocument {
  const template = templates.find((item) => item.id === templateId);
  if (!template) {
    throw new Error(`Unknown screen template: ${templateId}`);
  }
  return structuredClone(template.createDocument());
}

export function createTemplatePlan(
  templateId: string,
  dataset: Dataset,
  title: string,
): DashboardPlan {
  const template = templates.find((item) => item.id === templateId);
  if (!template) {
    throw new Error(`Unknown screen template: ${templateId}`);
  }
  const fields = dataset.definition?.fields ?? [];
  const first = fields[0];
  if (!first) {
    throw new Error("Template planning requires a dataset field.");
  }
  const numericFields = fields.filter((field) =>
    ["integer", "number"].includes(field.data_type),
  );
  const numeric =
    numericFields.find(
      (field) =>
        includesAnyTerm(field.name, businessMeasureTerms) &&
        !includesAnyTerm(field.name, nonMeasureTerms),
    ) ??
    numericFields.find(
      (field) => !includesAnyTerm(field.name, nonMeasureTerms),
    ) ??
    numericFields[0];
  const temporal = fields.find((field) =>
    ["date", "datetime"].includes(field.data_type),
  );
  const category = fields.find((field) =>
    ["boolean", "string"].includes(field.data_type),
  );
  const dimension = category ?? temporal ?? first;
  const trendDimension = temporal ?? dimension;
  const measure = numeric ?? first;
  const totalAggregation = numeric ? "sum" : "count";
  const averageAggregation = numeric ? "avg" : "count";
  const maximumAggregation = numeric ? "max" : "count";
  const plan = {
    schema_version: 1,
    title,
    audience: "业务负责人",
    narrative: template.description,
    dataset_ids: [dataset.id],
    layout: {
      template: template.planTemplate,
      grid_columns: 24,
      density: "comfortable",
      theme: "dark",
    },
    regions: [
      { id: "summary", kind: "summary", title: "核心指标", order: 0 },
      { id: "main", kind: "main", title: "主要分析", order: 1 },
      { id: "secondary", kind: "secondary", title: "补充分析", order: 2 },
    ],
    widgets: [
      {
        id: "template-total",
        title: measure.name,
        intent: `汇总 ${measure.name}`,
        region_id: "summary",
        dataset_id: dataset.id,
        chart_type: "kpi",
        dimensions: [],
        measures: [{ field: measure.name, aggregation: totalAggregation }],
        filters: [],
        sort: [],
        limit: 1000,
      },
      {
        id: "template-progress",
        title: `${measure.name} 进度`,
        intent: `展示 ${measure.name} 进度`,
        region_id: "summary",
        dataset_id: dataset.id,
        chart_type: "progress",
        dimensions: [],
        measures: [{ field: measure.name, aggregation: averageAggregation }],
        filters: [],
        sort: [],
        limit: 1000,
      },
      {
        id: "template-gauge",
        title: `${measure.name} 状态`,
        intent: `展示 ${measure.name} 状态`,
        region_id: "summary",
        dataset_id: dataset.id,
        chart_type: "gauge",
        dimensions: [],
        measures: [{ field: measure.name, aggregation: maximumAggregation }],
        filters: [],
        sort: [],
        limit: 1000,
      },
      {
        id: "template-bar",
        title: `${dimension.name} · ${measure.name}`,
        intent: `按 ${dimension.name} 分析 ${measure.name}`,
        region_id: "main",
        dataset_id: dataset.id,
        chart_type: "bar",
        dimensions: [dimension.name],
        measures: [{ field: measure.name, aggregation: totalAggregation }],
        filters: [],
        sort: [],
        limit: 1000,
      },
      {
        id: "template-share",
        title: `${dimension.name} 占比`,
        intent: `展示 ${dimension.name} 占比`,
        region_id: "main",
        dataset_id: dataset.id,
        chart_type: category ? "pie" : "table",
        dimensions: [dimension.name],
        measures: [{ field: measure.name, aggregation: totalAggregation }],
        filters: [],
        sort: [],
        limit: 1000,
      },
      {
        id: "template-radar",
        title: `${dimension.name} 对比`,
        intent: `对比 ${dimension.name}`,
        region_id: "main",
        dataset_id: dataset.id,
        chart_type: "bar",
        dimensions: [dimension.name],
        measures: [{ field: measure.name, aggregation: averageAggregation }],
        filters: [],
        sort: [],
        limit: 1000,
      },
      {
        id: "template-trend",
        title: `${trendDimension.name} 趋势`,
        intent: `展示 ${trendDimension.name} 趋势`,
        region_id: "secondary",
        dataset_id: dataset.id,
        chart_type: temporal ? "line" : "bar",
        dimensions: [trendDimension.name],
        measures: [{ field: measure.name, aggregation: totalAggregation }],
        filters: [],
        sort: [],
        limit: 1000,
      },
      {
        id: "template-detail",
        title: "数据明细",
        intent: "展示数据明细",
        region_id: "secondary",
        dataset_id: dataset.id,
        chart_type: "table",
        dimensions: [dimension.name],
        measures: [{ field: measure.name, aggregation: "count" }],
        filters: [],
        sort: [],
        limit: 1000,
      },
    ],
    parameters: [],
  };
  return plan as DashboardPlan;
}
