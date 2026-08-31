import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { toRaw } from "vue";

import type { Dataset } from "../../datasets/types";
import type { Screen } from "../types";
import InspectorPanel from "./InspectorPanel.vue";
import { useScreenEditorStore } from "./store";

const dataset: Dataset = {
  id: "sales",
  name: "销售数据",
  data_source_id: "source-1",
  created_at: "2026-07-30T03:00:00Z",
  updated_at: "2026-07-30T03:00:00Z",
  definition: {
    schema_version: 1,
    id: "sales",
    name: "销售数据",
    data_source_id: "source-1",
    query: { kind: "sql", sql: "select region, amount from sales" },
    fields: [
      { name: "region", data_type: "string" },
      { name: "amount", data_type: "number" },
    ],
    parameters: [],
    cache: { mode: "disabled", ttl_seconds: null },
    refresh: { mode: "manual", interval_seconds: null, cron: null },
    max_rows: 1000,
    timeout_seconds: 30,
  },
};

const screen: Screen = {
  id: "screen-inspector",
  name: "属性测试",
  description: "",
  draft_revision: 0,
  published_at: null,
  created_at: "2026-07-30T03:00:00Z",
  updated_at: "2026-07-30T03:00:00Z",
  published_document: null,
  draft_document: {
    schema_version: 1,
    canvas: { width: 1920, height: 1080, background: { color: "#101827" } },
    theme: { id: "datapulse-dark", tokens: { screen_accent: "#22c55e" } },
    parameters: [
      {
        id: "region",
        name: "region",
        data_type: "string",
        default: null,
        mutable: true,
      },
    ],
    components: [
      {
        id: "bar-1",
        type: "builtin.bar",
        frame: { x: 40, y: 40, width: 640, height: 360 },
        props: {},
        data_binding: {
          chart_spec: {
            dataset_id: "sales",
            dimensions: ["region"],
            measures: [{ field: "amount", aggregation: "avg" }],
            visual: { type: "bar" },
          },
        },
        interactions: [
          {
            event: "click",
            action: "set_parameter",
            field: "region",
            parameter: "region",
          },
        ],
      },
    ],
  },
};

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(async () => {
  vi.useFakeTimers();
  setActivePinia(createPinia());
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) =>
      Promise.resolve(
        jsonResponse(
          String(input) === "/api/admin/datasets" ? [dataset] : screen,
        ),
      ),
    ),
  );
  const store = useScreenEditorStore();
  await store.load(screen.id);
  store.selection = ["bar-1"];
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("inspector builds one validated ChartSpec from dataset fields", async () => {
  const store = useScreenEditorStore();
  const wrapper = mount(InspectorPanel);
  await flushPromises();

  wrapper.vm.bindChart({
    datasetId: "sales",
    dimension: "region",
    measure: "amount",
    aggregation: "sum",
  });

  expect(store.document?.components?.[0]?.data_binding).toEqual({
    chart_spec: {
      schema_version: 1,
      dataset_id: "sales",
      dimensions: ["region"],
      measures: [{ field: "amount", aggregation: "sum" }],
      filters: [],
      sort: [],
      limit: 1000,
      visual: { type: "bar", title: "" },
    },
  });
});

test("inspector updates theme, background, and click parameter mapping", () => {
  const store = useScreenEditorStore();
  const wrapper = mount(InspectorPanel);

  wrapper.vm.updateTheme("#2563eb", "#0b1020");
  wrapper.vm.setClickInteraction("region", "region");

  expect(store.document?.theme?.tokens).toMatchObject({
    screen_accent: "#2563eb",
  });
  expect(store.document?.canvas.background).toEqual({ color: "#0b1020" });
  expect(store.document?.components?.[0]?.interactions).toEqual([
    {
      event: "click",
      action: "set_parameter",
      field: "region",
      parameter: "region",
    },
  ]);
});

test("component properties are rendered from registry metadata", async () => {
  const store = useScreenEditorStore();
  const current = JSON.parse(JSON.stringify(toRaw(store.document!.components![0]!)));
  store.dispatch({
    type: "replace_component",
    component_id: "bar-1",
    component: {
      ...current,
      type: "builtin.panel",
      props: { title: "原始标题", frame_variant: "plain", show_grid: true },
      data_binding: {},
    },
  });
  store.selection = ["bar-1"];
  const wrapper = mount(InspectorPanel);

  const title = wrapper.get('[data-property-name="title"] input');
  expect((title.element as HTMLInputElement).value).toBe("原始标题");
  await title.setValue("新的标题");
  await wrapper
    .get('[data-property-name="frame_variant"] select')
    .setValue("corner");
  await wrapper
    .get('[data-property-name="show_grid"] input[type="checkbox"]')
    .setValue(false);

  expect(store.document?.components?.[0]?.props).toMatchObject({
    title: "新的标题",
    frame_variant: "corner",
    show_grid: false,
  });
});

test("theme inspector persists panel and chart tokens", async () => {
  const store = useScreenEditorStore();
  const wrapper = mount(InspectorPanel);
  await flushPromises();
  await wrapper.get('[data-inspector-tab="style"]').trigger("click");
  await wrapper
    .get('[data-theme-panel-background]')
    .setValue("#123456");
  await wrapper.get('[data-theme-text-secondary]').setValue("#aabbcc");
  await wrapper.get('[data-theme-chart-colors]').setValue("#123456, #abcdef");
  await wrapper.get('[data-apply-theme]').trigger("click");

  expect(store.document?.theme?.tokens).toMatchObject({
    panel_background: "#123456",
    text_secondary: "#aabbcc",
    chart_colors: ["#123456", "#abcdef"],
  });
});

test("visible data form applies selected dataset fields", async () => {
  const store = useScreenEditorStore();
  const wrapper = mount(InspectorPanel);
  await flushPromises();

  await wrapper.get('[data-inspector-dataset]').setValue("sales");
  await wrapper.get('[data-inspector-dimension]').setValue("region");
  await wrapper.get('[data-inspector-measure]').setValue("amount");
  await wrapper.get('[data-apply-binding]').trigger("click");

  expect(
    (
      store.document?.components?.[0]?.data_binding?.chart_spec as {
        dataset_id?: string;
      }
  ).dataset_id,
  ).toBe("sales");
});

test("inspector binds demo data and materializes it as static data", async () => {
  const store = useScreenEditorStore();
  const wrapper = mount(InspectorPanel);
  await flushPromises();

  await wrapper.get('[data-data-source="mock"]').trigger("click");
  expect(store.document?.components?.[0]?.data_binding).toMatchObject({
    source: "mock",
    mock_data: { seed: 42 },
  });
  await wrapper.get("[data-materialize-demo]").trigger("click");
  expect(store.document?.components?.[0]?.data_binding?.source).toBe("static");
  expect(store.document?.components?.[0]?.data_binding?.static_data).toMatchObject({
    schema_version: 1,
  });
});

test("inspector validates and saves one-level static object arrays", async () => {
  const store = useScreenEditorStore();
  const wrapper = mount(InspectorPanel);
  await flushPromises();

  await wrapper.get('[data-data-source="static"]').trigger("click");
  await wrapper.get("[data-static-data-json]").setValue('[{"name":"A","value":12},{"name":"B","value":8}]');
  await wrapper.get("[data-apply-static]").trigger("click");

  expect(store.document?.components?.[0]?.data_binding).toMatchObject({
    source: "static",
    static_data: {
      columns: [
        { name: "name", data_type: "string" },
        { name: "value", data_type: "number" },
      ],
      rows: [["A", 12], ["B", 8]],
    },
  });
});

test("inspector restores persisted data binding when selecting a component", async () => {
  const wrapper = mount(InspectorPanel);
  await flushPromises();

  expect(
    (wrapper.get('[data-inspector-dataset]').element as HTMLSelectElement).value,
  ).toBe("sales");
  expect(
    (wrapper.get('[data-inspector-dimension]').element as HTMLSelectElement).value,
  ).toBe("region");
  expect(
    (wrapper.get('[data-inspector-measure]').element as HTMLSelectElement).value,
  ).toBe("amount");
  expect(
    (wrapper.get('[data-inspector-aggregation]').element as HTMLSelectElement).value,
  ).toBe("avg");
  expect((wrapper.get('[data-theme-accent]').element as HTMLInputElement).value).toBe(
    "#22c55e",
  );
  expect(
    (wrapper.get('[data-theme-background]').element as HTMLInputElement).value,
  ).toBe("#101827");
});

test("non-data image components hide chart binding and click interaction", () => {
  const store = useScreenEditorStore();
  store.dispatch({
    type: "add_component",
    component: {
      id: "image-1",
      type: "builtin.image",
      frame: { x: 20, y: 20, width: 320, height: 180 },
      props: { asset_id: "" },
    },
  });
  store.selection = ["image-1"];

  const wrapper = mount(InspectorPanel);

  expect(wrapper.text()).not.toContain("应用数据绑定");
  expect(wrapper.text()).not.toContain("应用点击联动");
  expect(wrapper.text()).toContain("图片资源 ID");
});

test("base tab edits the complete frame and component state", async () => {
  const store = useScreenEditorStore();
  const wrapper = mount(InspectorPanel);
  await flushPromises();
  await wrapper.get('[data-inspector-tab="base"]').trigger("click");

  await wrapper.get('[data-frame-field="width"]').setValue("720");
  await wrapper.get('[data-frame-field="height"]').setValue("420");
  await wrapper.get('[data-component-lock]').trigger("click");

  expect(store.document?.components?.[0]?.frame).toMatchObject({
    width: 720,
    height: 420,
  });
  expect(store.document?.components?.[0]?.state?.locked).toBe(true);
  expect(wrapper.get('[data-inspector-tab="base"]').classes()).toContain(
    "is-active",
  );
});

test("table binding selects raw fields without aggregating string values", async () => {
  const store = useScreenEditorStore();
  store.document!.components![0] = {
    ...store.document!.components![0]!,
    type: "builtin.table",
    data_binding: {},
  };
  const wrapper = mount(InspectorPanel);
  await flushPromises();

  await wrapper.get('[data-inspector-dataset]').setValue("sales");
  await wrapper.get('[data-table-field="region"]').setValue(true);
  await wrapper.get('[data-table-field="amount"]').setValue(true);
  await wrapper.get('[data-apply-binding]').trigger("click");

  expect(store.document?.components?.[0]?.data_binding?.chart_spec).toMatchObject({
    dimensions: ["region", "amount"],
    measures: [],
    visual: { type: "table" },
  });
});

test("style and refresh settings round-trip through the inspector", async () => {
  const store = useScreenEditorStore();
  store.dispatch({
    type: "update_style",
    component_id: "bar-1",
    patch: {
      background_color: "#111827",
      text_color: "#f8fafc",
      border_color: "#3b82f6",
      border_width: 2,
      border_radius: 8,
      opacity: 0.8,
    },
  });
  store.dispatch({
    type: "update_refresh",
    refresh: { mode: "interval", interval_seconds: 30 },
  });
  const wrapper = mount(InspectorPanel);
  await flushPromises();

  await wrapper.get('[data-inspector-tab="style"]').trigger("click");
  expect(wrapper.get('[data-style-field="background_color"]').element).toHaveProperty(
    "value",
    "#111827",
  );
  await wrapper.get('[data-style-field="border_radius"]').setValue("12");
  await wrapper.get('[data-apply-component-style]').trigger("click");
  expect(store.document?.components?.[0]?.style).toMatchObject({
    background_color: "#111827",
    border_radius: 12,
    opacity: 0.8,
  });

  await wrapper.get('[data-inspector-tab="advanced"]').trigger("click");
  expect(wrapper.get('[data-refresh-mode]').element).toHaveProperty(
    "value",
    "interval",
  );
  expect(wrapper.get('[data-refresh-interval]').element).toHaveProperty(
    "value",
    "30",
  );
  await wrapper.get('[data-refresh-interval]').setValue("60");
  await wrapper.get('[data-apply-refresh]').trigger("click");
  expect(store.document?.refresh).toEqual({
    mode: "interval",
    interval_seconds: 60,
  });
});
