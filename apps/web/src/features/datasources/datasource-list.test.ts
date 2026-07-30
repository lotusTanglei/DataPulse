import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, expect, test, vi } from "vitest";
import { createMemoryHistory } from "vue-router";

import App from "../../App.vue";
import { createStudioRouter } from "../../router";

interface DatasourceFixture {
  id: string;
  name: string;
  config:
    | { type: "sqlite"; path: string }
    | {
        type: "postgresql" | "mysql";
        host: string;
        port: number;
        database: string;
        username: string;
        ssl_mode: string;
      };
  status: "available" | "unavailable" | "unknown";
  has_password: boolean;
  last_checked_at: string | null;
  last_latency_ms: number | null;
  last_error_code: string | null;
  created_at: string;
  updated_at: string;
}

const datasourceFixtures: DatasourceFixture[] = [
  {
    id: "sqlite-sales",
    name: "本地销售",
    config: { type: "sqlite", path: "sales/warehouse.db" },
    status: "available",
    has_password: false,
    last_checked_at: "2026-07-29T08:30:00Z",
    last_latency_ms: 4,
    last_error_code: null,
    created_at: "2026-07-28T08:00:00Z",
    updated_at: "2026-07-29T08:30:00Z",
  },
  {
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
    status: "unavailable",
    has_password: true,
    last_checked_at: "2026-07-29T09:30:00Z",
    last_latency_ms: 1200,
    last_error_code: "DATASOURCE_CONNECTION_FAILED",
    created_at: "2026-07-28T08:00:00Z",
    updated_at: "2026-07-29T09:30:00Z",
  },
  {
    id: "mysql-operations",
    name: "业务数据库",
    config: {
      type: "mysql",
      host: "mysql.internal",
      port: 3306,
      database: "operations",
      username: "analyst",
      ssl_mode: "preferred",
    },
    status: "unknown",
    has_password: true,
    last_checked_at: null,
    last_latency_ms: null,
    last_error_code: null,
    created_at: "2026-07-28T08:00:00Z",
    updated_at: "2026-07-28T08:00:00Z",
  },
];

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function baseFetch(listResponse: Response | (() => Promise<Response>)) {
  return vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/auth/status") {
      return Promise.resolve(jsonResponse({ initialized: true }));
    }
    if (url === "/api/auth/session") {
      return Promise.resolve(jsonResponse({ username: "admin" }));
    }
    if (url === "/api/admin/datasources") {
      return typeof listResponse === "function"
        ? listResponse()
        : Promise.resolve(listResponse.clone());
    }
    throw new Error(`Unexpected request: ${url}`);
  });
}

async function mountList(fetchMock: ReturnType<typeof vi.fn>): Promise<VueWrapper> {
  vi.stubGlobal("fetch", fetchMock);
  const pinia = createPinia();
  setActivePinia(pinia);
  const router = createStudioRouter({
    history: createMemoryHistory(),
    pinia,
  });
  await router.push("/studio/datasources");
  await router.isReady();
  const wrapper = mount(App, { global: { plugins: [pinia, router] } });
  await flushPromises();
  return wrapper;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("renders safe datasource summaries with status and connection actions", async () => {
  const wrapper = await mountList(baseFetch(jsonResponse(datasourceFixtures)));

  const headers = wrapper.findAll("th").map((header) => header.text());
  expect(headers).toEqual([
    "名称",
    "类型",
    "地址",
    "状态",
    "上次检查",
    "上次查询",
    "操作",
  ]);
  expect(wrapper.text()).toContain("sales/warehouse.db");
  expect(wrapper.text()).toContain("db.internal:5432/analytics");
  expect(wrapper.text()).toContain("mysql.internal:3306/operations");
  expect(wrapper.text()).not.toContain("reporter");
  expect(wrapper.text()).not.toContain("analyst");
  expect(wrapper.get('[data-source-id="sqlite-sales"]').text()).toContain("可用");
  expect(wrapper.get('[data-source-id="postgres-warehouse"]').text()).toContain(
    "不可用",
  );
  expect(wrapper.get('[data-source-id="mysql-operations"]').text()).toContain(
    "未检查",
  );
  expect(
    wrapper.get('[data-source-id="sqlite-sales"] [role="img"]').attributes("aria-label"),
  ).toBe("连接可用");
  expect(
    wrapper.findAll('button[aria-label^="测试连接"]').map((button) => button.text()),
  ).toEqual(["测试", "测试", "测试"]);
});

test("keeps the previous status while one connection test is running", async () => {
  let resolveTest!: (response: Response) => void;
  const testResponse = new Promise<Response>((resolve) => {
    resolveTest = resolve;
  });
  const fetchMock = baseFetch(jsonResponse(datasourceFixtures));
  fetchMock.mockImplementation((input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/admin/datasources/postgres-warehouse/test") {
      return testResponse;
    }
    if (url === "/api/auth/status") {
      return Promise.resolve(jsonResponse({ initialized: true }));
    }
    if (url === "/api/auth/session") {
      return Promise.resolve(jsonResponse({ username: "admin" }));
    }
    if (url === "/api/admin/datasources") {
      return Promise.resolve(jsonResponse(datasourceFixtures));
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  const wrapper = await mountList(fetchMock);
  const row = wrapper.get('[data-source-id="postgres-warehouse"]');
  const button = row.get('button[aria-label="测试连接：分析仓库"]');

  await button.trigger("click");

  expect(row.text()).toContain("不可用");
  expect(button.attributes()).toHaveProperty("disabled");
  expect(button.text()).toBe("测试中…");
  await button.trigger("click");
  expect(
    fetchMock.mock.calls.filter(
      ([input]) =>
        String(input) === "/api/admin/datasources/postgres-warehouse/test",
    ),
  ).toHaveLength(1);

  resolveTest(
    jsonResponse({
      ...datasourceFixtures[1],
      status: "available",
      last_checked_at: "2026-07-30T03:00:00Z",
      last_latency_ms: 18,
      last_error_code: null,
    }),
  );
  await flushPromises();

  expect(row.text()).toContain("可用");
  expect(button.attributes()).not.toHaveProperty("disabled");
});

test("links an empty datasource workspace to the creation flow", async () => {
  const wrapper = await mountList(baseFetch(jsonResponse([])));

  const link = wrapper.get('a[href="/studio/datasources/new"]');
  expect(link.text()).toContain("新建数据源");
  expect(wrapper.text()).toContain("还没有数据源");
});

test("shows a safe API error with a copyable request ID", async () => {
  const wrapper = await mountList(
    baseFetch(
      jsonResponse(
        {
          error: {
            code: "DATASOURCE_LIST_FAILED",
            message: "暂时无法加载数据源。",
            request_id: "request-list-42",
            field_errors: [],
          },
        },
        503,
      ),
    ),
  );

  expect(wrapper.text()).toContain("暂时无法加载数据源。");
  expect(wrapper.text()).toContain("request-list-42");
  expect(wrapper.get('button[aria-label="复制请求 ID"]').text()).toBe("复制");
});
