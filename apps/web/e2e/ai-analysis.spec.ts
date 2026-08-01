import { expect, test } from "@playwright/test";

import {
  apiGet,
  apiPost,
  authenticate,
  ensureAnalyticsDataset,
  mutationHeaders,
  type ScreenRecord,
} from "./helpers.js";

test("AI analysis uses one request, applies a chart, and preserves the draft", async ({
  page,
}) => {
  await authenticate(page);
  const dataset = await ensureAnalyticsDataset(page);
  const status = await apiGet<{ status: string; model: string | null }>(
    page,
    "/api/admin/ai/status",
  );
  expect(status).toEqual({ status: "configured", model: "e2e-fake-model" });

  const screen = await apiPost<ScreenRecord>(page, "/api/admin/screens", {
    name: "E2E AI 图表应用",
    draft_document: {
      schema_version: 1,
      canvas: { width: 1920, height: 1080, background: {} },
      components: [
        {
          id: "bar-1",
          type: "builtin.bar",
          frame: { x: 80, y: 120, width: 900, height: 520, z_index: 0 },
          state: { locked: false, hidden: false },
          props: { orientation: "vertical", empty_text: "暂无数据" },
          style: {},
          data_binding: {
            chart_spec: {
              schema_version: 1,
              dataset_id: dataset.id,
              dimensions: ["month"],
              measures: [{ field: "amount", aggregation: "sum" }],
              filters: [],
              sort: [],
              limit: 100,
              visual: { type: "bar", title: "原始图表" },
            },
          },
          interactions: [],
        },
      ],
      parameters: [],
      refresh: { mode: "disabled", interval_seconds: null },
      theme: { id: "datapulse-dark", tokens: {} },
    },
  });

  const aiRequests: string[] = [];
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path.includes("/api/admin/ai/") || path.endsWith("/publish")) {
      aiRequests.push(`${request.method()} ${path}`);
    }
  });
  await page.goto(`/studio/screens/${screen.id}/edit`);
  await page.getByLabel("图层").getByText("柱状图", { exact: true }).click();
  await expect(page.getByLabel("AI 分析面板")).toBeVisible();
  await page
    .getByLabel("分析问题")
    .fill("E2E_MODE:valid-analysis 请按区域分析销售额");
  await page.getByRole("button", { name: "生成建议" }).click();

  await expect(page.getByLabel("AI 分析结果")).toContainText(
    "E2E AI 建议按区域汇总销售额",
  );
  await expect(page.getByText("预览 3 行")).toBeVisible();
  await page.getByRole("button", { name: "应用到当前组件" }).click();
  await expect(
    page.getByLabel("编辑器工具栏").getByText("已保存"),
  ).toBeVisible({ timeout: 10_000 });

  expect(aiRequests.filter((item) => item.endsWith("/ai/analyze"))).toHaveLength(1);
  expect(aiRequests.some((item) => item.endsWith("/ai/chart"))).toBe(false);
  expect(aiRequests.some((item) => item.endsWith("/publish"))).toBe(false);

  await page.reload();
  const persisted = await apiGet<ScreenRecord>(
    page,
    `/api/admin/screens/${screen.id}`,
  );
  const chartSpec = persisted.draft_document.components[0].data_binding.chart_spec;
  expect(chartSpec.dimensions).toEqual(["region"]);
  expect(chartSpec.visual.title).toBe("区域销售额");
});

test("AI analysis maps malformed, invalid-field, and timeout responses", async ({
  page,
}) => {
  test.setTimeout(60_000);
  await authenticate(page);
  const dataset = await ensureAnalyticsDataset(page);
  const headers = await mutationHeaders(page);

  for (const [mode, status, code] of [
    ["malformed-json", 422, "AI_INVALID_OUTPUT"],
    ["invalid-field", 422, "AI_CHART_INVALID"],
    ["timeout", 504, "AI_TIMEOUT"],
  ] as const) {
    const response = await page.request.post("/api/admin/ai/analyze", {
      headers,
      data: {
        question: `E2E_MODE:${mode}`,
        dataset_ids: [dataset.id],
        mode: "chart",
      },
    });
    expect(response.status(), await response.text()).toBe(status);
    expect((await response.json()).error.code).toBe(code);
  }
});
