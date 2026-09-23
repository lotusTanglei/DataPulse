import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, expect, test, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import { useAuthStore, type UserRole } from "../../stores/auth";
import DatasourceListView from "../datasources/DatasourceListView.vue";
import DatasourceDetailView from "../datasources/DatasourceDetailView.vue";
import DatasourceFormView from "../datasources/DatasourceFormView.vue";
import DatasetListView from "../datasets/DatasetListView.vue";
import DatasetDetailView from "../datasets/DatasetDetailView.vue";

const source = {
  id: "source-1", name: "共享数据源", config: { type: "sqlite", path: "sales.db" },
  status: "available", has_password: false, last_checked_at: null,
  last_latency_ms: null, last_error_code: null, created_at: "2026-09-21T00:00:00Z", updated_at: "2026-09-21T00:00:00Z",
};
const dataset = {
  id: "dataset-1", name: "共享数据集", data_source_id: "source-1",
  definition: {
    query: { kind: "sql", sql: "SELECT amount FROM sales" }, fields: [], parameters: [],
    max_rows: 5000, timeout_seconds: 30,
  },
};
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { "Content-Type": "application/json" },
});
const wrappers: VueWrapper[] = [];
afterEach(() => { wrappers.splice(0).forEach((wrapper) => wrapper.unmount()); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

async function render(component: object, role: UserRole | undefined, path: string, writable = false, accessFails = false) {
  const pinia = createPinia();
  setActivePinia(pinia);
  useAuthStore().state = { status: "authenticated", username: "reader", role };
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/identity/access/")) return accessFails
      ? json({ code: "UNAVAILABLE", message: "unavailable" }, 503)
      : json({ read: true, write: writable, publish: false, manage: false });
    if (url === "/api/admin/datasources/source-1" && init?.method === "PATCH") return json(source);
    if (url === "/api/admin/datasources/source-1") return json(source);
    if (url === "/api/admin/datasources") return json([source]);
    if (url === "/api/admin/datasets/dataset-1/preview") return json({ columns: [], rows: [], row_count: 0, duration_ms: 1, request_id: "preview", truncated: false });
    if (url === "/api/admin/datasets/dataset-1") return json(dataset);
    if (url === "/api/admin/datasets") return json([dataset]);
    if (url === "/api/admin/files") return json([]);
    if (url === "/api/admin/ai/status") return json({ status: "unconfigured" });
    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: "/studio/datasources/new", name: "datasource-new", component },
    { path: "/studio/datasources/:id/edit", name: "datasource-edit", component },
    { path: "/studio/datasources/:id", component },
    { path: "/studio/datasets/:id", component },
    { path: "/:pathMatch(.*)*", component },
  ] });
  await router.push(path);
  const wrapper = mount(component, { global: { plugins: [pinia, router], stubs: { SqlEditor: true, AiAnalysisPanel: true } } });
  wrappers.push(wrapper);
  await flushPromises();
  return { wrapper, fetchMock };
}

test.each(["viewer", undefined] as const)("%s cannot create or test datasources", async (role) => {
  const { wrapper } = await render(DatasourceListView, role, "/studio/datasources");
  expect(wrapper.text()).toContain("共享数据源");
  expect(wrapper.find('a[href="/studio/datasources/new"]').exists()).toBe(false);
  expect(wrapper.find('button[aria-label="测试连接：共享数据源"]').exists()).toBe(false);
});

test.each([false, true])("editor datasource actions follow write permission %s", async (writable) => {
  const { wrapper } = await render(DatasourceListView, "editor", "/studio/datasources", writable);
  expect(wrapper.find('a[href="/studio/datasources/new"]').exists()).toBe(true);
  expect(wrapper.find('button[aria-label="测试连接：共享数据源"]').exists()).toBe(writable);
});

test("read grant hides datasource edit and settings controls", async () => {
  const { wrapper } = await render(DatasourceDetailView, "editor", "/studio/datasources/source-1");
  expect(wrapper.text()).toContain("共享数据源");
  expect(wrapper.find('a[href$="/edit"]').exists()).toBe(false);
  expect(wrapper.find('[data-tab="settings"]').exists()).toBe(false);
});

test("viewer dataset list offers readable resources without creation links", async () => {
  const { wrapper } = await render(DatasetListView, "viewer", "/studio/datasets");
  expect(wrapper.find('a[href="/studio/datasets/dataset-1"]').exists()).toBe(true);
  expect(wrapper.text()).not.toContain("导入文件");
  expect(wrapper.text()).not.toContain("从数据源创建");
});

test.each([false, true])("read-only dataset remains previewable when access request fails %s", async (accessFails) => {
  const { wrapper, fetchMock } = await render(DatasetDetailView, "editor", "/studio/datasets/dataset-1", false, accessFails);
  expect(wrapper.find('[data-action="save-dataset"]').exists()).toBe(false);
  expect(wrapper.find('[data-action="delete-dataset"]').exists()).toBe(false);
  expect(wrapper.get('input[name="name"]').attributes("disabled")).toBeDefined();
  expect(wrapper.find("sql-editor-stub").exists()).toBe(false);
  expect(wrapper.text()).toContain("SELECT amount FROM sales");
  await wrapper.get('[data-action="preview-dataset"]').trigger("click");
  await flushPromises();
  expect(fetchMock).toHaveBeenCalledWith("/api/admin/datasets/dataset-1/preview", expect.objectContaining({ method: "POST" }));
});

test("write grant enables dataset editing", async () => {
  const { wrapper } = await render(DatasetDetailView, "editor", "/studio/datasets/dataset-1", true);
  expect(wrapper.find('[data-action="save-dataset"]').exists()).toBe(true);
  expect(wrapper.find('[data-action="delete-dataset"]').exists()).toBe(true);
  expect(wrapper.get('input[name="name"]').attributes("disabled")).toBeUndefined();
});

test("editor cannot register a server-local SQLite path", async () => {
  const { wrapper } = await render(DatasourceFormView, "editor", "/studio/datasources/new");
  expect(wrapper.find('option[value="sqlite"]').exists()).toBe(false);
  expect(wrapper.find('input[name="path"]').exists()).toBe(false);
  expect(wrapper.find('option[value="postgresql"]').exists()).toBe(true);
});

test("direct edit route without write grant has no mutable connection form", async () => {
  const { wrapper } = await render(DatasourceFormView, "editor", "/studio/datasources/source-1/edit");
  expect(wrapper.text()).toContain("只读");
  expect(wrapper.find("form").exists()).toBe(false);
});

test("editor can rename a shared SQLite source without resubmitting its filesystem config", async () => {
  const { wrapper, fetchMock } = await render(DatasourceFormView, "editor", "/studio/datasources/source-1/edit", true);
  expect(wrapper.get('input[name="path"]').attributes("disabled")).toBeDefined();
  expect(wrapper.get('select[name="connectorType"]').attributes("disabled")).toBeDefined();
  await wrapper.get('input[name="name"]').setValue("新的名称");
  await wrapper.get("form").trigger("submit");
  await flushPromises();
  expect(fetchMock).toHaveBeenCalledWith("/api/admin/datasources/source-1", expect.objectContaining({ method: "PATCH", body: JSON.stringify({ name: "新的名称" }) }));
});
