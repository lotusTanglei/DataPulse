import { mount } from "@vue/test-utils";
import { expect, test, vi } from "vitest";

import type { QueryResult } from "../../query/types";
import { defaultComponentRegistry } from "../registry";
import type { ComponentInstance } from "../types";
import EChartComponent from "./EChartComponent.vue";
import {
  buildChartOption,
  buildGeoMapOption,
  type GeoFeatureCollection,
} from "./chartOptions";

vi.mock("vue-echarts", () => ({
  default: {
    name: "VChart",
    props: ["option", "autoresize"],
    emits: ["click"],
    template: '<div data-v-chart="true" />',
  },
}));

function result(): QueryResult {
  return {
    request_id: "chart-query",
    columns: [
      { name: "region", data_type: "text" },
      { name: "sales", data_type: "numeric" },
      { name: "profit", data_type: "numeric" },
    ],
    rows: [
      ["east", 120, 30],
      ["west", 80, 12],
    ],
    row_count: 2,
    truncated: false,
    duration_ms: 5,
  };
}

function chartInstance(
  type: ComponentInstance["type"],
  visualType: string,
  props: Record<string, string> = {},
): ComponentInstance {
  return {
    id: `${type}-1`,
    type,
    frame: { x: 0, y: 0, width: 640, height: 360 },
    props,
    data_binding: {
      chart_spec: {
        dataset_id: "sales",
        dimensions: ["region"],
        measures: [
          { field: "sales", aggregation: "sum" },
          { field: "profit", aggregation: "sum" },
        ],
        visual: { type: visualType, title: "区域销售" },
      },
    },
  };
}

test("line, area, and theme colors are declarative options", () => {
  const line = buildChartOption(
    chartInstance("builtin.line", "line"),
    result(),
    { chart_colors: ["#2563eb", "#16a34a"], text_primary: "#111827" },
  );
  const area = buildChartOption(
    chartInstance("builtin.line", "area"),
    result(),
    {},
  );

  expect(line.color).toEqual(["#2563eb", "#16a34a"]);
  expect(line.title).toMatchObject({ text: "区域销售" });
  expect(line.xAxis).toMatchObject({
    type: "category",
    data: ["east", "west"],
  });
  expect(line.series).toMatchObject([
    { type: "line", name: "sales", data: [120, 80] },
    { type: "line", name: "profit", data: [30, 12] },
  ]);
  expect(area.series).toMatchObject([
    { type: "line", areaStyle: {} },
    { type: "line", areaStyle: {} },
  ]);
});

test("interactive line charts expose transparent data-point hit targets", () => {
  const interactive = chartInstance("builtin.line", "line");
  interactive.interactions = [
    {
      event: "click",
      action: "set_parameter",
      field: "region",
      parameter: "selected_region",
    },
  ];

  const option = buildChartOption(interactive, result(), {});

  expect(Array.isArray(option.series) ? option.series[0] : null).toMatchObject({
    showSymbol: true,
    symbolSize: 14,
    itemStyle: { opacity: 0 },
  });
});

test("bar orientation and donut radius are explicit variants", () => {
  const horizontal = buildChartOption(
    chartInstance("builtin.bar", "bar", { orientation: "horizontal" }),
    result(),
    {},
  );
  const donut = buildChartOption(
    chartInstance("builtin.pie", "pie", { variant: "donut" }),
    result(),
    {},
  );

  expect(horizontal.yAxis).toMatchObject({
    type: "category",
    data: ["east", "west"],
  });
  expect(horizontal.xAxis).toMatchObject({ type: "value" });
  expect(donut.series).toMatchObject([
    {
      type: "pie",
      radius: ["48%", "72%"],
      data: [
        { name: "east", value: 120 },
        { name: "west", value: 80 },
      ],
    },
  ]);
});

test("chart click emits only a declared parameter interaction", async () => {
  const interactive = chartInstance("builtin.bar", "bar");
  interactive.interactions = [
    {
      event: "click",
      action: "set_parameter",
      field: "region",
      parameter: "selected_region",
    },
  ];
  const wrapper = mount(EChartComponent, {
    props: {
      instance: interactive,
      result: result(),
      loading: false,
      error: null,
      loadAsset: vi.fn(),
      theme: {},
    },
  });

  wrapper.getComponent({ name: "VChart" }).vm.$emit("click", {
    data: { __row: { region: "east", sales: 120 } },
  });
  await wrapper.vm.$nextTick();

  expect(wrapper.emitted("interaction")).toEqual([
    [
      {
        type: "set_parameter",
        name: "selected_region",
        value: "east",
      },
    ],
  ]);
});

test("GeoJSON map joins query rows by configured region code", () => {
  const geojson: GeoFeatureCollection = {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        properties: { code: "east", name: "华东" },
        geometry: { type: "Polygon", coordinates: [] },
      },
      {
        type: "Feature",
        properties: { code: "north", name: "华北" },
        geometry: { type: "Polygon", coordinates: [] },
      },
    ],
  };
  const option = buildGeoMapOption(
    chartInstance("builtin.geo_map", "map", {
      region_code_property: "code",
      region_name_property: "name",
    }),
    result(),
    "datapulse-map-asset",
    geojson,
    {},
  );

  expect(option.series).toMatchObject([
    {
      type: "map",
      map: "datapulse-map-asset",
      data: [
        { name: "华东", value: 120 },
        { name: "华北", value: "-" },
      ],
    },
  ]);
});

test("registers the complete built-in component system", () => {
  expect(
    defaultComponentRegistry
      .list()
      .map((definition) => definition.type)
      .sort(),
  ).toEqual([
    "builtin.alert_list",
    "builtin.bar",
    "builtin.digital_number",
    "builtin.divider",
    "builtin.funnel",
    "builtin.gauge",
    "builtin.geo_map",
    "builtin.heatmap",
    "builtin.image",
    "builtin.kpi",
    "builtin.line",
    "builtin.panel",
    "builtin.pie",
    "builtin.progress",
    "builtin.radar",
    "builtin.ranking",
    "builtin.scatter",
    "builtin.status_matrix",
    "builtin.table",
    "builtin.text",
    "builtin.timeline",
  ]);
});
