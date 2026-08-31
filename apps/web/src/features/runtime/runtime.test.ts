import { flushPromises, mount } from "@vue/test-utils";
import { defineComponent, markRaw } from "vue";
import { expect, test, vi } from "vitest";

import type { DashboardDocument } from "../../contracts";
import type { QueryResult } from "../query/types";
import ComponentHost from "./ComponentHost.vue";
import { createParameterState, ParameterValidationError } from "./parameters";
import { ComponentRegistry, defaultComponentRegistry } from "./registry";
import ScreenRuntime from "./ScreenRuntime.vue";
import { resolveTheme } from "./theme";
import type { ComponentDefinition } from "./types";

const StubComponent = defineComponent({
  name: "StubRuntimeComponent",
  template: "<div />",
});

test("registers and resolves component definitions without silent duplicates", () => {
  const registry = new ComponentRegistry();
  const definition = {
    type: "builtin.text" as const,
    label: "文本",
    defaultFrame: { width: 320, height: 120 },
    defaultProps: { text: "文本" },
    dataCapability: "none" as const,
    component: markRaw(StubComponent),
  };

  registry.register(definition);

  expect(registry.get("builtin.text")).toBe(definition);
  expect(registry.list()).toEqual([definition]);
  expect(() => registry.register(definition)).toThrow(
    "Component type is already registered",
  );
});

test("validates defaults, initial values, allowed values, and host mutability", () => {
  const parameters: NonNullable<DashboardDocument["parameters"]> = [
    {
      id: "region",
      name: "region",
      data_type: "string",
      default: "east",
      mutable: true,
      allowed_values: ["east", "west"],
    },
    {
      id: "year",
      name: "year",
      data_type: "integer",
      default: 2026,
      mutable: false,
    },
  ];
  const state = createParameterState(parameters, { region: "west" });

  expect(state.values()).toEqual({ region: "west", year: 2026 });
  state.set("region", "east", "host");
  expect(state.get("region")).toBe("east");
  expect(() => state.set("region", "north", "host")).toThrow(
    ParameterValidationError,
  );
  expect(() => state.set("year", 2027, "host")).toThrow(
    "cannot be changed by the host",
  );
  expect(() => state.set("missing", "value")).toThrow(
    ParameterValidationError,
  );
});

test("applies host parameter batches atomically", () => {
  const document: DashboardDocument = {
    schema_version: 1,
    canvas: { width: 1920, height: 1080 },
    parameters: [
      {
        id: "region",
        name: "region",
        data_type: "string",
        default: "east",
        mutable: true,
        allowed_values: ["east", "west"],
      },
      {
        id: "year",
        name: "year",
        data_type: "integer",
        default: 2026,
        mutable: false,
      },
    ],
    components: [],
  };
  const wrapper = mount(ScreenRuntime, {
    props: {
      document,
      loadAsset: vi.fn(),
      mode: "embed",
      queryComponent: vi.fn(),
    },
  });
  const runtime = wrapper.vm as unknown as {
    getParameters(): Record<string, unknown>;
    setParameters(
      values: Record<string, string | number>,
      source: "host",
    ): void;
  };

  expect(() =>
    runtime.setParameters({ region: "west", year: 2027 }, "host"),
  ).toThrow("cannot be changed by the host");
  expect(runtime.getParameters()).toEqual({ region: "east", year: 2026 });

  runtime.setParameters({ region: "west" }, "host");
  expect(runtime.getParameters()).toEqual({ region: "west", year: 2026 });
  expect(wrapper.emitted("parametersChange")).toEqual([
    [{ region: "west", year: 2026 }],
  ]);
  wrapper.unmount();
});

test("maps primitive theme tokens to scoped CSS custom properties", () => {
  expect(
    resolveTheme({
      id: "brand",
      tokens: {
        accent: "#2563eb",
        "panel.background": "#ffffff",
        ignored: { nested: true },
      },
    }),
  ).toEqual({
    "--dp-accent": "#2563eb",
    "--dp-panel-background": "#ffffff",
    "--screen-accent": "#2563eb",
    "--screen-panel-background": "#ffffff",
  });
});

test("contains a component render failure inside its own host", async () => {
  const brokenDefinition: ComponentDefinition = {
    type: "builtin.text",
    label: "异常组件",
    defaultFrame: { width: 320, height: 120 },
    defaultProps: {},
    dataCapability: "none",
    component: markRaw(
      defineComponent({
        setup() {
          throw new Error("render failed");
        },
        template: "<div />",
      }),
    ),
  };
  const wrapper = mount(ComponentHost, {
    props: {
      definition: brokenDefinition,
      instance: {
        id: "broken-text",
        type: "builtin.text",
        frame: { x: 0, y: 0, width: 320, height: 120 },
      },
      loadAsset: vi.fn(),
      queryState: { status: "idle", result: null, error: null },
      theme: {},
    },
  });

  await flushPromises();

  expect(wrapper.get('[role="status"]').text()).toBe("组件渲染失败");
});

test("applies persisted component appearance to the runtime host", () => {
  const definition: ComponentDefinition = {
    type: "builtin.text",
    label: "文本",
    defaultFrame: { width: 320, height: 120 },
    defaultProps: {},
    dataCapability: "none",
    component: markRaw(StubComponent),
  };
  const wrapper = mount(ComponentHost, {
    props: {
      definition,
      instance: {
        id: "styled-text",
        type: "builtin.text",
        frame: { x: 0, y: 0, width: 320, height: 120 },
        style: {
          background_color: "#111827",
          text_color: "#f8fafc",
          border_color: "#3b82f6",
          border_width: 2,
          border_radius: 8,
          opacity: 0.8,
        },
      },
      loadAsset: vi.fn(),
      queryState: { status: "idle", result: null, error: null },
      theme: {},
    },
  });

  expect(wrapper.get(".component-host").attributes("style")).toContain(
    "background-color: #111827",
  );
  expect(wrapper.get(".component-host").attributes("style")).toContain(
    "border: 2px solid #3b82f6",
  );
  expect(wrapper.get(".component-host").attributes("style")).toContain(
    "opacity: 0.8",
  );
});

test("resolves default component surfaces from the panel theme token", () => {
  const definition = defaultComponentRegistry.get("builtin.kpi")!;
  const wrapper = mount(ComponentHost, {
    props: {
      definition,
      instance: {
        id: "themed-kpi",
        type: "builtin.kpi",
        frame: { x: 0, y: 0, width: 280, height: 160 },
      },
      loadAsset: vi.fn(),
      queryState: { status: "idle", result: null, error: null },
      theme: { panel_background: "#112233" },
    },
  });

  const style = wrapper.get(".component-host").attributes("style");
  expect(style).toContain("--screen-panel-background: #112233");
  expect(style).toContain(
    "--screen-component-surface: var(--screen-panel-background, #0b1b2b)",
  );
});

test("loads bound components through one unified screen runtime", async () => {
  const registry = new ComponentRegistry().register({
    type: "builtin.kpi",
    label: "指标",
    defaultFrame: { width: 240, height: 120 },
    defaultProps: {},
    dataCapability: "single",
    component: StubComponent,
  });
  const binding = {
    chart_spec: { dataset_id: "sales", visual: { type: "kpi" } },
  };
  const document: DashboardDocument = {
    schema_version: 1,
    canvas: { width: 1920, height: 1080, background: { color: "#101828" } },
    components: [
      {
        id: "kpi-a",
        type: "builtin.kpi",
        frame: { x: 0, y: 0, width: 240, height: 120 },
        data_binding: binding,
      },
      {
        id: "kpi-b",
        type: "builtin.kpi",
        frame: { x: 260, y: 0, width: 240, height: 120 },
        data_binding: binding,
      },
    ],
    parameters: [],
  };
  const queryComponent = vi.fn().mockResolvedValue({
    request_id: "shared",
    columns: [],
    rows: [],
    row_count: 0,
    truncated: false,
    duration_ms: 1,
  });
  const wrapper = mount(ScreenRuntime, {
    props: {
      document,
      loadAsset: vi.fn(),
      mode: "editor",
      queryComponent,
      registry,
    },
  });

  await flushPromises();

  expect(queryComponent).toHaveBeenCalledTimes(1);
  expect(wrapper.findAll("[data-component-id]")).toHaveLength(2);
  expect(wrapper.get(".screen-runtime__canvas").attributes("style")).toContain(
    "background-color: #101828",
  );
  wrapper.unmount();
});

test("refresh cancellation does not surface as a component error", async () => {
  const registry = new ComponentRegistry().register({
    type: "builtin.kpi",
    label: "指标",
    defaultFrame: { width: 240, height: 120 },
    defaultProps: {},
    dataCapability: "single",
    component: StubComponent,
  });
  const document: DashboardDocument = {
    schema_version: 1,
    canvas: { width: 1920, height: 1080 },
    components: [
      {
        id: "kpi-a",
        type: "builtin.kpi",
        frame: { x: 0, y: 0, width: 240, height: 120 },
        data_binding: { chart_spec: { dataset_id: "sales" } },
      },
    ],
  };
  let call = 0;
  const queryComponent = vi.fn(
    (
      _componentId: string,
      _parameters: Record<string, unknown>,
      signal?: AbortSignal,
    ) => {
      call += 1;
      if (call > 1) {
        return Promise.resolve({
          request_id: "refreshed",
          columns: [],
          rows: [],
          row_count: 0,
          truncated: false,
          duration_ms: 1,
        });
      }
      return new Promise<QueryResult>((_, reject) => {
        signal?.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      });
    },
  );
  const wrapper = mount(ScreenRuntime, {
    props: {
      document,
      loadAsset: vi.fn(),
      mode: "embed",
      queryComponent,
      registry,
    },
  });
  await flushPromises();

  await (
    wrapper.vm as unknown as { refresh(): Promise<void> }
  ).refresh();
  await flushPromises();

  expect(wrapper.emitted("error")).toBeUndefined();
  wrapper.unmount();
});
