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
