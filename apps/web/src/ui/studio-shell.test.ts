import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, expect, test, vi } from "vitest";

import { useAuthStore } from "../stores/auth";
import StudioShell from "./StudioShell.vue";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("logs the administrator out and returns to the login page", async () => {
  const fetchMock = vi.fn(() => Promise.resolve(new Response(null, { status: 204 })));
  vi.stubGlobal("fetch", fetchMock);
  document.cookie = "datapulse_csrf=studio-logout-token; Path=/";

  const pinia = createPinia();
  setActivePinia(pinia);
  const auth = useAuthStore();
  auth.state = { status: "authenticated", username: "admin" };
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/studio",
        component: StudioShell,
        meta: { title: "数据源" },
      },
      {
        path: "/studio/login",
        component: { template: "<p>登录页</p>" },
      },
      {
        path: "/studio/:section",
        component: { template: "<p>工作区页面</p>" },
      },
    ],
  });
  await router.push("/studio");
  await router.isReady();
  const wrapper = mount(StudioShell, {
    global: {
      plugins: [pinia, router],
      stubs: { RouterView: true },
    },
  });

  await wrapper.get('button[aria-label="退出管理员账号"]').trigger("click");
  await flushPromises();

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/auth/logout",
    expect.objectContaining({ method: "POST" }),
  );
  expect(auth.state).toEqual({ status: "anonymous" });
  expect(router.currentRoute.value.fullPath).toBe("/studio/login");
});
