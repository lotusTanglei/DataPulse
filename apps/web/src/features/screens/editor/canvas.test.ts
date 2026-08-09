import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import type { Screen } from "../types";
import LayersPanel from "./LayersPanel.vue";
import ScreenCanvas from "./ScreenCanvas.vue";
import { useScreenEditorStore } from "./store";

const screen: Screen = {
  id: "screen-canvas",
  name: "画布测试",
  description: "",
  draft_revision: 0,
  published_at: null,
  created_at: "2026-07-30T03:00:00Z",
  updated_at: "2026-07-30T03:00:00Z",
  published_document: null,
  draft_document: {
    schema_version: 1,
    canvas: { width: 1000, height: 600, background: { color: "#0b1020" } },
    components: [
      {
        id: "text-1",
        type: "builtin.text",
        frame: { x: 40, y: 40, width: 200, height: 100, z_index: 0 },
        state: { locked: false, hidden: false },
        props: { text: "标题" },
      },
      {
        id: "kpi-1",
        type: "builtin.kpi",
        frame: { x: 300, y: 100, width: 240, height: 120, z_index: 1 },
        state: { locked: false, hidden: false },
        props: { label: "销售额" },
      },
      {
        id: "locked-1",
        type: "builtin.text",
        frame: { x: 600, y: 80, width: 160, height: 80, z_index: 2 },
        state: { locked: true, hidden: false },
        props: { text: "锁定" },
      },
      {
        id: "hidden-1",
        type: "builtin.text",
        frame: { x: 0, y: 300, width: 160, height: 80, z_index: 3 },
        state: { locked: false, hidden: true },
        props: { text: "隐藏" },
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
    vi.fn(() => Promise.resolve(jsonResponse(screen))),
  );
  await useScreenEditorStore().load(screen.id);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("drag snaps unlocked selected components to the ten-pixel grid", () => {
  const store = useScreenEditorStore();
  store.selection = ["text-1", "locked-1"];
  const wrapper = mount(ScreenCanvas, {
    props: { idFactory: () => "copy-1" },
  });

  wrapper.vm.commitDrag(store.selection, { dx: 17, dy: 24 });

  expect(store.document?.components?.[0]?.frame).toMatchObject({
    x: 60,
    y: 60,
  });
  expect(store.document?.components?.[2]?.frame).toMatchObject({
    x: 600,
    y: 80,
  });
});

test("bound components show draft query results while editing", async () => {
  const store = useScreenEditorStore();
  store.document!.components!.find((component) => component.id === "kpi-1")!.data_binding = {
    chart_spec: {
      schema_version: 1,
      dataset_id: "sales",
      dimensions: ["region"],
      measures: [{ field: "amount", aggregation: "sum" }],
      filters: [],
      sort: [],
      limit: 100,
      visual: { type: "kpi", title: "" },
    },
  };
  const queryResult = {
    request_id: "editor-query-1",
    columns: [{ name: "amount", data_type: "number" }],
    rows: [[12345]],
    row_count: 1,
    truncated: false,
    duration_ms: 3,
  };
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) =>
      Promise.resolve(
        jsonResponse(
          String(input) === "/api/admin/screens/query-document"
            ? queryResult
            : screen,
        ),
      ),
    ),
  );

  const wrapper = mount(ScreenCanvas);
  await flushPromises();

  expect(wrapper.get('[data-canvas-component="kpi-1"]').text()).toContain("12,345");
});

test("multi-selection exposes one bounding box and aligns in one undo step", () => {
  const store = useScreenEditorStore();
  store.selection = ["text-1", "kpi-1"];
  const wrapper = mount(ScreenCanvas);

  expect(wrapper.vm.selectionBounds).toMatchObject({
    x: 40,
    y: 40,
    width: 500,
    height: 180,
  });
  wrapper.vm.alignSelection("left");
  expect(
    store.document?.components
      ?.slice(0, 2)
      .map((component) => component.frame.x),
  ).toEqual([40, 40]);
  store.undo();
  expect(store.document?.components?.[1]?.frame.x).toBe(300);
});

test("hidden layers stay selectable in layers but are absent from canvas", () => {
  const store = useScreenEditorStore();
  const canvas = mount(ScreenCanvas);
  const layers = mount(LayersPanel);

  expect(canvas.find('[data-canvas-component="hidden-1"]').exists()).toBe(false);
  expect(
    layers
      .get('[data-layer-id="hidden-1"]')
      .find('button[aria-label="显示图层"]')
      .exists(),
  ).toBe(true);
  layers.get('[data-layer-id="hidden-1"]').trigger("click");
  expect(store.selection).toEqual(["hidden-1"]);
});

test("copy and paste regenerate component IDs and preserve one grouped action", () => {
  const store = useScreenEditorStore();
  store.selection = ["text-1", "kpi-1"];
  const ids = ["text-copy", "kpi-copy"];
  const wrapper = mount(ScreenCanvas, {
    props: { idFactory: () => ids.shift()! },
  });

  wrapper.vm.copySelection();
  wrapper.vm.pasteSelection();

  expect(store.document?.components?.slice(-2).map((item) => item.id)).toEqual([
    "text-copy",
    "kpi-copy",
  ]);
  expect(store.selection).toEqual(["text-copy", "kpi-copy"]);
  store.undo();
  expect(store.document?.components).toHaveLength(4);
});

test("layer ordering moves one component to the front in one undo step", () => {
  const store = useScreenEditorStore();
  const layers = mount(LayersPanel);

  layers.vm.moveLayer("text-1", "front");

  expect(store.document?.components?.at(-1)?.id).toBe("text-1");
  store.undo();
  expect(store.document?.components?.[0]?.id).toBe("text-1");
});

test("zoom and fit stay inside supported editor bounds", async () => {
  const wrapper = mount(ScreenCanvas);
  wrapper.vm.setZoom(3);
  expect(wrapper.vm.zoom).toBe(2);
  wrapper.vm.fitToViewport(500, 300);
  await flushPromises();
  expect(wrapper.vm.zoom).toBe(0.5);
});
