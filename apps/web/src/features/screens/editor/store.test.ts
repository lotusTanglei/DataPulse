import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import type { ChartSpec } from "../../../contracts";
import type { Screen } from "../types";
import { useScreenEditorStore } from "./store";

const screen: Screen = {
  id: "screen-1",
  name: "运营总览",
  description: "",
  draft_revision: 0,
  published_at: null,
  created_at: "2026-07-30T03:00:00Z",
  updated_at: "2026-07-30T03:00:00Z",
  draft_document: {
    schema_version: 1,
    canvas: { width: 1920, height: 1080, background: {} },
    theme: { id: "datapulse-dark", tokens: {} },
    refresh: { mode: "disabled", interval_seconds: null },
    parameters: [],
    components: [
      {
        id: "text-1",
        type: "builtin.text",
        frame: { x: 40, y: 40, width: 320, height: 120, z_index: 0 },
        state: { locked: false, hidden: false },
        props: { text: "原始文本" },
        style: {},
        data_binding: {},
        interactions: [],
      },
    ],
  },
  published_document: null,
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  setActivePinia(createPinia());
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("loads, edits, and autosaves with the current revision after 800ms", async () => {
  let patchPayload: unknown;
  const fetchMock = vi.fn(
    (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/admin/screens/screen-1" && init?.method === "GET") {
        return Promise.resolve(jsonResponse(screen));
      }
      if (url === "/api/admin/screens/screen-1" && init?.method === "PATCH") {
        patchPayload = JSON.parse(String(init.body));
        return Promise.resolve(
          jsonResponse({
            ...screen,
            draft_revision: 1,
            draft_document: (patchPayload as { draft_document: unknown })
              .draft_document,
          }),
        );
      }
      throw new Error(`Unexpected request: ${url}`);
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  const store = useScreenEditorStore();
  await store.load("screen-1");

  store.dispatch({
    type: "update_frame",
    component_ids: ["text-1"],
    patch: { x: 120 },
  });

  expect(store.saveState).toBe("dirty");
  expect(store.document?.components?.[0]?.frame.x).toBe(120);
  await vi.advanceTimersByTimeAsync(799);
  expect(fetchMock).toHaveBeenCalledTimes(1);
  await vi.advanceTimersByTimeAsync(1);
  await flushPromises();

  expect(patchPayload).toMatchObject({
    expected_revision: 0,
    draft_document: {
      components: [{ frame: { x: 120 } }],
    },
  });
  expect(store.screen?.draft_revision).toBe(1);
  expect(store.saveState).toBe("saved");
});

test("undo and redo participate in autosave history", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(jsonResponse(screen))),
  );
  const store = useScreenEditorStore();
  await store.load("screen-1");
  expect(store.canUndo).toBe(false);

  store.dispatch({
    type: "update_frame",
    component_ids: ["text-1"],
    patch: { x: 120 },
  });
  expect(store.canUndo).toBe(true);
  store.undo();
  expect(store.document?.components?.[0]?.frame.x).toBe(40);
  expect(store.canRedo).toBe(true);
  store.redo();
  expect(store.document?.components?.[0]?.frame.x).toBe(120);
  expect(store.canRedo).toBe(false);
});

test("a revision conflict stops automatic retry", async () => {
  const fetchMock = vi.fn(
    (_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === "GET") {
        return Promise.resolve(jsonResponse(screen));
      }
      return Promise.resolve(
        jsonResponse(
          {
            error: {
              code: "SCREEN_REVISION_CONFLICT",
              message: "草稿已变化。",
              request_id: "conflict-1",
              field_errors: [],
            },
          },
          409,
        ),
      );
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  const store = useScreenEditorStore();
  await store.load("screen-1");
  store.dispatch({
    type: "update_frame",
    component_ids: ["text-1"],
    patch: { x: 120 },
  });

  await vi.advanceTimersByTimeAsync(800);
  await flushPromises();

  expect(store.saveState).toBe("conflict");
  store.dispatch({
    type: "update_frame",
    component_ids: ["text-1"],
    patch: { x: 160 },
  });
  expect(store.saveState).toBe("conflict");
  await vi.advanceTimersByTimeAsync(5000);
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

test("chart suggestions replace the target component and mark the draft dirty", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(jsonResponse(screen))),
  );
  const store = useScreenEditorStore();
  await store.load("screen-1");

  const suggestion: ChartSpec = {
    schema_version: 1,
    dataset_id: "sales",
    dimensions: ["region"],
    measures: [{ field: "amount", aggregation: "sum" }],
    filters: [],
    sort: [],
    limit: 1000,
    visual: { type: "bar", title: "按区域销售额" },
  };

  store.applyChartSuggestion("text-1", suggestion);

  expect(store.saveState).toBe("dirty");
  expect(store.document?.components?.[0]).toMatchObject({
    id: "text-1",
    type: "builtin.bar",
    props: { title: "按区域销售额" },
    data_binding: {
      chart_spec: {
        dataset_id: "sales",
        visual: { type: "bar", title: "按区域销售额" },
      },
    },
  });
});

test("applies an AI edit batch as one undoable history entry", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(jsonResponse(screen))),
  );
  const store = useScreenEditorStore();
  await store.load("screen-1");

  store.applyAiEdit([
    {
      type: "update_props",
      component_id: "text-1",
      patch: { text: "华东销售分析" },
    },
    {
      type: "update_frame",
      component_ids: ["text-1"],
      patch: { x: 120, y: 80 },
    },
  ]);

  expect(store.document?.components?.[0]).toMatchObject({
    frame: { x: 120, y: 80 },
    props: { text: "华东销售分析" },
  });
  store.undo();
  expect(store.document?.components?.[0]).toMatchObject({
    frame: { x: 40, y: 40 },
    props: { text: "原始文本" },
  });
  expect(store.canRedo).toBe(true);
  store.redo();
  expect(store.document?.components?.[0]?.props?.text).toBe("华东销售分析");
});
