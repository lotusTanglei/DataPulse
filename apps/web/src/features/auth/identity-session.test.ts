import { createPinia, setActivePinia } from "pinia";
import { afterEach, expect, test, vi } from "vitest";
import { createMemoryHistory } from "vue-router";

import { apiRequest } from "../../lib/api";
import { createStudioRouter } from "../../router";
import { useAuthStore } from "../../stores/auth";

const json = (body: unknown) => new Response(JSON.stringify(body), {
  headers: { "Content-Type": "application/json" },
});

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = "datapulse_csrf=; Max-Age=0; Path=/";
});

test("login obtains the server identity and role before opening the workspace", async () => {
  setActivePinia(createPinia());
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(null, { status: 204 }))
    .mockResolvedValueOnce(json({ id: "reader-id", username: "reader", role: "viewer" }));
  vi.stubGlobal("fetch", fetchMock);
  const auth = useAuthStore();
  await auth.login({ username: "reader", password: "fixture-password" });
  expect(auth.state).toEqual({ status: "authenticated", id: "reader-id", username: "reader", role: "viewer" });
  expect(fetchMock).toHaveBeenLastCalledWith("/api/auth/session", expect.anything());
});

test("an editor cannot navigate to account administration", async () => {
  const pinia = createPinia();
  setActivePinia(pinia);
  vi.stubGlobal("fetch", vi.fn()
    .mockResolvedValueOnce(json({ initialized: true }))
    .mockResolvedValueOnce(json({ id: "editor-id", username: "editor", role: "editor" })));
  const router = createStudioRouter({ pinia, history: createMemoryHistory() });
  await router.push("/studio/users");
  expect(router.currentRoute.value.path).toBe("/studio/screens");
});

test("grant PUT requests carry CSRF like other mutations", async () => {
  document.cookie = "datapulse_csrf=fixture-csrf; Path=/";
  const fetchMock = vi.fn().mockResolvedValue(json({}));
  vi.stubGlobal("fetch", fetchMock);
  await apiRequest("/api/admin/permissions", { method: "PUT", json: {} });
  expect(new Headers(fetchMock.mock.calls[0]![1].headers).get("X-CSRF-Token")).toBe("fixture-csrf");
});

test.each(["/studio/datasources/new", "/studio/datasources/source-1/edit", "/studio/datasets/files/new", "/studio/datasets/api/new"])("viewer cannot open a creation or write form at %s", async (path) => {
  const pinia = createPinia();
  setActivePinia(pinia);
  useAuthStore().state = { status: "authenticated", id: "viewer", username: "viewer", role: "viewer" };
  const router = createStudioRouter({ pinia, history: createMemoryHistory() });
  await router.push(path);
  expect(router.currentRoute.value.path).toBe("/studio/screens");
});

test("a shared read-only screen opens in preview instead of the editor", async () => {
  const pinia = createPinia();
  setActivePinia(pinia);
  useAuthStore().state = { status: "authenticated", id: "editor", username: "editor", role: "editor" };
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({ read: true, write: false, publish: false, manage: false })));
  const router = createStudioRouter({ pinia, history: createMemoryHistory() });
  await router.push("/studio/screens/shared/edit");
  expect(router.currentRoute.value.path).toBe("/studio/screens/shared/preview");
});
