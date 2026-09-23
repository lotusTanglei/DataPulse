import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";
import UsersView from "./UsersView.vue";

const user = { id: "editor-1", username: "小林", role: "editor", active: true, created_at: "2026-09-21T00:00:00Z", updated_at: "2026-09-21T00:00:00Z" };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

test("creates an account and clears the temporary password", async () => {
  const fetchMock = vi.fn((url: RequestInfo | URL, options?: RequestInit) => Promise.resolve(
    options?.method === "POST" ? json(user, 201) : json(String(url).includes("audit") ? [] : [user]),
  ));
  vi.stubGlobal("fetch", fetchMock);
  const wrapper = mount(UsersView);
  await flushPromises();
  await wrapper.get('input[name="username"]').setValue("小林");
  await wrapper.get('input[name="password"]').setValue("fixture-password");
  await wrapper.get('select[name="role"]').setValue("editor");
  await wrapper.get('form[aria-label="创建用户"]').trigger("submit");
  await flushPromises();
  expect(fetchMock).toHaveBeenCalledWith("/api/admin/users", expect.objectContaining({ method: "POST", body: JSON.stringify({ username: "小林", password: "fixture-password", role: "editor" }) }));
  expect((wrapper.get('input[name="password"]').element as HTMLInputElement).value).toBe("");
  expect(wrapper.text()).toContain("小林");
});

test("disabling a user requires confirmation and persists the change", async () => {
  const fetchMock = vi.fn((_url: RequestInfo | URL, options?: RequestInit) => Promise.resolve(json(options?.method === "PATCH" ? { ...user, active: false } : [user])));
  vi.stubGlobal("fetch", fetchMock);
  const confirm = vi.fn().mockReturnValueOnce(false).mockReturnValueOnce(true);
  vi.stubGlobal("confirm", confirm);
  const wrapper = mount(UsersView);
  await flushPromises();
  const button = wrapper.get('button[aria-label="停用用户：小林"]');
  await button.trigger("click");
  expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PATCH")).toBe(false);
  await button.trigger("click");
  await flushPromises();
  expect(fetchMock).toHaveBeenCalledWith("/api/admin/users/editor-1", expect.objectContaining({ method: "PATCH", body: '{"active":false}' }));
});

test("failed account writes show the stable error without losing the list", async () => {
  vi.stubGlobal("fetch", vi.fn((_url, init?: RequestInit) => Promise.resolve(init?.method === "POST"
    ? json({ error: { code: "USER_NAME_CONFLICT", message: "用户名已存在。", request_id: "fixture-1", field_errors: [] } }, 409)
    : json([user]))));
  const wrapper = mount(UsersView);
  await flushPromises();
  await wrapper.get('input[name="username"]').setValue("小林");
  await wrapper.get('input[name="password"]').setValue("fixture-password");
  await wrapper.get('form[aria-label="创建用户"]').trigger("submit");
  await flushPromises();
  expect(wrapper.text()).toContain("用户名已存在");
  expect(wrapper.text()).toContain("小林");
  expect((wrapper.get('input[name="password"]').element as HTMLInputElement).value).toBe("");
});
