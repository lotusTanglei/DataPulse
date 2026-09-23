import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, expect, test, vi } from "vitest";
import SharingView from "./SharingView.vue";

const json = (body: unknown) => new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

test("shares a selected resource with a directory user and revokes after confirmation", async () => {
  const grant = { resource_type: "screen", resource_id: "screen-1", user_id: "editor-1", permission: "write" };
  let grants: typeof grant[] = [];
  const fetchMock = vi.fn((url: RequestInfo | URL, init?: RequestInit) => {
    const path = String(url);
    if (path.includes("directory")) return Promise.resolve(json([{ id: "editor-1", username: "小林" }]));
    if (path === "/api/admin/screens") return Promise.resolve(json([{ id: "screen-1", name: "销售看板" }]));
    if (path.includes("/identity/access/")) return Promise.resolve(json({ read: true, write: true, publish: true, manage: true }));
    if (init?.method === "PUT") { grants = [grant]; return Promise.resolve(json(grant)); }
    if (init?.method === "DELETE") { grants = []; return Promise.resolve(new Response(null, { status: 204 })); }
    return Promise.resolve(json(grants));
  });
  vi.stubGlobal("fetch", fetchMock);
  vi.stubGlobal("confirm", vi.fn(() => true));
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/:pathMatch(.*)*", component: SharingView }] });
  await router.push("/studio/sharing");
  const wrapper = mount(SharingView, { global: { plugins: [createPinia(), router] } });
  await flushPromises();
  await wrapper.get('select[name="resource"]').setValue("screen-1");
  await flushPromises();
  await wrapper.get('select[name="recipient"]').setValue("editor-1");
  await wrapper.get('select[name="permission"]').setValue("write");
  await wrapper.get('form[aria-label="共享资源"]').trigger("submit");
  await flushPromises();
  expect(fetchMock).toHaveBeenCalledWith("/api/admin/permissions", expect.objectContaining({ method: "PUT", body: JSON.stringify(grant) }));
  await wrapper.get('button[aria-label="撤销授权：小林"]').trigger("click");
  await flushPromises();
  expect(fetchMock).toHaveBeenCalledWith("/api/admin/permissions/screen/screen-1/editor-1", expect.objectContaining({ method: "DELETE" }));
  expect(wrapper.text()).toContain("暂无共享授权");
});

test("read access shows a clear notice without loading grants or offering mutation controls", async () => {
  const fetchMock = vi.fn((url: RequestInfo | URL) => {
    const path = String(url);
    if (path.includes("directory")) return Promise.resolve(json([]));
    if (path === "/api/admin/screens") return Promise.resolve(json([{ id: "screen-1", name: "只读看板" }]));
    if (path.includes("/identity/access/")) return Promise.resolve(json({ read: true, write: false, publish: false, manage: false }));
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/:pathMatch(.*)*", component: SharingView }] });
  await router.push("/studio/sharing?type=screen&id=screen-1");
  const wrapper = mount(SharingView, { global: { plugins: [createPinia(), router] } });
  await flushPromises();
  expect(wrapper.text()).toContain("仅拥有者和管理员可以管理此资源的共享");
  expect(wrapper.find('select[name="recipient"]').exists()).toBe(false);
  expect(wrapper.text()).not.toContain("保存共享授权");
  expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/permissions"))).toBe(false);
});
