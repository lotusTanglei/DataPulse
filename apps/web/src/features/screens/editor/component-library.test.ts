import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, expect, test } from "vitest";

import { defaultComponentRegistry } from "../../runtime/registry";
import ComponentLibrary from "./ComponentLibrary.vue";

beforeEach(() => {
  setActivePinia(createPinia());
});

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
