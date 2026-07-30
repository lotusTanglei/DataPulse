import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";
import {
  createMemoryHistory,
  createRouter,
  type Router,
} from "vue-router";

import type { Screen } from "../screens/types";
import PlayerView from "./PlayerView.vue";

const publishedDocument: Screen["draft_document"] = {
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
      props: { text: "独立播放内容" },
      style: {},
      data_binding: {},
      interactions: [],
    },
  ],
};

function standaloneRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/play/:screenId",
        component: PlayerView,
        props: (route) => ({
          mode: "standalone",
          screenId: String(route.params.screenId),
        }),
      },
    ],
  });
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("exchanges and removes the display key before loading published content", async () => {
  const requests: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      requests.push(`${init?.method ?? "GET"} ${url}`);
      if (
        url === "/api/player/screens/screen-1/session" &&
        init?.method === "POST"
      ) {
        return Promise.resolve(new Response(null, { status: 204 }));
      }
      if (
        url === "/api/player/screens/screen-1" &&
        init?.method === "GET"
      ) {
        return Promise.resolve(
          jsonResponse({
            id: "screen-1",
            name: "运营总览",
            document: publishedDocument,
          }),
        );
      }
      throw new Error(`Unexpected request: ${url}`);
    }),
  );
  const replaceState = vi.spyOn(window.history, "replaceState");
  const router = standaloneRouter();
  await router.push("/play/screen-1?key=display-key");
  await router.isReady();

  const wrapper = mount(PlayerView, {
    props: { mode: "standalone", screenId: "screen-1" },
    global: { plugins: [router] },
  });
  await flushPromises();

  expect(replaceState).toHaveBeenCalledWith(
    window.history.state,
    "",
    "/play/screen-1",
  );
  expect(requests).toEqual([
    "POST /api/player/screens/screen-1/session",
    "GET /api/player/screens/screen-1",
  ]);
  expect(requests.some((request) => request.includes("/api/auth/"))).toBe(
    false,
  );
  expect(wrapper.get(".screen-runtime").attributes("data-mode")).toBe(
    "standalone",
  );
  expect(wrapper.text()).toContain("独立播放内容");
  expect(wrapper.find('[aria-label="工作区导航"]').exists()).toBe(false);
  wrapper.unmount();
});

test("renders a neutral full-page error for invalid standalone access", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      jsonResponse(
        {
          error: {
            code: "DISPLAY_ACCESS_DENIED",
            message: "invalid",
            request_id: "request-1",
            field_errors: [],
          },
        },
        401,
      ),
    ),
  );
  const router = standaloneRouter();
  await router.push("/play/screen-1?key=invalid");
  await router.isReady();

  const wrapper = mount(PlayerView, {
    props: { mode: "standalone", screenId: "screen-1" },
    global: { plugins: [router] },
  });
  await flushPromises();

  expect(wrapper.text()).toContain("无法播放此大屏");
  expect(wrapper.text()).not.toContain("request-1");
  expect(wrapper.find('[aria-label="工作区导航"]').exists()).toBe(false);
});
