import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";
import {
  createMemoryHistory,
  createRouter,
  type Router,
} from "vue-router";

import ScreenListView from "./ScreenListView.vue";
import type { Screen, ScreenSummary } from "./types";

const publishedScreen: ScreenSummary = {
  id: "screen-1",
  name: "运营总览",
  description: "核心经营指标",
  draft_revision: 3,
  published_at: "2026-07-30T04:00:00Z",
  created_at: "2026-07-30T03:00:00Z",
  updated_at: "2026-07-30T05:00:00Z",
};

const copiedScreen: Screen = {
  ...publishedScreen,
  id: "screen-copy",
  name: "运营总览 副本",
  draft_revision: 0,
  published_at: null,
  draft_document: {
    schema_version: 1,
    canvas: { width: 1920, height: 1080, background: {} },
    components: [],
    parameters: [],
    refresh: { mode: "disabled", interval_seconds: null },
    theme: { id: "datapulse-dark", tokens: {} },
  },
  published_document: null,
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function testRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: { template: "<div />" } },
      {
        path: "/studio/screens/:id/edit",
        name: "screen-edit",
        component: { template: "<div />" },
      },
    ],
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("lists, marks, and copies a published screen", async () => {
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/admin/screens" && init?.method === "GET") {
      return Promise.resolve(jsonResponse([publishedScreen]));
    }
    if (
      url === "/api/admin/screens/screen-1/copy" &&
      init?.method === "POST"
    ) {
      return Promise.resolve(jsonResponse(copiedScreen, 201));
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  const router = testRouter();
  await router.push("/");
  await router.isReady();
  const wrapper = mount(ScreenListView, {
    global: { plugins: [router] },
  });
  await flushPromises();

  expect(wrapper.text()).toContain("运营总览");
  expect(wrapper.text()).toContain("核心经营指标");
  expect(wrapper.text()).toContain("已发布");
  expect(wrapper.text()).toContain("最后更新");

  await wrapper.get('[data-action="copy-screen"]').trigger("click");
  await flushPromises();

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/admin/screens/screen-1/copy",
    expect.objectContaining({ method: "POST" }),
  );
  expect(wrapper.text()).toContain("运营总览 副本");
});

test("creates a screen from the empty workspace and opens the editor", async () => {
  const created = { ...copiedScreen, id: "screen-new", name: "销售驾驶舱" };
  let submitted: unknown;
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/admin/screens" && init?.method === "GET") {
        return Promise.resolve(jsonResponse([]));
      }
      if (url === "/api/admin/screens" && init?.method === "POST") {
        submitted = JSON.parse(String(init.body));
        return Promise.resolve(jsonResponse(created, 201));
      }
      throw new Error(`Unexpected request: ${url}`);
    }),
  );
  const router = testRouter();
  await router.push("/");
  await router.isReady();
  const wrapper = mount(ScreenListView, {
    global: { plugins: [router] },
  });
  await flushPromises();

  expect(wrapper.text()).toContain("还没有大屏");
  await wrapper.get('[data-action="open-create-screen"]').trigger("click");
  expect(wrapper.get('[role="dialog"]').text()).toContain("新建大屏");

  await wrapper.get('input[name="screenName"]').setValue("销售驾驶舱");
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  expect(submitted).toEqual({ name: "销售驾驶舱", description: "" });
  expect(router.currentRoute.value.fullPath).toBe(
    "/studio/screens/screen-new/edit",
  );
});

test("creates a screen from a template through the normal draft flow", async () => {
  const created = { ...copiedScreen, id: "screen-template", name: "华东经营分析" };
  let submitted: Record<string, unknown> | undefined;
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/admin/screens" && init?.method === "GET") {
        return Promise.resolve(jsonResponse([]));
      }
      if (url === "/api/admin/screens" && init?.method === "POST") {
        submitted = JSON.parse(String(init.body)) as Record<string, unknown>;
        return Promise.resolve(jsonResponse(created, 201));
      }
      throw new Error(`Unexpected request: ${url}`);
    }),
  );
  const router = testRouter();
  await router.push("/");
  await router.isReady();
  const wrapper = mount(ScreenListView, {
    global: { plugins: [router] },
  });
  await flushPromises();

  await wrapper.get('[data-action="open-template-screen"]').trigger("click");
  expect(wrapper.get('[role="dialog"]').text()).toContain("经营分析");
  await wrapper.get('input[name="templateScreenName"]').setValue("华东经营分析");
  await wrapper.get("button.template-option").trigger("click");
  await wrapper.get('[role="dialog"] .primary-button').trigger("click");
  await flushPromises();

  expect(submitted?.name).toBe("华东经营分析");
  expect(
    (submitted?.draft_document as { components?: unknown[] }).components?.length,
  ).toBeGreaterThanOrEqual(7);
  expect(router.currentRoute.value.fullPath).toBe(
    "/studio/screens/screen-template/edit",
  );
});

test("creates an AI draft only after confirmation and does not publish it", async () => {
  const created = { ...copiedScreen, id: "screen-ai", name: "AI 经营总览" };
  const generatedDocument = {
    schema_version: 1,
    canvas: { width: 1920, height: 1080, background: {} },
    components: [
      {
        id: "kpi-1",
        type: "builtin.kpi",
        frame: { x: 40, y: 40, width: 280, height: 160, z_index: 0 },
        state: { locked: false, hidden: false },
        props: { label: "销售额" },
        style: {},
        data_binding: {
          chart_spec: {
            schema_version: 1,
            dataset_id: "sales",
            dimensions: [],
            measures: [{ field: "amount", aggregation: "sum" }],
            filters: [],
            sort: [],
            limit: 1000,
            visual: { type: "kpi", title: "销售额" },
          },
        },
        interactions: [],
      },
    ],
    parameters: [],
    refresh: { mode: "disabled", interval_seconds: null },
    theme: { id: "datapulse-dark", tokens: {} },
  };
  const requests: Array<{ url: string; method: string; body?: unknown }> = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url === "/api/admin/ai/status" && method === "GET") {
        return Promise.resolve(jsonResponse({ status: "configured", model: "test" }));
      }
      requests.push({
        url,
        method,
        body: init?.body ? JSON.parse(String(init.body)) : undefined,
      });
      if (url === "/api/admin/screens" && method === "GET") {
        return Promise.resolve(jsonResponse([]));
      }
      if (url === "/api/admin/datasets" && method === "GET") {
        return Promise.resolve(
          jsonResponse([
            {
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
                query: { kind: "sql", sql: "select * from sales" },
                fields: [],
                parameters: [],
                cache: { mode: "disabled", ttl_seconds: null },
                refresh: { mode: "manual", interval_seconds: null, cron: null },
                max_rows: 1000,
                timeout_seconds: 30,
              },
            },
          ]),
        );
      }
      if (url === "/api/admin/ai/screen" && method === "POST") {
        return Promise.resolve(
          jsonResponse({
            explanation: "建议使用 1 个 KPI 和 1 张趋势图。",
            warnings: [],
            document: generatedDocument,
          }),
        );
      }
      if (url === "/api/admin/screens/query-document" && method === "POST") {
        return Promise.resolve(
          jsonResponse({
            request_id: "preview-query-1",
            columns: [{ name: "amount", type: "number" }],
            rows: [[350]],
            row_count: 1,
            truncated: false,
            duration_ms: 1,
          }),
        );
      }
      if (url === "/api/admin/screens" && method === "POST") {
        return Promise.resolve(jsonResponse(created, 201));
      }
      throw new Error(`Unexpected request: ${url}`);
    }),
  );
  const router = testRouter();
  await router.push("/");
  await router.isReady();
  const wrapper = mount(ScreenListView, {
    global: { plugins: [router] },
  });
  await flushPromises();

  await wrapper.get('[data-action="open-ai-screen"]').trigger("click");
  await flushPromises();
  expect(wrapper.get('[role="dialog"]').text()).toContain("AI 生成大屏");

  await wrapper.get('input[name="aiScreenName"]').setValue("AI 经营总览");
  await wrapper
    .get('textarea[name="aiScreenQuestion"]')
    .setValue("生成一个经营总览大屏");
  await wrapper.get('input[name="aiScreenDatasets"]').setValue(true);
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  expect(wrapper.text()).toContain("建议使用 1 个 KPI 和 1 张趋势图");
  expect(wrapper.find(".screen-runtime").exists()).toBe(true);
  expect(requests).toContainEqual({
    url: "/api/admin/screens/query-document",
    method: "POST",
    body: {
      document: generatedDocument,
      component_id: "kpi-1",
      parameters: {},
    },
  });
  expect(
    requests.some(
      (request) =>
        request.url === "/api/admin/screens" && request.method === "POST",
    ),
  ).toBe(false);
  expect(requests.some((request) => request.url.endsWith("/publish"))).toBe(
    false,
  );
  await wrapper.get('[data-action="confirm-ai-screen"]').trigger("click");
  await flushPromises();

  expect(requests).toContainEqual({
    url: "/api/admin/ai/screen",
    method: "POST",
    body: {
      question: "生成一个经营总览大屏",
      dataset_ids: ["sales"],
      theme: "dark",
    },
  });
  expect(requests).toContainEqual({
    url: "/api/admin/screens",
    method: "POST",
    body: {
      name: "AI 经营总览",
      description: "",
      draft_document: generatedDocument,
    },
  });
  expect(
    requests.filter(
      (request) =>
        request.url === "/api/admin/screens" && request.method === "POST",
    ),
  ).toHaveLength(1);
  expect(requests.some((request) => request.method === "PATCH")).toBe(false);
  expect(requests.some((request) => request.url.endsWith("/publish"))).toBe(false);
  expect(router.currentRoute.value.fullPath).toBe(
    "/studio/screens/screen-ai/edit",
  );
});

test("deletes a screen only after confirmation", async () => {
  const confirm = vi.fn(() => true);
  vi.stubGlobal("confirm", confirm);
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/admin/screens" && init?.method === "GET") {
        return Promise.resolve(jsonResponse([publishedScreen]));
      }
      if (
        url === "/api/admin/screens/screen-1" &&
        init?.method === "DELETE"
      ) {
        return Promise.resolve(new Response(null, { status: 204 }));
      }
      throw new Error(`Unexpected request: ${url}`);
    }),
  );
  const router = testRouter();
  await router.push("/");
  await router.isReady();
  const wrapper = mount(ScreenListView, {
    global: { plugins: [router] },
  });
  await flushPromises();

  await wrapper.get('[data-action="delete-screen"]').trigger("click");
  await flushPromises();

  expect(confirm).toHaveBeenCalledWith(
    "删除“运营总览”？此操作无法撤销。",
  );
  expect(wrapper.text()).not.toContain("运营总览");
  expect(wrapper.text()).toContain("还没有大屏");
});

test("shows loading and a stable API error", async () => {
  let rejectRequest: ((reason: unknown) => void) | undefined;
  vi.stubGlobal(
    "fetch",
    vi.fn(
      () =>
        new Promise<Response>((_resolve, reject) => {
          rejectRequest = reject;
        }),
    ),
  );
  const router = testRouter();
  await router.push("/");
  await router.isReady();
  const wrapper = mount(ScreenListView, {
    global: { plugins: [router] },
  });

  expect(wrapper.get('[role="status"]').text()).toContain("正在加载大屏");
  rejectRequest?.(new Error("offline"));
  await flushPromises();

  expect(wrapper.text()).toContain("暂时无法加载大屏");
});
