import { markRaw } from "vue";

import EChartComponent from "./builtins/EChartComponent.vue";
import GeoMapComponent from "./builtins/GeoMapComponent.vue";
import ImageComponent from "./builtins/ImageComponent.vue";
import KpiComponent from "./builtins/KpiComponent.vue";
import ProgressComponent from "./builtins/ProgressComponent.vue";
import TableComponent from "./builtins/TableComponent.vue";
import TextComponent from "./builtins/TextComponent.vue";
import type { ComponentDefinition } from "./types";

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
    defaultFrame: { width: 320, height: 120 },
    defaultProps: { text: "文本", align: "left", font_size: 24 },
    dataCapability: "none",
    component: TextComponent,
  })
  .register({
    type: "builtin.image",
    label: "图片",
    defaultFrame: { width: 480, height: 320 },
    defaultProps: { asset_id: "", alt: "", fit: "cover" },
    dataCapability: "none",
    component: ImageComponent,
  })
  .register({
    type: "builtin.kpi",
    label: "指标",
    defaultFrame: { width: 280, height: 160 },
    defaultProps: { label: "指标", precision: 0, empty_text: "暂无数据" },
    dataCapability: "single",
    component: KpiComponent,
  })
  .register({
    type: "builtin.table",
    label: "表格",
    defaultFrame: { width: 640, height: 360 },
    defaultProps: { max_rows: 100, empty_text: "暂无数据" },
    dataCapability: "table",
    component: TableComponent,
  })
  .register({
    type: "builtin.progress",
    label: "进度",
    defaultFrame: { width: 360, height: 140 },
    defaultProps: { label: "进度", precision: 0, empty_text: "暂无数据" },
    dataCapability: "single",
    component: ProgressComponent,
  })
  .register({
    type: "builtin.line",
    label: "折线图",
    defaultFrame: { width: 640, height: 360 },
    defaultProps: { empty_text: "暂无数据" },
    dataCapability: "series",
    component: EChartComponent,
  })
  .register({
    type: "builtin.bar",
    label: "柱状图",
    defaultFrame: { width: 640, height: 360 },
    defaultProps: { orientation: "vertical", empty_text: "暂无数据" },
    dataCapability: "series",
    component: EChartComponent,
  })
  .register({
    type: "builtin.pie",
    label: "饼图",
    defaultFrame: { width: 480, height: 360 },
    defaultProps: { variant: "pie", empty_text: "暂无数据" },
    dataCapability: "series",
    component: EChartComponent,
  })
  .register({
    type: "builtin.geo_map",
    label: "地图",
    defaultFrame: { width: 720, height: 480 },
    defaultProps: {
      asset_id: "",
      region_code_property: "code",
      region_name_property: "name",
      empty_text: "暂无数据",
    },
    dataCapability: "geo",
    component: GeoMapComponent,
  });
