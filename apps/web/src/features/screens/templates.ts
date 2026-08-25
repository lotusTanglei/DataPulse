import type { DashboardDocument } from "../../contracts";

type TemplateComponent = NonNullable<DashboardDocument["components"]>[number];

export interface ScreenTemplate {
  id: string;
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
  background_color: "#101d31",
  border_color: "#243653",
  border_width: 1,
  border_radius: 10,
};

function component(
  id: string,
  type: string,
  frame: TemplateComponent["frame"],
  props: Record<string, unknown>,
  style: Record<string, unknown> = surfaceStyle,
): TemplateComponent {
  return {
    id,
    type,
    frame,
    state: { locked: false, hidden: false },
    props,
    style,
    data_binding: {},
    interactions: [],
  } as TemplateComponent;
}

function title(text: string, subtitle: string): TemplateComponent[] {
  return [
    component(
      "title",
      "builtin.text",
      { x: 40, y: 30, width: 1500, height: 56, z_index: 10 },
      { text, align: "left", font_size: 34, font_weight: 700 },
      { text_color: "#f8fafc" },
    ),
    component(
      "subtitle",
      "builtin.text",
      { x: 42, y: 90, width: 1200, height: 28, z_index: 10 },
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
): TemplateComponent {
  return component(
    id,
    "builtin.kpi",
    { x, y: 150, width: 260, height: 150, z_index: 2 },
    { label, precision: 0, empty_text: "绑定数据后显示" },
    { ...surfaceStyle, border_color: accent },
  );
}

function chart(
  id: string,
  type:
    | "builtin.line"
    | "builtin.bar"
    | "builtin.pie"
    | "builtin.table"
    | "builtin.geo_map",
  frame: TemplateComponent["frame"],
): TemplateComponent {
  return component(id, type, frame, {
    ...(type === "builtin.bar" ? { orientation: "vertical" } : {}),
    ...(type === "builtin.pie" ? { variant: "pie" } : {}),
    ...(type === "builtin.table" ? { max_rows: 100 } : {}),
    ...(type === "builtin.geo_map"
      ? {
          asset_id: "",
          region_code_property: "code",
          region_name_property: "name",
        }
      : {}),
    empty_text: "绑定数据后显示",
  });
}

function progress(
  id: string,
  x: number,
  label: string,
): TemplateComponent {
  return component(
    id,
    "builtin.progress",
    { x, y: 150, width: 260, height: 150, z_index: 2 },
    { label, precision: 1, empty_text: "绑定数据后显示" },
  );
}

function documentOf(components: TemplateComponent[]): DashboardDocument {
  return {
    schema_version: 1,
    canvas: darkCanvas,
    theme: { id: "datapulse-dark", tokens: { accent: "#4ade80" } },
    refresh: { mode: "disabled", interval_seconds: null },
    parameters: [],
    components,
  };
}

const templates: ScreenTemplate[] = [
  {
    id: "business-overview",
    name: "经营分析",
    category: "经营分析",
    description: "指标总览、趋势和结构分析，适合作为通用经营驾驶舱起点。",
    createDocument: () =>
      documentOf([
        ...title("经营分析总览", "从核心指标到趋势变化，快速搭建经营驾驶舱"),
        kpi("revenue", 40, "营业收入", "#4ade80"),
        kpi("orders", 330, "订单数量", "#60a5fa"),
        kpi("customers", 620, "活跃客户", "#fbbf24"),
        kpi("growth", 910, "同比增长", "#f472b6"),
        chart("trend", "builtin.line", {
          x: 40,
          y: 340,
          width: 920,
          height: 330,
          z_index: 1,
        }),
        chart("structure", "builtin.bar", {
          x: 990,
          y: 340,
          width: 890,
          height: 330,
          z_index: 1,
        }),
        chart("details", "builtin.table", {
          x: 40,
          y: 710,
          width: 1840,
          height: 320,
          z_index: 1,
        }),
      ]),
  },
  {
    id: "operations-monitoring",
    name: "运营监控",
    category: "运营监控",
    description: "实时指标、达成进度和异常趋势，适合运营值守场景。",
    createDocument: () =>
      documentOf([
        ...title("运营监控中心", "实时观察业务运行状态与关键目标达成情况"),
        kpi("online", 40, "在线用户", "#22d3ee"),
        kpi("requests", 330, "请求量", "#60a5fa"),
        kpi("success", 620, "成功率", "#4ade80"),
        progress("target", 910, "目标达成"),
        progress("health", 1200, "系统健康度"),
        chart("traffic", "builtin.line", {
          x: 40,
          y: 340,
          width: 1120,
          height: 360,
          z_index: 1,
        }),
        chart("alerts", "builtin.bar", {
          x: 1190,
          y: 340,
          width: 690,
          height: 360,
          z_index: 1,
        }),
        chart("events", "builtin.table", {
          x: 40,
          y: 740,
          width: 1840,
          height: 290,
          z_index: 1,
        }),
      ]),
  },
  {
    id: "sales-analysis",
    name: "销售分析",
    category: "销售分析",
    description: "销售额、区域结构和商品排行，适合销售复盘与目标管理。",
    createDocument: () =>
      documentOf([
        ...title("销售分析驾驶舱", "从目标完成、区域结构和商品表现定位增长机会"),
        kpi("sales", 40, "销售额", "#4ade80"),
        kpi("profit", 330, "毛利额", "#fbbf24"),
        kpi("conversion", 620, "转化率", "#60a5fa"),
        kpi("returns", 910, "退货率", "#f87171"),
        chart("regional", "builtin.bar", {
          x: 40,
          y: 340,
          width: 860,
          height: 360,
          z_index: 1,
        }),
        chart("mix", "builtin.pie", {
          x: 930,
          y: 340,
          width: 450,
          height: 360,
          z_index: 1,
        }),
        chart("ranking", "builtin.table", {
          x: 1410,
          y: 340,
          width: 470,
          height: 360,
          z_index: 1,
        }),
        chart("monthly", "builtin.line", {
          x: 40,
          y: 740,
          width: 1840,
          height: 290,
          z_index: 1,
        }),
      ]),
  },
  {
    id: "device-monitoring",
    name: "设备监控",
    category: "设备监控",
    description: "设备在线状态、告警趋势和区域分布，适合生产与物联网场景。",
    createDocument: () =>
      documentOf([
        ...title("设备运行监控", "集中查看设备在线、告警和区域运行状态"),
        kpi("devices", 40, "设备总数", "#60a5fa"),
        kpi("online", 330, "在线设备", "#4ade80"),
        kpi("alerts", 620, "待处理告警", "#f87171"),
        progress("availability", 910, "在线率"),
        progress("health", 1200, "健康度"),
        chart("device-trend", "builtin.line", {
          x: 40,
          y: 340,
          width: 930,
          height: 360,
          z_index: 1,
        }),
        chart("device-map", "builtin.geo_map", {
          x: 1000,
          y: 340,
          width: 880,
          height: 360,
          z_index: 1,
        }),
        chart("device-events", "builtin.table", {
          x: 40,
          y: 740,
          width: 1840,
          height: 290,
          z_index: 1,
        }),
      ]),
  },
  {
    id: "regional-operations",
    name: "区域运营",
    category: "区域运营",
    description: "区域指标、地图分布和排行组合，适合门店与区域经营管理。",
    createDocument: () =>
      documentOf([
        ...title("区域运营地图", "比较各区域经营表现，快速发现重点市场和异常区域"),
        kpi("active-regions", 40, "活跃区域", "#60a5fa"),
        kpi("top-region", 330, "领先区域", "#4ade80"),
        kpi("regional-sales", 620, "区域销售额", "#fbbf24"),
        kpi("regional-growth", 910, "区域增长", "#f472b6"),
        chart("map", "builtin.geo_map", {
          x: 40,
          y: 340,
          width: 1050,
          height: 690,
          z_index: 1,
        }),
        chart("regions", "builtin.bar", {
          x: 1120,
          y: 340,
          width: 760,
          height: 330,
          z_index: 1,
        }),
        chart("region-details", "builtin.table", {
          x: 1120,
          y: 700,
          width: 760,
          height: 330,
          z_index: 1,
        }),
      ]),
  },
];

export const screenTemplates: readonly ScreenTemplate[] = templates;

export function createTemplateDocument(templateId: string): DashboardDocument {
  const template = templates.find((item) => item.id === templateId);
  if (!template) {
    throw new Error(`Unknown screen template: ${templateId}`);
  }
  return structuredClone(template.createDocument());
}
