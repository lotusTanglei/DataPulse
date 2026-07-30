import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { createMemoryHistory } from "vue-router";

import { createStudioRouter } from "../../router";
import { useAuthStore } from "../../stores/auth";
import App from "../../App.vue";

function jsonResponse(body: object, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  setActivePinia(createPinia());
  document.cookie = "datapulse_csrf=; Max-Age=0; Path=/";
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("restores an authenticated session once across concurrent resolves", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(jsonResponse({ initialized: true }))
    .mockResolvedValueOnce(jsonResponse({ username: "admin" }));
  vi.stubGlobal("fetch", fetchMock);
  const auth = useAuthStore();

  const [first, second] = await Promise.all([auth.resolve(), auth.resolve()]);

  expect(first).toEqual({ status: "authenticated", username: "admin" });
  expect(second).toBe(first);
  expect(auth.state).toEqual({ status: "authenticated", username: "admin" });
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

test("setup sends credentials and transitions directly to authenticated", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValue(jsonResponse({ username: "owner" }, 201));
  vi.stubGlobal("fetch", fetchMock);
  const auth = useAuthStore();

  await auth.setup({
    code: "setup-code",
    username: "owner",
    password: "long-enough-password",
  });

  expect(auth.state).toEqual({ status: "authenticated", username: "owner" });
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/auth/setup",
    expect.objectContaining({
      method: "POST",
      credentials: "same-origin",
      body: JSON.stringify({
        code: "setup-code",
        username: "owner",
        password: "long-enough-password",
      }),
    }),
  );
});

test("logout sends CSRF and clears the authenticated state", async () => {
  document.cookie = "datapulse_csrf=logout-token; Path=/";
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(new Response(null, { status: 204 }))
    .mockResolvedValueOnce(new Response(null, { status: 204 }));
  vi.stubGlobal("fetch", fetchMock);
  const auth = useAuthStore();
  await auth.login({ username: "admin", password: "password" });

  await auth.logout();

  const logoutInit = fetchMock.mock.calls[1]?.[1] as RequestInit;
  expect(new Headers(logoutInit.headers).get("X-CSRF-Token")).toBe("logout-token");
  expect(auth.state).toEqual({ status: "anonymous" });
});

test("redirects an uninitialized installation to setup", async () => {
  const pinia = createPinia();
  setActivePinia(pinia);
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(jsonResponse({ initialized: false })),
  );
  const router = createStudioRouter({
    history: createMemoryHistory(),
    pinia,
  });

  await router.push("/studio/datasources");
  await router.isReady();

  expect(router.currentRoute.value.fullPath).toBe("/studio/setup");
});

test("redirects an initialized anonymous session to login", async () => {
  const pinia = createPinia();
  setActivePinia(pinia);
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ initialized: true }))
      .mockResolvedValueOnce(
        jsonResponse(
          {
            error: {
              code: "AUTH_REQUIRED",
              message: "Authentication is required.",
              request_id: "anonymous-1",
              field_errors: [],
            },
          },
          401,
        ),
      ),
  );
  const router = createStudioRouter({
    history: createMemoryHistory(),
    pinia,
  });

  await router.push("/studio/datasets");
  await router.isReady();

  expect(router.currentRoute.value.fullPath).toBe("/studio/login");
});

test.each(["/studio/setup", "/studio/login"])(
  "redirects authenticated users away from %s",
  async (path) => {
    const pinia = createPinia();
    setActivePinia(pinia);
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(jsonResponse({ initialized: true }))
        .mockResolvedValueOnce(jsonResponse({ username: "admin" })),
    );
    const router = createStudioRouter({
      history: createMemoryHistory(),
      pinia,
    });

    await router.push(path);
    await router.isReady();

    expect(router.currentRoute.value.fullPath).toBe("/studio/datasources");
  },
);

test("setup validates password confirmation before creating the administrator", async () => {
  const pinia = createPinia();
  setActivePinia(pinia);
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(jsonResponse({ initialized: false }))
    .mockResolvedValueOnce(jsonResponse({ username: "admin" }, 201))
    .mockResolvedValueOnce(jsonResponse([]));
  vi.stubGlobal("fetch", fetchMock);
  const router = createStudioRouter({
    history: createMemoryHistory(),
    pinia,
  });
  await router.push("/studio/setup");
  await router.isReady();
  const wrapper = mount(App, { global: { plugins: [pinia, router] } });

  await wrapper.get('input[name="code"]').setValue("setup-code");
  await wrapper.get('input[name="password"]').setValue("long-enough-password");
  await wrapper
    .get('input[name="passwordConfirmation"]')
    .setValue("different-password");
  await wrapper.get("form").trigger("submit");

  expect(wrapper.text()).toContain("两次输入的密码不一致");
  expect(fetchMock).toHaveBeenCalledTimes(1);

  await wrapper
    .get('input[name="passwordConfirmation"]')
    .setValue("long-enough-password");
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  expect(router.currentRoute.value.fullPath).toBe("/studio/datasources");
  expect(useAuthStore().state).toEqual({
    status: "authenticated",
    username: "admin",
  });
});

test("login submits credentials and opens the studio", async () => {
  const pinia = createPinia();
  setActivePinia(pinia);
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ initialized: true }))
      .mockResolvedValueOnce(
        jsonResponse(
          {
            error: {
              code: "AUTH_REQUIRED",
              message: "Authentication is required.",
              request_id: "login-session-1",
              field_errors: [],
            },
          },
          401,
        ),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse([])),
  );
  const router = createStudioRouter({
    history: createMemoryHistory(),
    pinia,
  });
  await router.push("/studio/login");
  await router.isReady();
  const wrapper = mount(App, { global: { plugins: [pinia, router] } });

  await wrapper.get('input[name="username"]').setValue("admin");
  await wrapper.get('input[name="password"]').setValue("long-enough-password");
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  expect(router.currentRoute.value.fullPath).toBe("/studio/datasources");
  expect(useAuthStore().state).toEqual({
    status: "authenticated",
    username: "admin",
  });
});
