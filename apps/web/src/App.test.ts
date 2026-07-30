import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, expect, test, vi } from "vitest";
import { createMemoryHistory } from "vue-router";

import App from "./App.vue";
import { createStudioRouter } from "./router";

function jsonResponse(body: object, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("shows the setup page when DataPulse is not initialized", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(jsonResponse({ initialized: false })),
  );
  const pinia = createPinia();
  setActivePinia(pinia);
  const router = createStudioRouter({
    history: createMemoryHistory(),
    pinia,
  });
  await router.push("/studio/datasources");
  await router.isReady();

  const wrapper = mount(App, {
    global: { plugins: [pinia, router] },
  });
  await flushPromises();

  expect(wrapper.get("h1").text()).toBe("初始化 DataPulse");
  expect(
    (wrapper.get('input[name="username"]').element as HTMLInputElement).value,
  ).toBe("admin");
});

test("renders the authenticated Notion-style studio shell", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ initialized: true }))
      .mockResolvedValueOnce(jsonResponse({ username: "admin" })),
  );
  const pinia = createPinia();
  setActivePinia(pinia);
  const router = createStudioRouter({
    history: createMemoryHistory(),
    pinia,
  });
  await router.push("/studio/datasources");
  await router.isReady();

  const wrapper = mount(App, {
    global: { plugins: [pinia, router] },
  });
  await flushPromises();

  expect(wrapper.get('[aria-label="工作区导航"]').text()).toContain("DataPulse");
  expect(wrapper.get('[aria-label="主导航"]').text()).toContain("概览");
  expect(wrapper.get('[aria-label="主导航"]').text()).toContain("数据源");
  expect(wrapper.get('[aria-label="主导航"]').text()).toContain("数据集");
  expect(wrapper.get('[aria-label="主导航"]').text()).toContain("大屏");
  expect(wrapper.get('[aria-label="最近访问"]').text()).toContain("暂无最近项目");
  expect(wrapper.text()).toContain("系统设置");
  expect(wrapper.get('[aria-label="面包屑"]').text()).toContain("数据源");
  expect(wrapper.get("h1").text()).toBe("数据源");
});
