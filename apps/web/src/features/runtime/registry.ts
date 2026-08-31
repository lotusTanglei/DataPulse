import { markRaw } from "vue";

import AlertListComponent from "./builtins/AlertListComponent.vue";
import DigitalNumberComponent from "./builtins/DigitalNumberComponent.vue";
import DividerComponent from "./builtins/DividerComponent.vue";
import EChartComponent from "./builtins/EChartComponent.vue";
import GeoMapComponent from "./builtins/GeoMapComponent.vue";
import GaugeComponent from "./builtins/GaugeComponent.vue";
import ImageComponent from "./builtins/ImageComponent.vue";
import KpiComponent from "./builtins/KpiComponent.vue";
import PanelComponent from "./builtins/PanelComponent.vue";
import ProgressComponent from "./builtins/ProgressComponent.vue";
import RankingComponent from "./builtins/RankingComponent.vue";
import StatusMatrixComponent from "./builtins/StatusMatrixComponent.vue";
import TableComponent from "./builtins/TableComponent.vue";
import TextComponent from "./builtins/TextComponent.vue";
import TimelineComponent from "./builtins/TimelineComponent.vue";
import type {
  ComponentDefinition,
  PropertyDefinition,
  PropertyGroup,
} from "./types";

const transparentStyle = {
  background_color: "transparent",
  border_width: 0,
  border_radius: 0,
};

const surfaceStyle = {
  background_color: "var(--screen-panel-background, #0b1b2b)",
  border_color: "var(--screen-panel-border, #1b4160)",
  border_width: 1,
  border_radius: 10,
};

const chartStyle = {
  ...surfaceStyle,
  border_radius: 8,
};

function propertyGroup(
  id: string,
  label: string,
  properties: PropertyDefinition[],
): PropertyGroup {
  return { id, label, properties };
}

function textProperty(
  name: string,
  label: string,
  defaultValue = "",
  options: Pick<PropertyDefinition, "wide" | "placeholder"> = {},
): PropertyDefinition {
  return { name, label, editor: "text", defaultValue, ...options };
}

function numberProperty(
  name: string,
  label: string,
  defaultValue: number,
  options: Pick<PropertyDefinition, "min" | "max" | "step" | "wide"> = {},
): PropertyDefinition {
  return { name, label, editor: "number", defaultValue, ...options };
}

function selectProperty(
  name: string,
  label: string,
  defaultValue: string,
  options: Array<{ label: string; value: string }>,
  wide = false,
): PropertyDefinition {
  return {
    name,
    label,
    editor: "select",
    defaultValue,
    options,
    wide,
  };
}

function booleanProperty(
  name: string,
  label: string,
  defaultValue: boolean,
): PropertyDefinition {
  return { name, label, editor: "boolean", defaultValue, wide: true };
}

const alignmentOptions = [
  { label: "左对齐", value: "left" },
  { label: "居中", value: "center" },
  { label: "右对齐", value: "right" },
];

const frameOptions = [
  { label: "简洁", value: "plain" },
  { label: "线框", value: "line" },
  { label: "角标", value: "corner" },
  { label: "科技", value: "tech" },
  { label: "玻璃", value: "glass" },
];

const chartProperties = [
  textProperty("title", "标题", "", { wide: true }),
  booleanProperty("show_legend", "显示图例", true),
  booleanProperty("animation", "播放动画", true),
];

export class ComponentRegistry {
  readonly #definitions = new Map<string, ComponentDefinition>();

  constructor() {
    markRaw(this);
  }

  register(definition: ComponentDefinition): this {
    if (this.#definitions.has(definition.type)) {
      throw new Error(
        `Component type is already registered: ${definition.type}`,
      );
    }
    markRaw(definition.component);
    this.#definitions.set(definition.type, definition);
    return this;
  }

  get(type: string): ComponentDefinition | undefined {
    return this.#definitions.get(type);
  }

  has(type: string): boolean {
    return this.#definitions.has(type);
  }

  list(): ComponentDefinition[] {
    return [...this.#definitions.values()];
  }
}

export const defaultComponentRegistry = new ComponentRegistry()
  .register({
    type: "builtin.text",
    label: "文本",
    category: "基础与装饰",
    defaultFrame: { width: 320, height: 120 },
    defaultProps: { text: "文本", align: "left", font_size: 24 },
    defaultStyle: transparentStyle,
    dataCapability: "none",
    demoDataKind: "none",
    propertyGroups: [
      propertyGroup("content", "内容", [
        textProperty("text", "文本内容", "文本", { wide: true }),
        selectProperty("align", "对齐方式", "left", alignmentOptions),
        numberProperty("font_size", "字号", 24, { min: 10, max: 160, step: 1 }),
        numberProperty("font_weight", "字重", 500, { min: 100, max: 900, step: 100 }),
      ]),
    ],
    component: TextComponent,
  })
  .register({
    type: "builtin.image",
    label: "图片",
    category: "基础与装饰",
    defaultFrame: { width: 480, height: 320 },
    defaultProps: { asset_id: "", alt: "", fit: "cover" },
    defaultStyle: surfaceStyle,
    dataCapability: "none",
    demoDataKind: "none",
    propertyGroups: [
      propertyGroup("content", "内容", [
        textProperty("asset_id", "图片资源 ID", "", { wide: true }),
        textProperty("alt", "替代文本", "", { wide: true }),
        selectProperty("fit", "填充方式", "cover", [
          { label: "裁剪填充", value: "cover" },
          { label: "完整显示", value: "contain" },
          { label: "拉伸填充", value: "fill" },
          { label: "原始尺寸", value: "none" },
          { label: "按需缩放", value: "scale-down" },
        ], true),
      ]),
    ],
    component: ImageComponent,
  })
  .register({
    type: "builtin.panel",
    label: "面板",
    category: "基础与装饰",
    defaultFrame: { width: 640, height: 360 },
    defaultProps: {
      title: "面板标题",
      subtitle: "",
      frame_variant: "tech",
      show_grid: true,
    },
    defaultStyle: surfaceStyle,
    dataCapability: "none",
    demoDataKind: "none",
    propertyGroups: [
      propertyGroup("content", "内容", [
        textProperty("title", "标题", "面板标题", { wide: true }),
        textProperty("subtitle", "副标题", "", { wide: true }),
        selectProperty("frame_variant", "面板框架", "tech", frameOptions, true),
        booleanProperty("show_grid", "显示背景网格", true),
      ]),
    ],
    component: PanelComponent,
  })
  .register({
    type: "builtin.divider",
    label: "分割线",
    category: "基础与装饰",
    defaultFrame: { width: 520, height: 32 },
    defaultProps: { orientation: "horizontal", label: "" },
    defaultStyle: transparentStyle,
    dataCapability: "none",
    demoDataKind: "none",
    propertyGroups: [
      propertyGroup("content", "内容", [
        selectProperty("orientation", "方向", "horizontal", [
          { label: "水平", value: "horizontal" },
          { label: "垂直", value: "vertical" },
        ], true),
        textProperty("label", "分隔文字", "", { wide: true }),
      ]),
    ],
    component: DividerComponent,
  })
  .register({
    type: "builtin.digital_number",
    label: "数字翻牌",
    category: "基础与装饰",
    defaultFrame: { width: 320, height: 140 },
    defaultProps: {
      label: "核心指标",
      unit: "",
      prefix: "",
      precision: 0,
      empty_text: "暂无数据",
    },
    defaultStyle: surfaceStyle,
    dataCapability: "single",
    demoDataKind: "single",
    propertyGroups: [
      propertyGroup("content", "内容", [
        textProperty("label", "标签", "核心指标", { wide: true }),
        textProperty("prefix", "前缀", ""),
        textProperty("unit", "单位", ""),
        numberProperty("precision", "小数位", 0, { min: 0, max: 4, step: 1 }),
        textProperty("empty_text", "空数据文案", "暂无数据", { wide: true }),
      ]),
    ],
    component: DigitalNumberComponent,
  })
  .register({
    type: "builtin.kpi",
    label: "指标",
    category: "指标与状态",
    defaultFrame: { width: 280, height: 160 },
    defaultProps: { label: "指标", precision: 0, empty_text: "暂无数据" },
    defaultStyle: surfaceStyle,
    dataCapability: "single",
    demoDataKind: "single",
    propertyGroups: [
      propertyGroup("content", "内容", [
        textProperty("label", "标签", "指标", { wide: true }),
        textProperty("prefix", "前缀", ""),
        textProperty("suffix", "后缀", ""),
        numberProperty("precision", "小数位", 0, { min: 0, max: 8, step: 1 }),
        textProperty("empty_text", "空数据文案", "暂无数据", { wide: true }),
      ]),
    ],
    component: KpiComponent,
  })
  .register({
    type: "builtin.table",
    label: "表格",
    category: "列表与分析",
    defaultFrame: { width: 640, height: 360 },
    defaultProps: { max_rows: 100, empty_text: "暂无数据" },
    defaultStyle: surfaceStyle,
    dataCapability: "table",
    demoDataKind: "table",
    propertyGroups: [
      propertyGroup("content", "内容", [
        numberProperty("max_rows", "最大行数", 100, { min: 1, max: 1000, step: 1 }),
        textProperty("empty_text", "空数据文案", "暂无数据", { wide: true }),
      ]),
    ],
    component: TableComponent,
  })
  .register({
    type: "builtin.progress",
    label: "进度",
    category: "指标与状态",
    defaultFrame: { width: 360, height: 140 },
    defaultProps: { label: "进度", precision: 0, empty_text: "暂无数据" },
    defaultStyle: surfaceStyle,
    dataCapability: "single",
    demoDataKind: "single",
    propertyGroups: [
      propertyGroup("content", "内容", [
        textProperty("label", "标签", "进度", { wide: true }),
        numberProperty("precision", "小数位", 0, { min: 0, max: 4, step: 1 }),
        textProperty("empty_text", "空数据文案", "暂无数据", { wide: true }),
      ]),
    ],
    component: ProgressComponent,
  })
  .register({
    type: "builtin.gauge",
    label: "仪表盘",
    category: "指标与状态",
    defaultFrame: { width: 320, height: 260 },
    defaultProps: { label: "完成率", precision: 1, empty_text: "暂无数据" },
    defaultStyle: surfaceStyle,
    dataCapability: "single",
    demoDataKind: "single",
    propertyGroups: [
      propertyGroup("content", "内容", [
        textProperty("label", "标签", "完成率", { wide: true }),
        numberProperty("precision", "小数位", 1, { min: 0, max: 3, step: 1 }),
        textProperty("empty_text", "空数据文案", "暂无数据", { wide: true }),
      ]),
    ],
    component: GaugeComponent,
  })
  .register({
    type: "builtin.status_matrix",
    label: "状态矩阵",
    category: "指标与状态",
    defaultFrame: { width: 480, height: 300 },
    defaultProps: { title: "运行状态", empty_text: "暂无数据" },
    defaultStyle: surfaceStyle,
    dataCapability: "table",
    demoDataKind: "table",
    propertyGroups: [
      propertyGroup("content", "内容", [
        textProperty("title", "标题", "运行状态", { wide: true }),
        textProperty("empty_text", "空数据文案", "暂无数据", { wide: true }),
      ]),
    ],
    component: StatusMatrixComponent,
  })
  .register({
    type: "builtin.line",
    label: "折线图",
    category: "图表",
    defaultFrame: { width: 640, height: 360 },
    defaultProps: { title: "趋势分析", empty_text: "暂无数据" },
    defaultStyle: chartStyle,
    dataCapability: "series",
    demoDataKind: "series",
    propertyGroups: [propertyGroup("appearance", "图表外观", chartProperties)],
    component: EChartComponent,
  })
  .register({
    type: "builtin.bar",
    label: "柱状图",
    category: "图表",
    defaultFrame: { width: 640, height: 360 },
    defaultProps: { title: "分类对比", orientation: "vertical", empty_text: "暂无数据" },
    defaultStyle: chartStyle,
    dataCapability: "series",
    demoDataKind: "series",
    propertyGroups: [
      propertyGroup("appearance", "图表外观", [
        ...chartProperties,
        selectProperty("orientation", "方向", "vertical", [
          { label: "纵向", value: "vertical" },
          { label: "横向", value: "horizontal" },
        ], true),
      ]),
    ],
    component: EChartComponent,
  })
  .register({
    type: "builtin.pie",
    label: "饼图",
    category: "图表",
    defaultFrame: { width: 480, height: 360 },
    defaultProps: { title: "结构占比", variant: "pie", empty_text: "暂无数据" },
    defaultStyle: chartStyle,
    dataCapability: "series",
    demoDataKind: "series",
    propertyGroups: [
      propertyGroup("appearance", "图表外观", [
        ...chartProperties,
        selectProperty("variant", "图形样式", "pie", [
          { label: "饼图", value: "pie" },
          { label: "环图", value: "donut" },
        ], true),
      ]),
    ],
    component: EChartComponent,
  })
  .register({
    type: "builtin.radar",
    label: "雷达图",
    category: "图表",
    defaultFrame: { width: 520, height: 380 },
    defaultProps: { title: "多维画像", empty_text: "暂无数据" },
    defaultStyle: chartStyle,
    dataCapability: "series",
    demoDataKind: "radar",
    propertyGroups: [propertyGroup("appearance", "图表外观", chartProperties)],
    component: EChartComponent,
  })
  .register({
    type: "builtin.heatmap",
    label: "热力图",
    category: "图表",
    defaultFrame: { width: 640, height: 360 },
    defaultProps: { title: "分布热力", empty_text: "暂无数据" },
    defaultStyle: chartStyle,
    dataCapability: "series",
    demoDataKind: "series",
    propertyGroups: [propertyGroup("appearance", "图表外观", chartProperties)],
    component: EChartComponent,
  })
  .register({
    type: "builtin.scatter",
    label: "散点图",
    category: "图表",
    defaultFrame: { width: 560, height: 360 },
    defaultProps: { title: "关系分布", empty_text: "暂无数据" },
    defaultStyle: chartStyle,
    dataCapability: "series",
    demoDataKind: "series",
    propertyGroups: [propertyGroup("appearance", "图表外观", chartProperties)],
    component: EChartComponent,
  })
  .register({
    type: "builtin.funnel",
    label: "漏斗图",
    category: "图表",
    defaultFrame: { width: 520, height: 360 },
    defaultProps: { title: "阶段转化", empty_text: "暂无数据" },
    defaultStyle: chartStyle,
    dataCapability: "series",
    demoDataKind: "series",
    propertyGroups: [propertyGroup("appearance", "图表外观", chartProperties)],
    component: EChartComponent,
  })
  .register({
    type: "builtin.ranking",
    label: "排行榜",
    category: "列表与分析",
    defaultFrame: { width: 480, height: 360 },
    defaultProps: { title: "Top 排行", empty_text: "暂无数据" },
    defaultStyle: surfaceStyle,
    dataCapability: "table",
    demoDataKind: "ranking",
    propertyGroups: [
      propertyGroup("content", "内容", [
        textProperty("title", "标题", "Top 排行", { wide: true }),
        textProperty("empty_text", "空数据文案", "暂无数据", { wide: true }),
      ]),
    ],
    component: RankingComponent,
  })
  .register({
    type: "builtin.alert_list",
    label: "告警列表",
    category: "列表与分析",
    defaultFrame: { width: 560, height: 360 },
    defaultProps: { title: "实时告警", empty_text: "暂无告警" },
    defaultStyle: surfaceStyle,
    dataCapability: "table",
    demoDataKind: "alerts",
    propertyGroups: [
      propertyGroup("content", "内容", [
        textProperty("title", "标题", "实时告警", { wide: true }),
        textProperty("empty_text", "空数据文案", "暂无告警", { wide: true }),
      ]),
    ],
    component: AlertListComponent,
  })
  .register({
    type: "builtin.timeline",
    label: "时间线",
    category: "列表与分析",
    defaultFrame: { width: 560, height: 360 },
    defaultProps: { title: "事件流", empty_text: "暂无事件" },
    defaultStyle: surfaceStyle,
    dataCapability: "table",
    demoDataKind: "table",
    propertyGroups: [
      propertyGroup("content", "内容", [
        textProperty("title", "标题", "事件流", { wide: true }),
        textProperty("empty_text", "空数据文案", "暂无事件", { wide: true }),
      ]),
    ],
    component: TimelineComponent,
  })
  .register({
    type: "builtin.geo_map",
    label: "地图",
    category: "地图",
    defaultFrame: { width: 720, height: 480 },
    defaultProps: {
      asset_id: "",
      region_code_property: "code",
      region_name_property: "name",
      empty_text: "暂无数据",
    },
    defaultStyle: chartStyle,
    dataCapability: "geo",
    demoDataKind: "geo",
    propertyGroups: [
      propertyGroup("map", "地图配置", [
        textProperty("asset_id", "GeoJSON 资源 ID", "", { wide: true }),
        textProperty("region_code_property", "区域编码字段", "code"),
        textProperty("region_name_property", "区域名称字段", "name"),
        textProperty("empty_text", "空数据文案", "暂无数据", { wide: true }),
      ]),
    ],
    component: GeoMapComponent,
  });
