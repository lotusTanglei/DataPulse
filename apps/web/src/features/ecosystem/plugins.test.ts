import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import ComponentHost from "../runtime/ComponentHost.vue";
import { defaultComponentRegistry } from "../runtime/registry";
import { createPluginRegistry, schemaProperties } from "./plugins";
import type { CatalogPackage } from "./types";

export function metricPackage(version = "1.0.0"): CatalogPackage {
  return {
    kind: "plugin",
    id: "org.example.metrics",
    version,
    name: "Metrics",
    description: "",
    license: "MIT",
    source: "local",
    compatible_api: ">=1,<2",
    sha256: "a".repeat(64),
    installed_at: "2026-09-21T00:00:00Z",
    files: [],
    manifest: {
      id: "org.example.metrics",
      version,
      name: "Metrics",
      compatible_api: ">=1,<2",
      entry: "index.mjs",
      components: [
        {
          type: "org.example.metric",
          name: "Metric",
          category: "Metrics",
          default_props: { label: "Total" },
          property_schema: {
            type: "object",
            properties: { label: { type: "string" } },
            required: ["label"],
          },
          data_schema: {},
        },
      ],
    },
  };
}

const instance = {
  id: "metric",
  type: "org.example.metric",
  frame: { x: 0, y: 0, width: 100, height: 100 },
  props: { label: "Hello" },
};

describe("trusted plugin runtime", () => {
  it("keeps exact versions in independent registries without modifying builtins", async () => {
    const moduleFor = (version: string) => ({
      default: {
        apiVersion: 1,
        components: {
          "org.example.metric": {
            mount(element: HTMLElement) {
              element.textContent = version;
              return { update() {}, destroy() {} };
            },
          },
        },
      },
    });
    const first = await createPluginRegistry([metricPackage()], async () =>
      moduleFor("one"),
    );
    const second = await createPluginRegistry(
      [metricPackage("2.0.0")],
      async () => moduleFor("two"),
    );
    const mountHost = (registry: typeof first) =>
      mount(ComponentHost, {
        props: {
          instance,
          definition: registry.get(instance.type),
          loadAsset: async () => "",
          theme: {},
          queryState: { status: "idle", result: null, error: null },
          mode: "preview",
        },
      });
    const a = mountHost(first),
      b = mountHost(second);
    await nextTick();
    expect(a.text()).toContain("one");
    expect(b.text()).toContain("two");
    expect(defaultComponentRegistry.has(instance.type)).toBe(false);
    a.unmount();
    b.unmount();
  });
  it("updates with query results and aborts and destroys on unmount", async () => {
    const update = vi.fn(),
      destroy = vi.fn();
    let signal: AbortSignal | undefined;
    const registry = await createPluginRegistry(
      [metricPackage()],
      async () => ({
        default: {
          apiVersion: 1,
          components: {
            [instance.type]: {
              mount(_element: HTMLElement, context: { signal: AbortSignal }) {
                signal = context.signal;
                return { update, destroy };
              },
            },
          },
        },
      }),
    );
    const wrapper = mount(ComponentHost, {
      props: {
        instance,
        definition: registry.get(instance.type),
        loadAsset: async () => "",
        theme: { accent: "red" },
        queryState: { status: "idle", result: null, error: null },
      },
    });
    await nextTick();
    await wrapper.setProps({
      instance: { ...instance, props: { label: "Updated" } },
    });
    expect(update).toHaveBeenLastCalledWith(
      expect.objectContaining({ props: { label: "Updated" } }),
    );
    wrapper.unmount();
    expect(destroy).toHaveBeenCalledOnce();
    expect(signal?.aborted).toBe(true);
  });
  it("isolates module and render failures to their component", async () => {
    const registry = await createPluginRegistry([metricPackage()], async () => {
      throw new Error("bad module");
    });
    expect(registry.has("builtin.text")).toBe(true);
    const wrapper = mount(ComponentHost, {
      props: {
        instance,
        definition: registry.get(instance.type),
        loadAsset: async () => "",
        theme: {},
        queryState: { status: "idle", result: null, error: null },
      },
    });
    await nextTick();
    expect(wrapper.text()).toContain("组件渲染失败");
    wrapper.unmount();
  });
  it("does not mount props rejected by the declared schema", async () => {
    const render = vi.fn();
    const registry = await createPluginRegistry(
      [metricPackage()],
      async () => ({
        default: {
          apiVersion: 1,
          components: { [instance.type]: { mount: render } },
        },
      }),
    );
    const wrapper = mount(ComponentHost, {
      props: {
        instance: { ...instance, props: { label: 4 } },
        definition: registry.get(instance.type),
        loadAsset: async () => "",
        theme: {},
        queryState: { status: "idle", result: null, error: null },
      },
    });
    await nextTick();
    expect(render).not.toHaveBeenCalled();
    wrapper.unmount();
  });
  it("derives scalar property fields from JSON Schema", () => {
    expect(
      schemaProperties(
        {
          type: "object",
          properties: {
            label: { type: "string", title: "Label" },
            count: { type: "integer", minimum: 0, maximum: 20 },
            enabled: { type: "boolean" },
          },
        },
        {},
      ),
    ).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          name: "count",
          editor: "number",
          min: 0,
          max: 20,
          step: 1,
        }),
      ]),
    );
  });
});
