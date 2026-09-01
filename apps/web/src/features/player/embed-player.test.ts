import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";
import {
  createMemoryHistory,
  createRouter,
  type Router,
} from "vue-router";

import type { JsonValue } from "../query/types";
import {
  createEmbedBridge,
  type EmbedBridge,
} from "./embedBridge";
import PlayerView from "./PlayerView.vue";

const HOST_ORIGIN = "https://host.example.com";

const embedDocument = {
  schema_version: 1 as const,
  canvas: {
    width: 1920,
    height: 1080,
    background: { color: "#101828" },
  },
  theme: { id: "datapulse-dark", tokens: {} },
  refresh: { mode: "disabled" as const, interval_seconds: null },
  parameters: [
    {
      id: "region",
      name: "region",
      data_type: "string" as const,
      default: "east",
      mutable: true,
      allowed_values: ["east", "west"],
    },
    {
      id: "year",
      name: "year",
      data_type: "integer" as const,
      default: 2026,
      mutable: false,
      allowed_values: [],
    },
  ],
  components: [
    {
      id: "text-1",
      type: "builtin.text",
      frame: { x: 40, y: 40, width: 320, height: 120, z_index: 0 },
      state: { hidden: false, locked: false },
      props: { text: "嵌入播放内容" },
      style: {},
      data_binding: {},
      interactions: [],
    },
    {
      id: "kpi-1",
      type: "builtin.kpi",
      frame: { x: 380, y: 40, width: 280, height: 160, z_index: 1 },
      state: { hidden: false, locked: false },
      props: { label: "销售额" },
      style: {},
      data_binding: { chart_spec: { dataset_id: "sales" } },
      interactions: [],
    },
  ],
};

function embedRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/embed/:screenId",
        component: PlayerView,
        props: (route) => ({
          mode: "embed",
          screenId: String(route.params.screenId),
        }),
      },
    ],
  });
}

function dispatchHostMessage(data: unknown, origin = HOST_ORIGIN): void {
  window.dispatchEvent(
    new MessageEvent("message", {
      data,
      origin,
      source: window.parent,
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("iframe bridge validates parent Origin and correlates replies", async () => {
  let parameters: Record<string, JsonValue> = { region: "east", year: 2026 };
  const postMessage = vi
    .spyOn(window.parent, "postMessage")
    .mockImplementation(() => undefined);
  const setParameters = vi.fn((values: Record<string, JsonValue>) => {
    if ("year" in values) {
      throw Object.assign(new Error("Immutable parameter."), {
        code: "EMBED_PARAMETER_DENIED",
      });
    }
    parameters = { ...parameters, ...values };
  });
  const bridge = createEmbedBridge({
    allowedOrigin: HOST_ORIGIN,
    instanceId: "embed-1",
    refresh: vi.fn(),
    setParameters,
    getParameters: () => parameters,
    fullscreen: vi.fn(),
  });
  bridge.ready();

  expect(postMessage).toHaveBeenLastCalledWith(
    {
      type: "ready",
      protocol_version: 1,
      instance_id: "embed-1",
    },
    HOST_ORIGIN,
  );

  dispatchHostMessage(
    {
      type: "setParameters",
      instance_id: "embed-1",
      request_id: "wrong-origin",
      parameters: { region: "west" },
    },
    "https://evil.example.com",
  );
  expect(setParameters).not.toHaveBeenCalled();

  dispatchHostMessage({
    type: "setParameters",
    instance_id: "embed-1",
    request_id: "set-1",
    parameters: { region: "west" },
  });
  await flushPromises();
  expect(setParameters).toHaveBeenCalledWith({ region: "west" });
  expect(postMessage).toHaveBeenLastCalledWith(
    {
      type: "ack",
      instance_id: "embed-1",
      request_id: "set-1",
    },
    HOST_ORIGIN,
  );

  dispatchHostMessage({
    type: "getParameters",
    instance_id: "embed-1",
    request_id: "get-1",
  });
  await flushPromises();
  expect(postMessage).toHaveBeenLastCalledWith(
    {
      type: "parameters",
      instance_id: "embed-1",
      request_id: "get-1",
      parameters: { region: "west", year: 2026 },
    },
    HOST_ORIGIN,
  );

  dispatchHostMessage({
    type: "setParameters",
    instance_id: "embed-1",
    request_id: "set-immutable",
    parameters: { year: 2027 },
  });
  await flushPromises();
  expect(postMessage).toHaveBeenLastCalledWith(
    expect.objectContaining({
      type: "error",
      code: "EMBED_PARAMETER_DENIED",
      request_id: "set-immutable",
    }),
    HOST_ORIGIN,
  );

  bridge.destroy();
  dispatchHostMessage({
    type: "getParameters",
    instance_id: "embed-1",
    request_id: "after-destroy",
  });
  await flushPromises();
  expect(postMessage).not.toHaveBeenCalledWith(
    expect.objectContaining({ request_id: "after-destroy" }),
    HOST_ORIGIN,
  );
});

test("embed player scrubs the ticket and uses Bearer-only runtime APIs", async () => {
  const fetchMock = vi.fn(
    (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/embed/screens/screen-1") {
        expect(new Headers(init?.headers).get("Authorization")).toBe(
          "Bearer short-ticket",
        );
        expect(init?.credentials).toBe("omit");
        return Promise.resolve(
          new Response(
            JSON.stringify({
              id: "screen-1",
              name: "运营总览",
              document: embedDocument,
              allowed_origin: HOST_ORIGIN,
              parameters: { region: "west", year: 2026 },
              mutable_parameters: ["region"],
              expires_at: "2026-07-30T18:00:00Z",
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      if (url === "/api/embed/screens/screen-1/query") {
        expect(new Headers(init?.headers).get("Authorization")).toBe(
          "Bearer short-ticket",
        );
        expect(JSON.parse(String(init?.body))).toEqual({
          component_id: "kpi-1",
          parameters: { region: "west" },
        });
        return Promise.resolve(
          new Response(
            JSON.stringify({
              request_id: "embed-query",
              columns: [{ name: "amount", data_type: "number" }],
              rows: [[500]],
              row_count: 1,
              truncated: false,
              duration_ms: 1,
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      throw new Error(`Unexpected request: ${url}`);
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  const replaceState = vi.spyOn(window.history, "replaceState");
  const postMessage = vi
    .spyOn(window.parent, "postMessage")
    .mockImplementation(() => undefined);
  const router = embedRouter();
  await router.push(
    "/embed/screen-1?ticket=short-ticket&instance_id=embed-1",
  );
  await router.isReady();

  const wrapper = mount(PlayerView, {
    props: { mode: "embed", screenId: "screen-1" },
    global: { plugins: [router] },
  });
  await flushPromises();

  expect(replaceState).toHaveBeenCalledWith(
    window.history.state,
    "",
    "/embed/screen-1",
  );
  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(fetchMock.mock.calls[0]?.[0]).not.toContain("short-ticket");
  expect(wrapper.get(".screen-runtime").attributes("data-mode")).toBe(
    "embed",
  );
  expect(wrapper.text()).toContain("嵌入播放内容");
  expect(postMessage).toHaveBeenCalledWith(
    {
      type: "ready",
      protocol_version: 1,
      instance_id: "embed-1",
    },
    HOST_ORIGIN,
  );
  expect(
    fetchMock.mock.calls.some(([url]) => String(url).includes("/api/auth/")),
  ).toBe(false);
  wrapper.unmount();
});

test("direct iframe embeds work without an instance_id query parameter", async () => {
  const fetchMock = vi.fn(
    (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/embed/screens/screen-1") {
        expect(new Headers(init?.headers).get("Authorization")).toBe(
          "Bearer short-ticket",
        );
        return Promise.resolve(
          new Response(
            JSON.stringify({
              id: "screen-1",
              name: "运营总览",
              document: embedDocument,
              allowed_origin: HOST_ORIGIN,
              parameters: { region: "west", year: 2026 },
              mutable_parameters: ["region"],
              expires_at: "2026-07-30T18:00:00Z",
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      if (url === "/api/embed/screens/screen-1/query") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              request_id: "embed-query",
              columns: [{ name: "amount", data_type: "number" }],
              rows: [[500]],
              row_count: 1,
              truncated: false,
              duration_ms: 1,
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      throw new Error(`Unexpected request: ${url}`);
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  const replaceState = vi.spyOn(window.history, "replaceState");
  const postMessage = vi
    .spyOn(window.parent, "postMessage")
    .mockImplementation(() => undefined);
  const router = embedRouter();
  await router.push("/embed/screen-1?ticket=short-ticket");
  await router.isReady();

  const wrapper = mount(PlayerView, {
    props: { mode: "embed", screenId: "screen-1" },
    global: { plugins: [router] },
  });
  await flushPromises();

  expect(replaceState).toHaveBeenCalledWith(
    window.history.state,
    "",
    "/embed/screen-1",
  );
  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(wrapper.get(".screen-runtime").attributes("data-mode")).toBe(
    "embed",
  );
  const readyMessage = postMessage.mock.calls.find(
    ([message]) =>
      typeof message === "object" &&
      message !== null &&
      "type" in message &&
      message.type === "ready",
  )?.[0];
  expect(readyMessage).toEqual(
    expect.objectContaining({
      type: "ready",
      protocol_version: 1,
      instance_id: expect.any(String),
    }),
  );
  expect((readyMessage as { instance_id: string }).instance_id).not.toBe("");
  wrapper.unmount();
});

test("bridge reports ticket expiry as a stable host error", () => {
  const postMessage = vi
    .spyOn(window.parent, "postMessage")
    .mockImplementation(() => undefined);
  const bridge: EmbedBridge = createEmbedBridge({
    allowedOrigin: HOST_ORIGIN,
    instanceId: "embed-1",
    refresh: vi.fn(),
    setParameters: vi.fn(),
    getParameters: () => ({}),
    fullscreen: vi.fn(),
  });

  bridge.reportError(
    Object.assign(new Error("Ticket expired."), {
      code: "EMBED_TICKET_EXPIRED",
    }),
  );

  expect(postMessage).toHaveBeenCalledWith(
    {
      type: "error",
      instance_id: "embed-1",
      code: "EMBED_TICKET_EXPIRED",
      message: "Ticket expired.",
    },
    HOST_ORIGIN,
  );
  bridge.destroy();
});
