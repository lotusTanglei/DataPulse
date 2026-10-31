import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { defaultComponentRegistry } from "../../runtime/registry";
import ComponentLibrary from "./ComponentLibrary.vue";
import { useScreenEditorStore } from "./store";

beforeEach(() => {
  setActivePinia(createPinia());
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response("[]", {
    headers: { "Content-Type": "application/json" },
  }))));
});

afterEach(() => vi.unstubAllGlobals());

test("renders one visual preview and icon for every registered component", () => {
  const wrapper = mount(ComponentLibrary);
  const definitions = defaultComponentRegistry.list();

  expect(wrapper.findAll("[data-preview]")).toHaveLength(definitions.length);
  expect(wrapper.findAll(".component-library__icon")).toHaveLength(definitions.length);
  expect(wrapper.text()).toContain("基础与装饰");
  expect(wrapper.text()).toContain("指标与状态");
  expect(wrapper.text()).toContain("图表");
  expect(wrapper.text()).toContain("列表与分析");
  expect(wrapper.text()).toContain("地图");
});

test("binds a versioned component instance to its contract version", async () => {
  const store = useScreenEditorStore();
  store.document = {
    schema_version: 1,
    canvas: { width: 1920, height: 1080 },
    components: [],
  };
  const dispatch = vi.spyOn(store, "dispatch").mockImplementation(() => undefined);
  const wrapper = mount(ComponentLibrary);
  const definition = defaultComponentRegistry.get("builtin.relation_graph")!;
  expect(definition.contract).toBeDefined();
  const contract = definition.contract!;
  const button = wrapper.findAll("button").find((item) =>
    item.text().includes(definition.label),
  )!;

  await button.trigger("click");

  expect(dispatch).toHaveBeenCalledWith(expect.objectContaining({
    type: "add_component",
    component: expect.objectContaining({
      type: definition.type,
      contract_version: contract.version,
    }),
  }));
});
