import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";

import AiScreenGeneratorDialog from "./AiScreenGeneratorDialog.vue";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

function generatedScreen() {
  const plan = {
    schema_version: 1,
    title: "销售大屏",
    audience: "销售负责人",
    narrative: "展示销售趋势。",
    dataset_ids: ["sales"],
    layout: {
      template: "trend-focus",
      grid_columns: 24,
      density: "comfortable",
      theme: "dark",
    },
    regions: [{ id: "main", kind: "main", title: "趋势", order: 0 }],
    widgets: [
      {
        id: "trend",
        title: "销售趋势",
        intent: "展示月度销售趋势",
        region_id: "main",
        dataset_id: "sales",
        chart_type: "line",
        dimensions: ["month"],
        measures: [{ field: "amount", aggregation: "sum" }],
        filters: [],
        sort: [],
        limit: 1000,
      },
    ],
    parameters: [],
  };
  return {
    plan,
    document: {
      schema_version: 1,
      canvas: { width: 1920, height: 1080, background: {} },
      theme: { id: "datapulse-dark", tokens: {} },
      refresh: { mode: "disabled", interval_seconds: null },
      parameters: [],
      components: [
        {
          id: "trend",
          type: "builtin.line",
          frame: { x: 48, y: 112, width: 1824, height: 900, z_index: 1 },
          state: { locked: false, hidden: false, group_id: null },
          props: {},
          style: {},
          data_binding: {},
          interactions: [],
        },
      ],
      plugin_dependencies: [],
    },
    report: {
      valid: true,
      widget_count: 1,
      executed_count: 1,
      fallback_count: 0,
      checks: [],
      issues: [],
    },
    explanation: "采用趋势布局。",
    warnings: [] as string[],
  };
}

test("shows actionable component and field details for screen generation errors", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/admin/datasets") {
        return Promise.resolve(jsonResponse([{ id: "sales", name: "销售数据集" }]));
      }
      if (url === "/api/admin/ai/status") {
        return Promise.resolve(jsonResponse({ status: "configured", model: "test" }));
      }
      if (url === "/api/admin/ai/screen" && init?.method === "POST") {
        return Promise.resolve(
          jsonResponse(
            {
              error: {
                code: "AI_FIELD_UNKNOWN",
                message: "AI 使用了未知字段，请检查组件和字段绑定。",
                request_id: "screen-error-1",
                field_errors: [
                  {
                    component_id: "sales-chart",
                    field: "data_binding.chart_spec.dimensions[0]",
                    reason: "字段不存在于数据集",
                    expected: "已声明的数据集字段",
                  },
                ],
              },
            },
            422,
          ),
        );
      }
      throw new Error(`Unexpected request: ${url}`);
    }),
  );

  const wrapper = mount(AiScreenGeneratorDialog, { props: { open: true } });
  await flushPromises();
  await wrapper.get('input[name="aiScreenName"]').setValue("销售大屏");
  await wrapper.get('textarea[name="aiScreenQuestion"]').setValue("生成销售分析");
  await wrapper.get('input[name="aiScreenDatasets"]').setValue(true);
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  expect(wrapper.text()).toContain("sales-chart");
  expect(wrapper.text()).toContain("data_binding.chart_spec.dimensions[0]");
  expect(wrapper.text()).toContain("字段不存在于数据集");
  expect(wrapper.text()).toContain("已声明的数据集字段");
});

test("edits the generated plan through the shared compile endpoint", async () => {
  const generated = generatedScreen();
  generated.warnings = ["旧的生成提示"];
  const compileBodies: unknown[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/admin/datasets") {
        return Promise.resolve(jsonResponse([{ id: "sales", name: "销售数据集" }]));
      }
      if (url === "/api/admin/ai/status") {
        return Promise.resolve(jsonResponse({ status: "configured", model: "test" }));
      }
      if (url === "/api/admin/ai/screen" && init?.method === "POST") {
        return Promise.resolve(jsonResponse(generated));
      }
      if (url === "/api/admin/screens/plan/compile" && init?.method === "POST") {
        const body = JSON.parse(String(init.body));
        compileBodies.push(body);
        return Promise.resolve(
          jsonResponse({
            plan: body.plan,
            document: {
              ...generated.document,
              components: [
                { ...generated.document.components[0], type: "builtin.bar" },
              ],
            },
            report: {
              valid: false,
              widget_count: 1,
              executed_count: 1,
              fallback_count: 0,
              checks: [],
              issues: [
                {
                  code: "SEMANTIC_CATEGORY_EXPECTED",
                  component_id: "trend",
                  field: "dimensions[0]",
                  message: "柱状图应使用类别维度",
                },
              ],
            },
            warnings: ["修改后的自检提示"],
          }),
        );
      }
      throw new Error(`Unexpected request: ${url}`);
    }),
  );

  const wrapper = mount(AiScreenGeneratorDialog, {
    props: { open: true },
    global: { stubs: { ScreenDraftPreview: true } },
  });
  await flushPromises();
  await wrapper.get('input[name="aiScreenName"]').setValue("销售大屏");
  await wrapper.get('textarea[name="aiScreenQuestion"]').setValue("生成销售分析");
  await wrapper.get('input[name="aiScreenDatasets"]').setValue(true);
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  await wrapper.get('[data-field="chart-type"]').setValue("bar");
  await flushPromises();

  expect(compileBodies).toHaveLength(1);
  expect(compileBodies[0]).toMatchObject({
    plan: { widgets: [{ id: "trend", chart_type: "bar" }] },
  });
  expect(wrapper.text()).toContain("柱状图应使用类别维度");
  expect(wrapper.text()).toContain("组件 trend");
  expect(wrapper.text()).toContain("dimensions[0]");
  expect(wrapper.text()).toContain("修改后的自检提示");
  expect(wrapper.text()).not.toContain("旧的生成提示");
  await wrapper.get('[data-action="confirm-ai-screen"]').trigger("click");
  const confirmation = wrapper.emitted("confirm")?.[0]?.[0] as {
    result: {
      plan: { widgets: Array<{ chart_type: string }> };
      report: { valid: boolean };
    };
  };
  expect(confirmation.result.plan.widgets[0].chart_type).toBe("bar");
  expect(confirmation.result.report.valid).toBe(false);
});

test("groups multi-source datasets and filters them by name or id", async () => {
  const dataset = (
    id: string,
    name: string,
    query: Record<string, unknown>,
    dataSourceId: string | null,
  ) => ({
    id,
    name,
    data_source_id: dataSourceId,
    definition: {
      schema_version: 1,
      id,
      name,
      data_source_id: dataSourceId,
      query,
      fields: [],
      parameters: [],
      cache: { mode: "disabled", ttl_seconds: null },
      refresh: { mode: "manual", interval_seconds: null, cron: null },
      max_rows: 5000,
      timeout_seconds: 30,
    },
    created_at: "2026-09-23T00:00:00Z",
    updated_at: "2026-09-23T00:00:00Z",
  });
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/admin/datasets") {
        return Promise.resolve(
          jsonResponse([
            dataset("warehouse-sales", "主库销售", { kind: "sql", sql: "SELECT 1" }, "warehouse"),
            dataset("crm-sales", "CRM 销售", { kind: "sql", sql: "SELECT 1" }, "crm"),
            dataset("excel-targets", "Excel 目标", { kind: "file", asset_id: "targets", format: "excel", sheet_name: "目标" }, null),
            dataset("api-orders", "实时订单", { kind: "rest", method: "GET", url: "https://api.example.com/orders", query: {}, body: null, response_path: null }, "orders-api"),
          ]),
        );
      }
      if (url === "/api/admin/ai/status") {
        return Promise.resolve(jsonResponse({ status: "configured", model: "test" }));
      }
      throw new Error(`Unexpected request: ${url}`);
    }),
  );

  const wrapper = mount(AiScreenGeneratorDialog, { props: { open: true } });
  await flushPromises();

  expect(wrapper.get('[data-source-group="database:warehouse"]').text()).toContain("主库销售");
  expect(wrapper.get('[data-source-group="database:crm"]').text()).toContain("CRM 销售");
  expect(wrapper.get('[data-source-group="file:targets"]').text()).toContain("Excel 目标");
  expect(wrapper.get('[data-source-group="rest:orders-api"]').text()).toContain("实时订单");

  await wrapper.get('input[name="aiScreenDatasetSearch"]').setValue("warehouse");
  expect(wrapper.get('[data-dataset-id="warehouse-sales"]').text()).toContain("主库销售");
  expect(wrapper.find('[data-dataset-id="crm-sales"]').exists()).toBe(false);

  await wrapper.get('input[name="aiScreenDatasetSearch"]').setValue("api-orders");

  expect(wrapper.find('[data-dataset-id="warehouse-sales"]').exists()).toBe(false);
  expect(wrapper.find('[data-dataset-id="excel-targets"]').exists()).toBe(false);
  expect(wrapper.get('[data-dataset-id="api-orders"]').text()).toContain("实时订单");
});

test("applies a natural-language whole-screen edit before draft creation", async () => {
  const generated = generatedScreen();
  const requests: Array<{ url: string; body: Record<string, unknown> | null }> = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const body = init?.body ? JSON.parse(String(init.body)) : null;
      requests.push({ url, body });
      if (url === "/api/admin/datasets") {
        return Promise.resolve(jsonResponse([{ id: "sales", name: "销售数据集" }]));
      }
      if (url === "/api/admin/ai/status") {
        return Promise.resolve(jsonResponse({ status: "configured", model: "test" }));
      }
      if (url === "/api/admin/ai/screen" && init?.method === "POST") {
        return Promise.resolve(jsonResponse(generated));
      }
      if (url === "/api/admin/ai/screen/edit" && init?.method === "POST") {
        return Promise.resolve(
          jsonResponse({
            plan: {
              ...generated.plan,
              layout: { ...generated.plan.layout, theme: "light" },
            },
            document: {
              ...generated.document,
              theme: { id: "datapulse-light", tokens: {} },
            },
            affected_region_ids: ["main"],
            report: generated.report,
            explanation: "已切换为浅色风格。",
            warnings: [],
          }),
        );
      }
      throw new Error(`Unexpected request: ${url}`);
    }),
  );
  const wrapper = mount(AiScreenGeneratorDialog, {
    props: { open: true },
    global: { stubs: { ScreenDraftPreview: true } },
  });
  await flushPromises();
  await wrapper.get('input[name="aiScreenName"]').setValue("销售大屏");
  await wrapper.get('textarea[name="aiScreenQuestion"]').setValue("生成销售分析");
  await wrapper.get('input[name="aiScreenDatasets"]').setValue(true);
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  await wrapper.get('textarea[name="aiScreenEditQuestion"]').setValue("切换成浅色风格");
  await wrapper.get('form[aria-label="AI 修改大屏草稿"]').trigger("submit");
  await flushPromises();

  const editRequest = requests.find((request) => request.url === "/api/admin/ai/screen/edit");
  expect(editRequest?.body).toMatchObject({
    question: "切换成浅色风格",
    affected_region_ids: [],
    plan: { title: "销售大屏" },
  });
  expect(wrapper.text()).toContain("已切换为浅色风格");
  expect(
    requests.filter(
      (request) =>
        request.url === "/api/admin/screens" || request.url.includes("/publish"),
    ),
  ).toEqual([]);
});

test("limits a natural-language edit to selected regions", async () => {
  const generated = generatedScreen();
  const editBodies: Array<Record<string, unknown>> = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/admin/datasets") {
        return Promise.resolve(jsonResponse([{ id: "sales", name: "销售数据集" }]));
      }
      if (url === "/api/admin/ai/status") {
        return Promise.resolve(jsonResponse({ status: "configured", model: "test" }));
      }
      if (url === "/api/admin/ai/screen" && init?.method === "POST") {
        return Promise.resolve(jsonResponse(generated));
      }
      if (url === "/api/admin/ai/screen/edit" && init?.method === "POST") {
        const body = JSON.parse(String(init.body));
        editBodies.push(body);
        return Promise.resolve(
          jsonResponse({
            plan: {
              ...generated.plan,
              widgets: [
                { ...generated.plan.widgets[0], chart_type: "bar" },
              ],
            },
            document: {
              ...generated.document,
              components: [
                { ...generated.document.components[0], type: "builtin.bar" },
              ],
            },
            affected_region_ids: ["main"],
            report: generated.report,
            explanation: "已修改趋势分区。",
            warnings: [],
          }),
        );
      }
      throw new Error(`Unexpected request: ${url}`);
    }),
  );
  const wrapper = mount(AiScreenGeneratorDialog, {
    props: { open: true },
    global: { stubs: { ScreenDraftPreview: true } },
  });
  await flushPromises();
  await wrapper.get('input[name="aiScreenName"]').setValue("销售大屏");
  await wrapper.get('textarea[name="aiScreenQuestion"]').setValue("生成销售分析");
  await wrapper.get('input[name="aiScreenDatasets"]').setValue(true);
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  await wrapper.get('select[name="aiScreenEditScope"]').setValue("regions");
  await wrapper.get('input[name="aiScreenEditRegions"]').setValue(true);
  await wrapper.get('textarea[name="aiScreenEditQuestion"]').setValue("改成柱状图");
  await wrapper.get('form[aria-label="AI 修改大屏草稿"]').trigger("submit");
  await flushPromises();

  expect(editBodies).toHaveLength(1);
  expect(editBodies[0]).toMatchObject({
    affected_region_ids: ["main"],
    plan: { widgets: [{ id: "trend", chart_type: "line" }] },
  });
  await wrapper.get('[data-action="confirm-ai-screen"]').trigger("click");
  const confirmation = wrapper.emitted("confirm")?.[0]?.[0] as {
    result: { plan: { widgets: Array<{ chart_type: string }> } };
  };
  expect(confirmation.result.plan.widgets[0].chart_type).toBe("bar");
});
