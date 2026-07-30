import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, expect, test, vi } from "vitest";
import {
  createMemoryHistory,
  createRouter,
  type Router,
} from "vue-router";

import type { Screen } from "../screens/types";
import ScreenEditorView from "../screens/ScreenEditorView.vue";
import PlayerView from "./PlayerView.vue";

const screen: Screen = {
  id: "screen-1",
  name: "运营总览",
  description: "",
  draft_revision: 3,
  published_at: null,
  created_at: "2026-07-30T03:00:00Z",
  updated_at: "2026-07-30T03:00:00Z",
  draft_document: {
    schema_version: 1,
    canvas: {
      width: 1920,
      height: 1080,
      background: { color: "#101828" },
    },
    theme: { id: "datapulse-dark", tokens: {} },
    refresh: { mode: "disabled", interval_seconds: null },
    parameters: [],
    components: [
      {
        id: "text-1",
        type: "builtin.text",
        frame: { x: 40, y: 40, width: 320, height: 120, z_index: 0 },
        state: { hidden: false, locked: false },
        props: { text: "这是草稿内容" },
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

function testRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/studio/screens",
        name: "screens",
        component: { template: "<div />" },
      },
      {
        path: "/studio/screens/:id/edit",
        name: "screen-edit",
        component: { template: "<div />" },
      },
      {
        path: "/studio/screens/:id/preview",
        name: "screen-preview",
        component: { template: "<div />" },
      },
    ],
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("loads an authenticated draft into the shared full-screen runtime", async () => {
  const fetchMock = vi.fn().mockResolvedValue(jsonResponse(screen));
  vi.stubGlobal("fetch", fetchMock);
  const router = testRouter();
  await router.push("/studio/screens/screen-1/preview");
  await router.isReady();

  const wrapper = mount(PlayerView, {
    props: { mode: "preview", screenId: "screen-1" },
    global: { plugins: [router] },
  });
  await flushPromises();

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/admin/screens/screen-1",
    expect.objectContaining({ method: "GET" }),
  );
  expect(wrapper.get(".screen-runtime").attributes("data-mode")).toBe(
    "preview",
  );
  expect(wrapper.text()).toContain("这是草稿内容");
  expect(wrapper.text()).toContain("草稿预览");
  wrapper.unmount();
});

test("requires explicit confirmation before publishing the saved revision", async () => {
  let publishPayload: unknown;
  const published = {
    ...screen,
    published_document: screen.draft_document,
    published_at: "2026-07-30T06:00:00Z",
  };
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (
        url === "/api/admin/screens/screen-1" &&
        init?.method === "GET"
      ) {
        return Promise.resolve(jsonResponse(screen));
      }
      if (
        url === "/api/admin/screens/screen-1/publish" &&
        init?.method === "POST"
      ) {
        publishPayload = JSON.parse(String(init.body));
        return Promise.resolve(jsonResponse(published));
      }
      throw new Error(`Unexpected request: ${url}`);
    }),
  );
  const pinia = createPinia();
  setActivePinia(pinia);
  const router = testRouter();
  await router.push("/studio/screens/screen-1/edit");
  await router.isReady();
  const wrapper = mount(ScreenEditorView, {
    global: {
      plugins: [pinia, router],
      stubs: {
        ComponentLibrary: true,
        InspectorPanel: true,
        LayersPanel: true,
        ScreenCanvas: true,
      },
    },
  });
  await flushPromises();

  await wrapper.get('[data-action="publish-screen"]').trigger("click");
  await flushPromises();

  expect(wrapper.text()).toContain(
    "发布将覆盖当前线上大屏，且无法直接回滚。",
  );
  expect(wrapper.text()).toContain("如需备份，请先复制大屏。");
  expect(publishPayload).toBeUndefined();

  await wrapper.get('[data-action="confirm-publish"]').trigger("click");
  await flushPromises();

  expect(publishPayload).toEqual({ expected_revision: 3 });
  expect(wrapper.text()).toContain("发布成功");
});
