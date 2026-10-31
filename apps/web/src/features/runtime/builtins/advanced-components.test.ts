import { flushPromises, mount } from "@vue/test-utils";
import { expect, test, vi } from "vitest";

import { defaultComponentRegistry } from "../registry";
import { createMockBinding, resolveLocalResult } from "../mockData";
import {
  ADVANCED_COMPONENT_TYPES,
  advancedComponentDefinitions,
} from "./advancedComponents";
import { buildAdvancedChartOption } from "./advancedChartOptions";
import AdvancedDataComponent from "./AdvancedDataComponent.vue";
import MediaEmbedComponent from "./MediaEmbedComponent.vue";

vi.mock("vue-echarts", () => ({
  default: {
    name: "VChart",
    props: ["option", "autoresize"],
    emits: ["click"],
    template: '<div data-v-chart="true" />',
  },
}));

const expectedTypes = [
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

test("registers every batch 2 and batch 3 component with a versioned contract", () => {
  expect(ADVANCED_COMPONENT_TYPES).toEqual(expectedTypes);
  expect(advancedComponentDefinitions).toHaveLength(expectedTypes.length);

  for (const definition of advancedComponentDefinitions) {
    expect(defaultComponentRegistry.get(definition.type)).toBe(definition);
    expect(definition.contract.schema_version).toBe(1);
    expect(definition.contract.version).toMatch(/^1\.\d+\.\d+$/);
    expect(definition.contract.type).toBe(definition.type);
    expect(definition.contract.props_schema.type).toBe("object");
    expect(definition.contract.data_input_schema.type).toBe("object");
  }
});

function queryResult(rows: Array<Array<string | number | null>>) {
  return {
    request_id: "advanced-component",
    columns: [
      { name: "label", data_type: "string" },
      { name: "current", data_type: "number" },
      { name: "previous", data_type: "number" },
    ],
    rows,
    row_count: rows.length,
    truncated: false,
    duration_ms: 0,
  };
}

test.each(advancedComponentDefinitions)(
  "$type mounts its batch renderer with deterministic demo data",
  async (definition) => {
    const dataBinding = definition.dataCapability === "none"
      ? undefined
      : createMockBinding(definition.type, 17);
    const component = {
      id: `${definition.type}-fixture`,
      type: definition.type,
      frame: { x: 0, y: 0, width: definition.defaultFrame.width, height: definition.defaultFrame.height },
      props: definition.type === "builtin.iframe"
        ? { ...definition.defaultProps, url: "https://example.com/status" }
        : definition.type === "builtin.screen_carousel"
          ? { ...definition.defaultProps, screen_urls: "https://example.com/one\nhttps://example.com/two" }
          : definition.defaultProps,
      data_binding: dataBinding,
    };
    const result = dataBinding ? resolveLocalResult(component, dataBinding) : null;
    const wrapper = mount(definition.component, {
      props: {
        instance: component,
        result,
        loading: false,
        error: null,
        loadAsset: vi.fn(),
        mode: "editor",
        theme: {},
      },
    });
    await flushPromises();

    expect(wrapper.attributes("data-v-app")).toBeUndefined();
    expect(wrapper.html()).not.toBe("");
    expect(wrapper.text()).not.toContain("undefined");
    wrapper.unmount();
  },
);

test.each([
  ["builtin.relation_graph", "graph"],
  ["builtin.org_chart", "graph"],
  ["builtin.sankey", "sankey"],
  ["builtin.calendar_heatmap", "heatmap"],
  ["builtin.polar_bar", "bar"],
] as const)("%s compiles a stable ECharts %s series", (type, expectedSeries) => {
  const option = buildAdvancedChartOption(
    {
      id: "chart-1",
      type,
      frame: { x: 0, y: 0, width: 640, height: 360 },
      props: { title: "业务图表" },
    },
    type === "builtin.calendar_heatmap"
      ? queryResult([["2026-09-01", 12, null]])
      : queryResult([["来源", "目标", 12]]),
    {},
  );
  const series = Array.isArray(option.series) ? option.series[0] : option.series;
  expect(series).toMatchObject({ type: expectedSeries });
});

test("calendar heatmap declares dark-theme cell styling", () => {
  const option = buildAdvancedChartOption(
    {
      id: "calendar",
      type: "builtin.calendar_heatmap",
      frame: { x: 0, y: 0, width: 640, height: 360 },
      props: { title: "活跃度" },
    },
    queryResult([["2026-09-01", 12, null]]),
    {},
  );

  expect(option.calendar).toMatchObject({
    itemStyle: { color: "#102b3e", borderColor: "#071522" },
    splitLine: { lineStyle: { color: "#31506a" } },
  });
});

test("advanced demo data follows component contracts and demo map coordinates", () => {
  const resolve = (type: string) => {
    const binding = createMockBinding(type, 17);
    return resolveLocalResult(
      { id: `${type}-demo`, type },
      binding,
    )!;
  };
  const wordCloud = resolve("builtin.word_cloud");
  const polar = resolve("builtin.polar_bar");
  const bubble = resolve("builtin.bubble_map");
  const flow = resolve("builtin.flow_map");
  const map = resolve("builtin.map_drilldown");

  expect(wordCloud.columns.map((column) => column.name)).toEqual(["name", "value"]);
  expect(polar.columns.map((column) => column.name)).toEqual(["category", "value"]);
  expect(map.columns.map((column) => column.name)).toEqual(["code", "value"]);
  expect(map.rows[0]?.[1]).toBeTypeOf("number");
  expect(wordCloud.rows[0]?.[0]).toBe("数据治理");
  for (const row of bubble.rows) {
    expect(row[1]).toBeTypeOf("number");
    expect(row[1] as number).toBeGreaterThanOrEqual(0);
    expect(row[1] as number).toBeLessThanOrEqual(90);
    expect(row[2] as number).toBeGreaterThanOrEqual(0);
    expect(row[2] as number).toBeLessThanOrEqual(60);
  }
  for (const row of flow.rows) {
    for (const index of [1, 2, 4, 5]) {
      expect(row[index] as number).toBeGreaterThanOrEqual(0);
      expect(row[index] as number).toBeLessThanOrEqual(index % 3 === 1 ? 90 : 60);
    }
  }
});

test("data components render Gantt ranges, merged cells, and comparison deltas", () => {
  const shared = { loading: false, error: null, loadAsset: vi.fn() };
  const gantt = mount(AdvancedDataComponent, {
    props: {
      ...shared,
      instance: { id: "gantt", type: "builtin.gantt", frame: { x: 0, y: 0, width: 600, height: 300 }, props: {} },
      result: queryResult([["设计", "2026-09-01", "2026-09-05"]]),
    },
  });
  const table = mount(AdvancedDataComponent, {
    props: {
      ...shared,
      instance: { id: "table", type: "builtin.rich_table", frame: { x: 0, y: 0, width: 600, height: 300 }, props: { merge_columns: 1, highlight_threshold: 80 } },
      result: queryResult([["华东", 92, null], ["华东", 78, null]]),
    },
  });
  const comparison = mount(AdvancedDataComponent, {
    props: {
      ...shared,
      instance: { id: "comparison", type: "builtin.metric_comparison", frame: { x: 0, y: 0, width: 600, height: 300 }, props: {} },
      result: queryResult([["销售额", 120, 100]]),
    },
  });

  expect(gantt.get(".gantt-track i").attributes("style")).toContain("width:");
  expect(table.get("tbody td").attributes("rowspan")).toBe("2");
  expect(table.findAll(".is-highlight")).toHaveLength(1);
  expect(comparison.text()).toContain("+20.0%");
});

test("media embeds reject executable URLs and keep carousel navigation operable", async () => {
  const shared = { result: null, loading: false, error: null, loadAsset: vi.fn(), mode: "editor" as const };
  const unsafe = mount(MediaEmbedComponent, {
    props: {
      ...shared,
      instance: { id: "embed", type: "builtin.iframe", frame: { x: 0, y: 0, width: 600, height: 300 }, props: { url: "javascript:alert(1)" } },
    },
  });
  const carousel = mount(MediaEmbedComponent, {
    props: {
      ...shared,
      instance: { id: "carousel", type: "builtin.screen_carousel", frame: { x: 0, y: 0, width: 600, height: 300 }, props: { screen_urls: "https://example.com/one\nhttps://example.com/two" } },
    },
  });

  expect(unsafe.find("iframe").exists()).toBe(false);
  expect(unsafe.text()).toContain("HTTP(S)");
  expect(carousel.findAll("nav button")).toHaveLength(2);
  await carousel.get('button[aria-label="显示第 2 屏"]').trigger("click");
  expect(carousel.get("iframe").attributes("src")).toContain("/two");
});
