import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, expect, test, vi } from "vitest";
import { createMemoryHistory, type Router } from "vue-router";

import App from "../../App.vue";
import { createStudioRouter } from "../../router";

const mysqlDatasource = {
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
  status: "available",
  has_password: true,
  last_checked_at: "2026-07-30T03:00:00Z",
  last_latency_ms: 15,
  last_error_code: null,
  created_at: "2026-07-28T08:00:00Z",
  updated_at: "2026-07-30T03:00:00Z",
} as const;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function authenticatedFetch(
  handler?: (url: string, init?: RequestInit) => Promise<Response>,
) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/auth/status") {
      return Promise.resolve(jsonResponse({ initialized: true }));
    }
    if (url === "/api/auth/session") {
      return Promise.resolve(jsonResponse({ username: "admin" }));
    }
    if (handler !== undefined) {
      return handler(url, init);
    }
    throw new Error(`Unexpected request: ${url}`);
  });
}

async function mountForm(
  path: string,
  fetchMock: ReturnType<typeof vi.fn>,
): Promise<{ wrapper: VueWrapper; router: Router }> {
  vi.stubGlobal("fetch", fetchMock);
  const pinia = createPinia();
  setActivePinia(pinia);
  const router = createStudioRouter({
    history: createMemoryHistory(),
    pinia,
  });
  await router.push(path);
  await router.isReady();
  const wrapper = mount(App, { global: { plugins: [pinia, router] } });
  await flushPromises();
  return { wrapper, router };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("switches between connector-specific fields and resets their defaults", async () => {
  const { wrapper } = await mountForm(
    "/studio/datasources/new",
    authenticatedFetch(),
  );
  const connector = wrapper.get('select[name="connectorType"]');

  expect(wrapper.find('input[name="name"]').exists()).toBe(true);
  expect(wrapper.find('input[name="path"]').exists()).toBe(true);
  expect(wrapper.find('input[name="host"]').exists()).toBe(false);

  await connector.setValue("postgresql");

  expect(wrapper.find('input[name="path"]').exists()).toBe(false);
  expect(wrapper.find('input[name="host"]').exists()).toBe(true);
  expect(
    (wrapper.get('input[name="port"]').element as HTMLInputElement).value,
  ).toBe("5432");
  expect(wrapper.find('input[name="database"]').exists()).toBe(true);
  expect(wrapper.find('input[name="username"]').exists()).toBe(true);
  expect(wrapper.find('input[name="password"]').exists()).toBe(true);
  expect(
    (wrapper.get('select[name="ssl_mode"]').element as HTMLSelectElement).value,
  ).toBe("prefer");

  await connector.setValue("mysql");

  expect(
    (wrapper.get('input[name="port"]').element as HTMLInputElement).value,
  ).toBe("3306");
  expect(
    (wrapper.get('select[name="ssl_mode"]').element as HTMLSelectElement).value,
  ).toBe("preferred");
});

test("creates an HTTP API datasource without exposing its credential in config", async () => {
  let submitted: unknown;
  const fetchMock = authenticatedFetch(async (url, init) => {
    if (url === "/api/admin/datasources" && init?.method === "POST") {
      submitted = JSON.parse(String(init.body));
      return jsonResponse({
        id: "http-source",
        name: "订单 API",
        config: {
          type: "http_api",
          base_url: "https://api.example.com/v1",
          auth_type: "bearer",
          api_key_header: "X-API-Key",
          username: null,
        },
        status: "unknown",
        has_password: true,
        last_checked_at: null,
        last_latency_ms: null,
        last_error_code: null,
        created_at: "2026-08-09T00:00:00Z",
        updated_at: "2026-08-09T00:00:00Z",
      }, 201);
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  const { wrapper, router } = await mountForm("/studio/datasources/new", fetchMock);
  await wrapper.get('select[name="connectorType"]').setValue("http_api");
  await wrapper.get('input[name="name"]').setValue("订单 API");
  await wrapper.get('input[name="base_url"]').setValue("https://api.example.com/v1");
  await wrapper.get('select[name="auth_type"]').setValue("bearer");
  await wrapper.get('input[name="password"]').setValue("secret-token");
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  expect(submitted).toEqual({
    name: "订单 API",
    config: {
      type: "http_api",
      base_url: "https://api.example.com/v1",
      auth_type: "bearer",
      api_key_header: "X-API-Key",
      username: null,
    },
    password: "secret-token",
  });
  expect(router.currentRoute.value.fullPath).toBe("/studio/datasources/http-source");
});

test("does not expose datasource credentials as login autofill targets on create", async () => {
  const { wrapper } = await mountForm(
    "/studio/datasources/new",
    authenticatedFetch(),
  );

  await wrapper.get('select[name="connectorType"]').setValue("postgresql");

  expect(wrapper.get("form").attributes("autocomplete")).toBe("off");
  expect(wrapper.get('input[name="username"]').attributes("autocomplete")).toBe(
    "new-password",
  );
  expect(wrapper.get('input[name="password"]').attributes("autocomplete")).toBe(
    "new-password",
  );
  expect((wrapper.get('input[name="username"]').element as HTMLInputElement).value).toBe(
    "",
  );
  expect((wrapper.get('input[name="password"]').element as HTMLInputElement).value).toBe(
    "",
  );
});

test("keeps datasource credentials out of login autofill targets while editing", async () => {
  const fetchMock = authenticatedFetch(async (url, init) => {
    if (
      url === "/api/admin/datasources/mysql-operations" &&
      init?.method === "GET"
    ) {
      return jsonResponse(mysqlDatasource);
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  const { wrapper } = await mountForm(
    "/studio/datasources/mysql-operations/edit",
    fetchMock,
  );

  expect(wrapper.get("form").attributes("autocomplete")).toBe("off");
  expect(wrapper.get('input[name="username"]').attributes("autocomplete")).toBe(
    "new-password",
  );
  expect(wrapper.get('input[name="password"]').attributes("autocomplete")).toBe(
    "new-password",
  );
  expect((wrapper.get('input[name="password"]').element as HTMLInputElement).value).toBe(
    "",
  );
});

test("tests an unsaved datasource configuration without saving it", async () => {
  let testedBody: unknown;
  const fetchMock = authenticatedFetch(async (url, init) => {
    if (url === "/api/admin/datasources/test" && init?.method === "POST") {
      testedBody = JSON.parse(String(init.body));
      return jsonResponse({ status: "available", latency_ms: 8, error_code: null });
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  const { wrapper } = await mountForm("/studio/datasources/new", fetchMock);

  await wrapper.get('select[name="connectorType"]').setValue("postgresql");
  await wrapper.get('input[name="name"]').setValue("销售库");
  await wrapper.get('input[name="host"]').setValue("localhost");
  await wrapper.get('input[name="database"]').setValue("sales");
  await wrapper.get('input[name="username"]').setValue("analyst");
  await wrapper.get('input[name="password"]').setValue("ephemeral-secret");
  const testButton = wrapper
    .findAll('button[type="button"]')
    .find((button) => button.text() === "测试连接");
  expect(testButton).toBeDefined();
  await testButton!.trigger("click");
  await flushPromises();

  expect(testedBody).toEqual({
    config: {
      type: "postgresql",
      host: "localhost",
      port: 5432,
      database: "sales",
      username: "analyst",
      ssl_mode: "prefer",
    },
    password: "ephemeral-secret",
  });
  expect(wrapper.text()).toContain("连接可用");
  expect(wrapper.text()).not.toContain("正在保存");
});

test("rejects unsafe SQLite paths and invalid remote ports before submit", async () => {
  const fetchMock = authenticatedFetch();
  const { wrapper } = await mountForm("/studio/datasources/new", fetchMock);

  await wrapper.get('input[name="name"]').setValue("本地销售");
  await wrapper.get('input[name="path"]').setValue("/tmp/sales.db");
  await wrapper.get("form").trigger("submit");
  expect(wrapper.text()).toContain("请输入 sources 目录内的相对路径");

  await wrapper.get('input[name="path"]').setValue("../sales.db");
  await wrapper.get("form").trigger("submit");
  expect(wrapper.text()).toContain("路径不能包含上级目录");

  await wrapper.get('select[name="connectorType"]').setValue("postgresql");
  await wrapper.get('input[name="port"]').setValue("70000");
  await wrapper.get("form").trigger("submit");
  expect(wrapper.text()).toContain("端口必须在 1 到 65535 之间");
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

test("creates a datasource and navigates to its detail page", async () => {
  let submittedBody = "";
  const created = {
    ...mysqlDatasource,
    id: "postgres-created",
    name: "分析仓库",
    config: {
      type: "postgresql",
      host: "db.internal",
      port: 5432,
      database: "analytics",
      username: "reporter",
      ssl_mode: "require",
    },
  };
  const fetchMock = authenticatedFetch(async (url, init) => {
    if (url === "/api/admin/datasources" && init?.method === "POST") {
      submittedBody = String(init.body);
      return jsonResponse(created, 201);
    }
    if (
      url === "/api/admin/datasources/postgres-created" &&
      init?.method === "GET"
    ) {
      return jsonResponse(created);
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  const { wrapper, router } = await mountForm(
    "/studio/datasources/new",
    fetchMock,
  );

  await wrapper.get('input[name="name"]').setValue("分析仓库");
  await wrapper.get('select[name="connectorType"]').setValue("postgresql");
  await wrapper.get('input[name="host"]').setValue("db.internal");
  await wrapper.get('input[name="database"]').setValue("analytics");
  await wrapper.get('input[name="username"]').setValue("reporter");
  await wrapper.get('input[name="password"]').setValue("secret-password");
  await wrapper.get('select[name="ssl_mode"]').setValue("require");
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  expect(JSON.parse(submittedBody)).toEqual({
    name: "分析仓库",
    config: {
      type: "postgresql",
      host: "db.internal",
      port: 5432,
      database: "analytics",
      username: "reporter",
      ssl_mode: "require",
    },
    password: "secret-password",
  });
  expect(router.currentRoute.value.fullPath).toBe(
    "/studio/datasources/postgres-created",
  );
});

test("edits connection details without exposing the stored password", async () => {
  let resolveUpdate!: (response: Response) => void;
  const updateResponse = new Promise<Response>((resolve) => {
    resolveUpdate = resolve;
  });
  let updateCalls = 0;
  const fetchMock = authenticatedFetch((url, init) => {
    if (
      url === "/api/admin/datasources/mysql-operations" &&
      init?.method === "GET"
    ) {
      return Promise.resolve(jsonResponse(mysqlDatasource));
    }
    if (
      url === "/api/admin/datasources/mysql-operations" &&
      init?.method === "PATCH"
    ) {
      updateCalls += 1;
      return updateResponse;
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  const { wrapper, router } = await mountForm(
    "/studio/datasources/mysql-operations/edit",
    fetchMock,
  );

  const password = wrapper.get('input[name="password"]');
  const clearPassword = wrapper.get('input[name="clear_password"]');
  expect((password.element as HTMLInputElement).value).toBe("");
  expect(wrapper.text()).toContain("留空则保留现有密码");

  await password.setValue("replacement-password");
  await clearPassword.setValue(true);
  await wrapper.get("form").trigger("submit");
  expect(wrapper.text()).toContain("新密码与清除密码不能同时设置");
  expect(updateCalls).toBe(0);

  await clearPassword.setValue(false);
  await wrapper.get("form").trigger("submit");
  expect(wrapper.get('button[type="submit"]').attributes()).toHaveProperty(
    "disabled",
  );
  expect(wrapper.get('button[type="submit"]').text()).toBe("正在保存…");

  resolveUpdate(
    jsonResponse({
      ...mysqlDatasource,
      updated_at: "2026-07-30T04:00:00Z",
    }),
  );
  await flushPromises();

  expect(router.currentRoute.value.fullPath).toBe(
    "/studio/datasources/mysql-operations",
  );
});

test("maps server field errors back to the visible field", async () => {
  const fetchMock = authenticatedFetch(async (url, init) => {
    if (url === "/api/admin/datasources" && init?.method === "POST") {
      return jsonResponse(
        {
          error: {
            code: "REQUEST_VALIDATION_ERROR",
            message: "数据源配置无效。",
            request_id: "form-request-7",
            field_errors: [
              {
                field: "config.path",
                message: "该 SQLite 文件不可用。",
              },
            ],
          },
        },
        422,
      );
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  const { wrapper } = await mountForm(
    "/studio/datasources/new",
    fetchMock,
  );

  await wrapper.get('input[name="name"]').setValue("本地销售");
  await wrapper.get('input[name="path"]').setValue("sales.db");
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  expect(wrapper.text()).toContain("数据源配置无效。");
  expect(wrapper.get('[data-field="path"]').text()).toContain(
    "该 SQLite 文件不可用。",
  );
  expect(wrapper.text()).toContain("form-request-7");
});
