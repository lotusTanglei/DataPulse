import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";
import {
  createMemoryHistory,
  createRouter,
  type Router,
} from "vue-router";

import DatasetDetailView from "./DatasetDetailView.vue";
import DatasetListView from "./DatasetListView.vue";
import SaveDatasetDialog from "./SaveDatasetDialog.vue";
import type { Dataset } from "./types";

const dataset: Dataset = {
  id: "dataset-1",
  name: "月度销售",
  data_source_id: "source-1",
  definition: {
    schema_version: 1,
    id: "dataset-1",
    name: "月度销售",
    data_source_id: "source-1",
    query: {
      kind: "sql",
      sql: "SELECT month, amount FROM sales WHERE region = :region",
    },
    fields: [
      { name: "month", data_type: "string" },
      { name: "amount", data_type: "number" },
    ],
    parameters: [
      {
        name: "region",
        data_type: "string",
        required: false,
        default: "north",
      },
    ],
    cache: { mode: "disabled", ttl_seconds: null },
    refresh: { mode: "manual", interval_seconds: null, cron: null },
    max_rows: 5000,
    timeout_seconds: 30,
  },
  created_at: "2026-07-30T03:00:00Z",
  updated_at: "2026-07-30T03:00:00Z",
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function testRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: { template: "<div />" } },
      {
        path: "/studio/datasets/:id",
        name: "dataset-detail",
        component: { template: "<div />" },
      },
      {
        path: "/studio/datasources",
        component: { template: "<div />" },
      },
    ],
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("saves a successful query as a named dataset and opens its detail", async () => {
  let submitted: unknown;
  vi.stubGlobal(
    "fetch",
    vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      submitted = JSON.parse(String(init?.body));
      return Promise.resolve(jsonResponse(dataset, 201));
    }),
  );
  const router = testRouter();
  await router.push("/");
  await router.isReady();
  const wrapper = mount(SaveDatasetDialog, {
    props: {
      open: true,
      datasourceId: "source-1",
      sql: "SELECT month, amount FROM sales WHERE region = :region",
      parameters: [
        { name: "region", data_type: "string", value: "north" },
      ],
    },
    global: { plugins: [router] },
  });

  expect(
    (wrapper.get('textarea[name="datasetSql"]').element as HTMLTextAreaElement)
      .value,
  ).toContain("SELECT month");
  await wrapper.get("form").trigger("submit");
  expect(wrapper.text()).toContain("请输入数据集名称");

  await wrapper.get('input[name="datasetName"]').setValue("月度销售");
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  expect(submitted).toEqual({
    name: "月度销售",
    data_source_id: "source-1",
    sql: "SELECT month, amount FROM sales WHERE region = :region",
    parameters: [
      {
        name: "region",
        data_type: "string",
        required: false,
        default: "north",
      },
    ],
    max_rows: 5000,
    timeout_seconds: 30,
  });
  expect(router.currentRoute.value.fullPath).toBe(
    "/studio/datasets/dataset-1",
  );
});

test("lists datasets with their source and fields", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/admin/datasets") {
        return Promise.resolve(jsonResponse([dataset]));
      }
      if (url === "/api/admin/datasources") {
        return Promise.resolve(
          jsonResponse([
            {
              id: "source-1",
              name: "分析仓库",
              config: { type: "sqlite", path: "sales.db" },
            },
          ]),
        );
      }
      throw new Error(`Unexpected request: ${url}`);
    }),
  );
  const router = testRouter();
  await router.push("/");
  await router.isReady();
  const wrapper = mount(DatasetListView, {
    global: { plugins: [router] },
  });
  await flushPromises();

  expect(wrapper.text()).toContain("月度销售");
  expect(wrapper.text()).toContain("分析仓库");
  expect(wrapper.text()).toContain("2 个字段");
});

test("edits dataset config and preserves preview parameters after an error", async () => {
  let patched: unknown;
  let previewCalls = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/admin/datasets/dataset-1" && init?.method === "GET") {
        return Promise.resolve(jsonResponse(dataset));
      }
      if (
        url === "/api/admin/datasources/source-1" &&
        init?.method === "GET"
      ) {
        return Promise.resolve(
          jsonResponse({
            id: "source-1",
            name: "分析仓库",
            config: { type: "sqlite", path: "sales.db" },
            status: "available",
            has_password: false,
            last_checked_at: null,
            last_latency_ms: null,
            last_error_code: null,
            created_at: "2026-07-30T03:00:00Z",
            updated_at: "2026-07-30T03:00:00Z",
          }),
        );
      }
      if (url === "/api/admin/datasets/dataset-1" && init?.method === "PATCH") {
        patched = JSON.parse(String(init.body));
        return Promise.resolve(
          jsonResponse({ ...dataset, name: "区域销售" }),
        );
      }
      if (
        url === "/api/admin/datasets/dataset-1/preview" &&
        init?.method === "POST"
      ) {
        previewCalls += 1;
        return Promise.resolve(
          jsonResponse(
            {
              error: {
                code: "QUERY_EXECUTION_FAILED",
                message: "预览失败。",
                request_id: "preview-error-5",
                field_errors: [],
              },
            },
            422,
          ),
        );
      }
      throw new Error(`Unexpected request: ${url}`);
    }),
  );
  const router = testRouter();
  await router.push("/studio/datasets/dataset-1");
  await router.isReady();
  const wrapper = mount(DatasetDetailView, {
    global: { plugins: [router] },
  });
  await flushPromises();

  await wrapper.get('input[name="name"]').setValue("区域销售");
  await wrapper.get('[data-action="save-dataset"]').trigger("click");
  await flushPromises();
  expect(patched).toMatchObject({ name: "区域销售" });

  const parameter = wrapper.get('input[name="parameter.region"]');
  await parameter.setValue('"south"');
  await wrapper.get('[data-action="preview-dataset"]').trigger("click");
  await flushPromises();

  expect(previewCalls).toBe(1);
  expect((parameter.element as HTMLInputElement).value).toBe('"south"');
  expect(wrapper.text()).toContain("预览失败。");
  expect(wrapper.text()).toContain("preview-error-5");
});
