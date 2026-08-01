import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";
import {
  createMemoryHistory,
  createRouter,
  type Router,
} from "vue-router";

import DatasetDetailView from "./DatasetDetailView.vue";
import FileDatasetCreateView from "./FileDatasetCreateView.vue";
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

const fileDataset: Dataset = {
  id: "dataset-file-1",
  name: "销售文件数据集",
  data_source_id: null,
  definition: {
    schema_version: 1,
    id: "dataset-file-1",
    name: "销售文件数据集",
    data_source_id: null,
    query: {
      kind: "file",
      asset_id: "file-1",
      format: "csv",
      sheet_name: null,
    },
    fields: [
      { name: "region", data_type: "string" },
      { name: "amount", data_type: "number" },
    ],
    parameters: [],
    cache: { mode: "disabled", ttl_seconds: null },
    refresh: { mode: "manual", interval_seconds: null, cron: null },
    max_rows: 5000,
    timeout_seconds: 30,
  },
  created_at: "2026-07-30T03:00:00Z",
  updated_at: "2026-07-30T03:00:00Z",
};

const fileAsset = {
  id: "file-1",
  original_name: "sales.csv",
  format: "csv",
  mime_type: "text/csv",
  size_bytes: 32,
  sha256: "hash",
  row_count: 2,
  fields: [
    { name: "region", data_type: "string" },
    { name: "amount", data_type: "number" },
  ],
  created_at: "2026-07-30T03:00:00Z",
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
        path: "/studio/datasets/files/new",
        name: "dataset-file-new",
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
        return Promise.resolve(jsonResponse([dataset, fileDataset]));
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
      if (url === "/api/admin/files") {
        return Promise.resolve(jsonResponse([fileAsset]));
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
  expect(wrapper.text()).toContain("销售文件数据集");
  expect(wrapper.text()).toContain("sales.csv");
  expect(wrapper.text()).toContain("导入文件");
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

test("loads file datasets without requesting a datasource and previews rows", async () => {
  let previewCalls = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (
        url === "/api/admin/datasets/dataset-file-1" &&
        init?.method === "GET"
      ) {
        return Promise.resolve(jsonResponse(fileDataset));
      }
      if (url === "/api/admin/files" && init?.method === "GET") {
        return Promise.resolve(jsonResponse([fileAsset]));
      }
      if (
        url === "/api/admin/datasets/dataset-file-1/preview" &&
        init?.method === "POST"
      ) {
        previewCalls += 1;
        return Promise.resolve(
          jsonResponse({
            request_id: "preview-file-1",
            columns: fileAsset.fields,
            rows: [["north", 10], ["south", 20]],
            row_count: 2,
            truncated: false,
            duration_ms: 12,
          }),
        );
      }
      throw new Error(`Unexpected request: ${url}`);
    }),
  );

  const router = testRouter();
  await router.push("/studio/datasets/dataset-file-1");
  await router.isReady();
  const wrapper = mount(DatasetDetailView, {
    global: { plugins: [router] },
  });
  await flushPromises();

  expect(wrapper.text()).toContain("sales.csv");
  expect(wrapper.text()).toContain("CSV");
  expect(wrapper.text()).toContain("文件数据集当前为只读");
  expect(wrapper.find('[data-action="save-dataset"]').exists()).toBe(false);

  await wrapper.get('[data-action="preview-dataset"]').trigger("click");
  await flushPromises();

  expect(previewCalls).toBe(1);
  expect(wrapper.text()).toContain("preview-file-1");
  expect(wrapper.text()).toContain("2 行");
  expect(wrapper.text()).toContain("region");
  expect(wrapper.text()).toContain("amount");
});

test("uploads a file and creates a file dataset", async () => {
  let submitted: unknown;
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/admin/files" && init?.method === "GET") {
        return Promise.resolve(jsonResponse([]));
      }
      if (url === "/api/admin/files" && init?.method === "POST") {
        return Promise.resolve(jsonResponse(fileAsset, 201));
      }
      if (url === "/api/admin/datasets/files" && init?.method === "POST") {
        submitted = JSON.parse(String(init.body));
        return Promise.resolve(jsonResponse(fileDataset, 201));
      }
      throw new Error(`Unexpected request: ${url}`);
    }),
  );

  const router = testRouter();
  await router.push("/studio/datasets/files/new");
  await router.isReady();
  const wrapper = mount(FileDatasetCreateView, {
    global: { plugins: [router] },
  });
  await flushPromises();

  const file = new File(["region,amount\nnorth,10\nsouth,20\n"], "sales.csv", {
    type: "text/csv",
  });
  const fileInput = wrapper.get('input[name="fileAsset"]');
  Object.defineProperty(fileInput.element, "files", {
    value: [file],
    configurable: true,
  });
  await fileInput.trigger("change");
  await flushPromises();

  expect(wrapper.text()).toContain("sales.csv");
  await wrapper.get('input[name="datasetName"]').setValue("销售文件数据集");
  await wrapper.get('[data-action="create-file-dataset"]').trigger("click");
  await flushPromises();

  expect(submitted).toEqual({
    name: "销售文件数据集",
    file_asset_id: "file-1",
    max_rows: 5000,
    timeout_seconds: 30,
  });
  expect(router.currentRoute.value.fullPath).toBe(
    "/studio/datasets/dataset-file-1",
  );
});
