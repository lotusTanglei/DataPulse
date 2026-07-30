import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

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
    canvas: { width: 1920, height: 1080, background: {} },
    theme: { id: "datapulse-dark", tokens: {} },
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
        data_binding: {},
        interactions: [],
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
