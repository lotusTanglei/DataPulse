import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { expect, test } from "vitest";

import EditorToolbar from "./EditorToolbar.vue";

test("toolbar exposes manual data refresh and disables invalid layout actions", async () => {
  const wrapper = mount(EditorToolbar, {
    global: {
      plugins: [createPinia()],
      stubs: { RouterLink: { template: "<a><slot /></a>" } },
    },
    props: {
      saveLabel: "已保存",
      zoom: 0.5,
      selectionCount: 1,
    },
  });

  expect(wrapper.get('[aria-label="左对齐"]').attributes("disabled")).toBeDefined();
  expect(wrapper.get('[aria-label="水平等间距"]').attributes("disabled")).toBeDefined();
  await wrapper.get('[aria-label="刷新数据"]').trigger("click");
  expect(wrapper.emitted("refresh")).toHaveLength(1);
});
