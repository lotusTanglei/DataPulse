import type { JsonValue } from "../../query/types";
import type {
  ComponentContractDefinition,
  PropertyDefinition,
  VersionedComponentDefinition,
} from "../types";
import AdvancedChartComponent from "./AdvancedChartComponent.vue";
import AdvancedDataComponent from "./AdvancedDataComponent.vue";
import AdvancedGeoComponent from "./AdvancedGeoComponent.vue";
import MediaEmbedComponent from "./MediaEmbedComponent.vue";
import SpecialChartComponent from "./SpecialChartComponent.vue";

export const ADVANCED_COMPONENT_TYPES = [
  "builtin.map_drilldown",
  "builtin.flow_map",
  "builtin.bubble_map",
  "builtin.relation_graph",
  "builtin.org_chart",
  "builtin.sankey",
  "builtin.steps",
  "builtin.gantt",
  "builtin.calendar_heatmap",
  "builtin.kpi_group",
  "builtin.metric_comparison",
  "builtin.video",
  "builtin.iframe",
  "builtin.word_cloud",
  "builtin.liquid_fill",
  "builtin.polar_bar",
  "builtin.rich_table",
  "builtin.screen_carousel",
] as const;

type AdvancedComponentType = (typeof ADVANCED_COMPONENT_TYPES)[number];

const surfaceStyle = {
  background_color: "var(--screen-panel-background, #0b1b2b)",
  border_color: "var(--screen-panel-border, #1b4160)",
  border_width: 1,
  border_radius: 6,
};

function text(
  name: string,
  label: string,
  defaultValue = "",
  wide = false,
): PropertyDefinition {
  return { name, label, editor: "text", defaultValue, wide };
}

function number(
  name: string,
  label: string,
  defaultValue: number,
  min: number,
  max: number,
): PropertyDefinition {
  return { name, label, editor: "number", defaultValue, min, max, step: 1 };
}

function boolean(
  name: string,
  label: string,
  defaultValue: boolean,
): PropertyDefinition {
  return { name, label, editor: "boolean", defaultValue, wide: true };
}

function objectSchema(
  properties: Record<string, JsonValue>,
  required: string[] = [],
) {
  return {
    type: "object" as const,
    properties,
    required,
    additionalProperties: false,
  };
}

function contract(
  type: AdvancedComponentType,
  category: string,
  propsSchema: Record<string, JsonValue>,
  dataSchema: Record<string, JsonValue>,
  required: string[] = [],
): ComponentContractDefinition {
  return {
    schema_version: 1,
    type,
    version: "1.0.0",
    category,
    props_schema: objectSchema(propsSchema),
    data_input_schema: objectSchema(dataSchema, required),
  };
}

const commonPropsSchema = {
  title: { type: "string" },
  empty_text: { type: "string" },
  animation: { type: "boolean" },
};
const chartProperties = [
  text("title", "标题", "", true),
  boolean("animation", "播放动画", true),
  text("empty_text", "空数据文案", "暂无数据", true),
];
const mapPropsSchema = {
  ...commonPropsSchema,
  asset_id: { type: "string" },
  region_code_property: { type: "string" },
  region_name_property: { type: "string" },
  drill_parameter: { type: "string" },
};
const mapProperties = [
  text("title", "标题", "", true),
  text("asset_id", "GeoJSON 资源 ID", "", true),
  text("region_code_property", "区域编码字段", "code"),
  text("region_name_property", "区域名称字段", "name"),
  text("drill_parameter", "下钻参数", "region"),
  text("empty_text", "空数据文案", "暂无数据", true),
];

function definition(
  value: Omit<VersionedComponentDefinition, "defaultStyle" | "propertyGroups"> & {
    properties: PropertyDefinition[];
  },
): VersionedComponentDefinition {
  const { properties, ...rest } = value;
  return {
    ...rest,
    defaultStyle: surfaceStyle,
    propertyGroups: [{ id: "settings", label: "组件设置", properties }],
  };
}

export const advancedComponentDefinitions: VersionedComponentDefinition[] = [
  definition({
    type: "builtin.map_drilldown", label: "下钻地图", category: "地图",
    defaultFrame: { width: 720, height: 480 },
    defaultProps: { title: "区域分布", asset_id: "", region_code_property: "code", region_name_property: "name", drill_parameter: "region", empty_text: "暂无数据" },
    dataCapability: "geo", demoDataKind: "geo", component: AdvancedGeoComponent,
    properties: mapProperties,
    contract: contract("builtin.map_drilldown", "地图", mapPropsSchema, { code: { type: "string" }, name: { type: "string" }, value: { type: "number" } }, ["code", "value"]),
  }),
  definition({
    type: "builtin.flow_map", label: "地图飞线", category: "地图",
    defaultFrame: { width: 720, height: 480 },
    defaultProps: { title: "流向分布", asset_id: "", empty_text: "暂无数据" },
    dataCapability: "geo", demoDataKind: "geo", component: AdvancedGeoComponent,
    properties: mapProperties,
    contract: contract("builtin.flow_map", "地图", mapPropsSchema, { source: { type: "string" }, source_lng: { type: "number" }, source_lat: { type: "number" }, target: { type: "string" }, target_lng: { type: "number" }, target_lat: { type: "number" }, value: { type: "number" } }, ["source", "source_lng", "source_lat", "target", "target_lng", "target_lat"]),
  }),
  definition({
    type: "builtin.bubble_map", label: "气泡点位", category: "地图",
    defaultFrame: { width: 720, height: 480 },
    defaultProps: { title: "点位分布", asset_id: "", empty_text: "暂无数据" },
    dataCapability: "geo", demoDataKind: "geo", component: AdvancedGeoComponent,
    properties: mapProperties,
    contract: contract("builtin.bubble_map", "地图", mapPropsSchema, { name: { type: "string" }, longitude: { type: "number" }, latitude: { type: "number" }, value: { type: "number" } }, ["name", "longitude", "latitude"]),
  }),
  ...(["builtin.relation_graph", "builtin.org_chart", "builtin.sankey"] as const).map((type) => definition({
    type,
    label: type === "builtin.relation_graph" ? "关系图" : type === "builtin.org_chart" ? "组织架构" : "桑基图",
    category: "关系与流程",
    defaultFrame: { width: 640, height: 420 },
    defaultProps: { title: type === "builtin.sankey" ? "流量关系" : "关系网络", animation: true, empty_text: "暂无数据" },
    dataCapability: "table", demoDataKind: "table", component: AdvancedChartComponent,
    properties: chartProperties,
    contract: contract(type, "关系与流程", commonPropsSchema, { source: { type: "string" }, target: { type: "string" }, value: { type: "number" } }, ["source", "target"]),
  })),
  definition({
    type: "builtin.steps", label: "步骤条", category: "流程与计划",
    defaultFrame: { width: 560, height: 360 },
    defaultProps: { title: "流程进度", empty_text: "暂无步骤" },
    dataCapability: "table", demoDataKind: "table", component: AdvancedDataComponent,
    properties: chartProperties,
    contract: contract("builtin.steps", "流程与计划", commonPropsSchema, { title: { type: "string" }, detail: { type: "string" }, status: { type: "string" } }, ["title", "status"]),
  }),
  definition({
    type: "builtin.gantt", label: "甘特图", category: "流程与计划",
    defaultFrame: { width: 720, height: 420 },
    defaultProps: { title: "项目计划", empty_text: "暂无任务" },
    dataCapability: "table", demoDataKind: "table", component: AdvancedDataComponent,
    properties: chartProperties,
    contract: contract("builtin.gantt", "流程与计划", commonPropsSchema, { task: { type: "string" }, start: { type: "string", format: "date-time" }, end: { type: "string", format: "date-time" }, progress: { type: "number" } }, ["task", "start", "end"]),
  }),
  definition({
    type: "builtin.calendar_heatmap", label: "日历热力", category: "流程与计划",
    defaultFrame: { width: 720, height: 360 },
    defaultProps: { title: "年度活跃度", animation: true, empty_text: "暂无数据" },
    dataCapability: "series", demoDataKind: "series", component: AdvancedChartComponent,
    properties: chartProperties,
    contract: contract("builtin.calendar_heatmap", "流程与计划", commonPropsSchema, { date: { type: "string", format: "date" }, value: { type: "number" } }, ["date", "value"]),
  }),
  ...(["builtin.kpi_group", "builtin.metric_comparison"] as const).map((type) => definition({
    type,
    label: type === "builtin.kpi_group" ? "指标卡组" : "多指标对比",
    category: "指标与状态",
    defaultFrame: { width: 640, height: 280 },
    defaultProps: { title: type === "builtin.kpi_group" ? "核心指标" : "指标对比", empty_text: "暂无数据" },
    dataCapability: "table", demoDataKind: "table", component: AdvancedDataComponent,
    properties: chartProperties,
    contract: contract(type, "指标与状态", commonPropsSchema, { label: { type: "string" }, value: { type: "number" }, comparison: { type: ["number", "string"] } }, ["label", "value"]),
  })),
  definition({
    type: "builtin.video", label: "视频", category: "媒体与嵌入",
    defaultFrame: { width: 640, height: 360 },
    defaultProps: { title: "", asset_id: "", autoplay: false, muted: true, loop: false },
    dataCapability: "none", demoDataKind: "none", component: MediaEmbedComponent,
    properties: [text("title", "标题", "", true), text("asset_id", "视频资源 ID", "", true), boolean("autoplay", "自动播放", false), boolean("muted", "静音", true), boolean("loop", "循环播放", false)],
    contract: contract("builtin.video", "媒体与嵌入", { title: { type: "string" }, asset_id: { type: "string" }, autoplay: { type: "boolean" }, muted: { type: "boolean" }, loop: { type: "boolean" } }, {}),
  }),
  definition({
    type: "builtin.iframe", label: "网页嵌入", category: "媒体与嵌入",
    defaultFrame: { width: 720, height: 420 },
    defaultProps: { title: "嵌入页面", url: "" },
    dataCapability: "none", demoDataKind: "none", component: MediaEmbedComponent,
    properties: [text("title", "标题", "嵌入页面", true), text("url", "HTTP(S) 地址", "", true)],
    contract: contract("builtin.iframe", "媒体与嵌入", { title: { type: "string" }, url: { type: "string", format: "uri" } }, {}),
  }),
  definition({
    type: "builtin.word_cloud", label: "词云", category: "场景化图表",
    defaultFrame: { width: 560, height: 360 },
    defaultProps: { title: "热点词", animation: true, empty_text: "暂无数据" },
    dataCapability: "series", demoDataKind: "series", component: SpecialChartComponent,
    properties: chartProperties,
    contract: contract("builtin.word_cloud", "场景化图表", commonPropsSchema, { name: { type: "string" }, value: { type: "number" } }, ["name", "value"]),
  }),
  definition({
    type: "builtin.liquid_fill", label: "水球图", category: "场景化图表",
    defaultFrame: { width: 360, height: 320 },
    defaultProps: { title: "完成率", animation: true, empty_text: "暂无数据" },
    dataCapability: "single", demoDataKind: "single", component: SpecialChartComponent,
    properties: chartProperties,
    contract: contract("builtin.liquid_fill", "场景化图表", commonPropsSchema, { value: { type: "number", minimum: 0, maximum: 100 } }, ["value"]),
  }),
  definition({
    type: "builtin.polar_bar", label: "极坐标柱", category: "场景化图表",
    defaultFrame: { width: 520, height: 380 },
    defaultProps: { title: "环形对比", animation: true, empty_text: "暂无数据" },
    dataCapability: "series", demoDataKind: "series", component: AdvancedChartComponent,
    properties: chartProperties,
    contract: contract("builtin.polar_bar", "场景化图表", commonPropsSchema, { category: { type: "string" }, value: { type: "number" } }, ["category", "value"]),
  }),
  definition({
    type: "builtin.rich_table", label: "富表格", category: "列表与分析",
    defaultFrame: { width: 720, height: 420 },
    defaultProps: { title: "明细数据", merge_columns: 1, highlight_threshold: 80, empty_text: "暂无数据" },
    dataCapability: "table", demoDataKind: "table", component: AdvancedDataComponent,
    properties: [text("title", "标题", "明细数据", true), number("merge_columns", "合并前 N 列", 1, 0, 4), number("highlight_threshold", "高亮阈值", 80, -1000000, 1000000), text("empty_text", "空数据文案", "暂无数据", true)],
    contract: contract("builtin.rich_table", "列表与分析", { title: { type: "string" }, merge_columns: { type: "integer", minimum: 0, maximum: 4 }, highlight_threshold: { type: "number" }, empty_text: { type: "string" } }, { columns: { type: "array" }, rows: { type: "array" } }, ["columns", "rows"]),
  }),
  definition({
    type: "builtin.screen_carousel", label: "多屏轮播", category: "媒体与嵌入",
    defaultFrame: { width: 960, height: 540 },
    defaultProps: { title: "", screen_urls: "", interval_seconds: 10 },
    dataCapability: "none", demoDataKind: "none", component: MediaEmbedComponent,
    properties: [text("title", "标题", "", true), text("screen_urls", "大屏地址（每行一个）", "", true), number("interval_seconds", "轮播秒数", 10, 5, 120)],
    contract: contract("builtin.screen_carousel", "媒体与嵌入", { title: { type: "string" }, screen_urls: { type: "string" }, interval_seconds: { type: "number", minimum: 5, maximum: 120 } }, {}),
  }),
];
