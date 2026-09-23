import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, expect, test, vi } from "vitest";
import { createMemoryHistory } from "vue-router";

import App from "../../App.vue";
import { createStudioRouter } from "../../router";

const postgresDatasource = {
  id: "postgres-warehouse",
  name: "分析仓库",
  config: {
    type: "postgresql",
    host: "db.internal",
    port: 5432,
    database: "analytics",
    username: "reporter",
    ssl_mode: "require",
  },
  status: "available",
  has_password: true,
  last_checked_at: "2026-07-30T03:00:00Z",
  last_latency_ms: 18,
  last_error_code: null,
  created_at: "2026-07-28T08:00:00Z",
  updated_at: "2026-07-30T03:00:00Z",
} as const;

const sqliteDatasource = {
  ...postgresDatasource,
  id: "sqlite-sales",
  name: "本地销售",
  config: {
    type: "sqlite",
    path: "sales/warehouse.db",
  },
  has_password: false,
} as const;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function authenticatedFetch(
  handler: (url: string, init?: RequestInit) => Promise<Response>,
) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/auth/status") {
      return Promise.resolve(jsonResponse({ initialized: true }));
    }
    if (url === "/api/auth/session") {
      return Promise.resolve(jsonResponse({ username: "admin", role: "admin" }));
    }
    return handler(url, init);
  });
}

async function mountDetail(
  datasourceId: string,
  fetchMock: ReturnType<typeof vi.fn>,
): Promise<VueWrapper> {
  vi.stubGlobal("fetch", fetchMock);
  const pinia = createPinia();
  setActivePinia(pinia);
  const router = createStudioRouter({
    history: createMemoryHistory(),
    pinia,
  });
  await router.push(`/studio/datasources/${datasourceId}`);
  await router.isReady();
  const wrapper = mount(App, { global: { plugins: [pinia, router] } });
  await flushPromises();
  return wrapper;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("shows datasource properties and lazily expands a remote catalog", async () => {
  const fetchMock = authenticatedFetch(async (url) => {
    if (url === "/api/admin/datasources/postgres-warehouse") {
      return jsonResponse(postgresDatasource);
    }
    if (url === "/api/admin/datasources/postgres-warehouse/namespaces") {
      return jsonResponse([{ name: "public" }, { name: "analytics" }]);
    }
    if (
      url ===
      "/api/admin/datasources/postgres-warehouse/relations?namespace=public"
    ) {
      return jsonResponse([
        { namespace: "public", name: "sales", kind: "table" },
        { namespace: "public", name: "monthly_sales", kind: "view" },
      ]);
    }
    if (
      url ===
      "/api/admin/datasources/postgres-warehouse/relation?namespace=public&relation=sales"
    ) {
      return jsonResponse({
        namespace: "public",
        name: "sales",
        kind: "table",
        fields: [
          { name: "month", data_type: "text", nullable: false },
          { name: "amount", data_type: "numeric", nullable: false },
          { name: "region", data_type: "text", nullable: true },
        ],
      });
    }
    if (
      url ===
      "/api/admin/datasources/postgres-warehouse/relation/preview?namespace=public&relation=sales&limit=100"
    ) {
      return jsonResponse({
        request_id: "preview-1",
        columns: [
          { name: "month", data_type: "string" },
          { name: "amount", data_type: "number" },
        ],
        rows: [["2026-01", 100]],
        row_count: 1,
        truncated: false,
        duration_ms: 3,
      });
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  const wrapper = await mountDetail("postgres-warehouse", fetchMock);

  expect(wrapper.get("h1").text()).toBe("分析仓库");
  expect(wrapper.text()).toContain("PostgreSQL");
  expect(wrapper.text()).toContain("db.internal:5432/analytics");
  expect(wrapper.text()).toContain("18 ms");
  expect(
    wrapper.findAll('[role="tab"]').map((tab) => tab.text()),
  ).toEqual(["概览", "Schema", "SQL 调试", "设置"]);
  expect(
    fetchMock.mock.calls.some(
      ([input]) =>
        String(input) ===
        "/api/admin/datasources/postgres-warehouse/namespaces",
    ),
  ).toBe(false);

  await wrapper.get('[role="tab"][data-tab="schema"]').trigger("click");
  await flushPromises();
  expect(wrapper.get('[data-namespace="public"]').text()).toContain("public");
  expect(
    fetchMock.mock.calls.filter(
      ([input]) =>
        String(input) ===
        "/api/admin/datasources/postgres-warehouse/namespaces",
    ),
  ).toHaveLength(1);

  await wrapper
    .get('[data-namespace="public"] button[aria-label="展开命名空间 public"]')
    .trigger("click");
  await flushPromises();
  expect(wrapper.get('[data-relation="public.sales"]').text()).toContain("sales");

  await wrapper
    .get('[data-relation="public.sales"] button[aria-label="展开关系 sales"]')
    .trigger("click");
  await flushPromises();
  expect(wrapper.get('[data-field-name="amount"]').text()).toContain("numeric");
  expect(wrapper.get('[data-field-name="region"]').text()).toContain("可空");

  await wrapper
    .get('[data-relation="public.sales"] [data-preview-relation="sales"]')
    .trigger("click");
  await flushPromises();
  expect(wrapper.get('[data-preview-table="sales"]').text()).toContain("2026-01");
});

test("skips the namespace level for SQLite", async () => {
  const fetchMock = authenticatedFetch(async (url) => {
    if (url === "/api/admin/datasources/sqlite-sales") {
      return jsonResponse(sqliteDatasource);
    }
    if (
      url === "/api/admin/datasources/sqlite-sales/relations?namespace="
    ) {
      return jsonResponse([
        { namespace: null, name: "sales", kind: "table" },
      ]);
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  const wrapper = await mountDetail("sqlite-sales", fetchMock);

  await wrapper.get('[role="tab"][data-tab="schema"]').trigger("click");
  await flushPromises();

  expect(wrapper.find("[data-namespace]").exists()).toBe(false);
  expect(wrapper.get('[data-relation=".sales"]').text()).toContain("sales");
  expect(
    fetchMock.mock.calls.some(([input]) =>
      String(input).endsWith("/namespaces"),
    ),
  ).toBe(false);
});

test("isolates branch errors and refreshes only the selected namespace", async () => {
  const fetchMock = authenticatedFetch(async (url) => {
    if (url === "/api/admin/datasources/postgres-warehouse") {
      return jsonResponse(postgresDatasource);
    }
    if (url === "/api/admin/datasources/postgres-warehouse/namespaces") {
      return jsonResponse([{ name: "public" }, { name: "broken" }]);
    }
    if (
      url ===
      "/api/admin/datasources/postgres-warehouse/relations?namespace=public"
    ) {
      return jsonResponse([
        { namespace: "public", name: "sales", kind: "table" },
      ]);
    }
    if (
      url ===
      "/api/admin/datasources/postgres-warehouse/relations?namespace=broken"
    ) {
      return jsonResponse(
        {
          error: {
            code: "DATASOURCE_CATALOG_FAILED",
            message: "无法读取该命名空间。",
            request_id: "catalog-broken-9",
            field_errors: [],
          },
        },
        502,
      );
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  const wrapper = await mountDetail("postgres-warehouse", fetchMock);
  await wrapper.get('[role="tab"][data-tab="schema"]').trigger("click");
  await flushPromises();
  await wrapper
    .get('[data-namespace="public"] button[aria-label="展开命名空间 public"]')
    .trigger("click");
  await wrapper
    .get('[data-namespace="broken"] button[aria-label="展开命名空间 broken"]')
    .trigger("click");
  await flushPromises();

  expect(wrapper.find('[data-relation="public.sales"]').exists()).toBe(true);
  expect(wrapper.get('[data-namespace="broken"]').text()).toContain(
    "无法读取该命名空间。",
  );
  expect(wrapper.get('[data-namespace="broken"]').text()).toContain(
    "catalog-broken-9",
  );

  await wrapper
    .get('[data-namespace="public"] button[aria-label="刷新命名空间 public"]')
    .trigger("click");
  await flushPromises();

  expect(
    fetchMock.mock.calls.filter(
      ([input]) =>
        String(input) ===
        "/api/admin/datasources/postgres-warehouse/relations?namespace=public",
    ),
  ).toHaveLength(2);
  expect(
    fetchMock.mock.calls.filter(
      ([input]) =>
        String(input) ===
        "/api/admin/datasources/postgres-warehouse/namespaces",
    ),
  ).toHaveLength(1);
  expect(
    fetchMock.mock.calls.filter(
      ([input]) =>
        String(input) ===
        "/api/admin/datasources/postgres-warehouse/relations?namespace=broken",
    ),
  ).toHaveLength(1);
});

test("aborts a stale branch request when the namespace collapses", async () => {
  let relationSignal: AbortSignal | undefined;
  const pendingRelations = new Promise<Response>(() => undefined);
  const fetchMock = authenticatedFetch(async (url, init) => {
    if (url === "/api/admin/datasources/postgres-warehouse") {
      return jsonResponse(postgresDatasource);
    }
    if (url === "/api/admin/datasources/postgres-warehouse/namespaces") {
      return jsonResponse([{ name: "public" }]);
    }
    if (
      url ===
      "/api/admin/datasources/postgres-warehouse/relations?namespace=public"
    ) {
      relationSignal = init?.signal ?? undefined;
      return pendingRelations;
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  const wrapper = await mountDetail("postgres-warehouse", fetchMock);
  await wrapper.get('[role="tab"][data-tab="schema"]').trigger("click");
  await flushPromises();
  await wrapper
    .get('[data-namespace="public"] button[aria-label="展开命名空间 public"]')
    .trigger("click");
  await flushPromises();

  expect(relationSignal?.aborted).toBe(false);

  await wrapper
    .get('[data-namespace="public"] button[aria-label="收起命名空间 public"]')
    .trigger("click");

  expect(relationSignal?.aborted).toBe(true);
});
