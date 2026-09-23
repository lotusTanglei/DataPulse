# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ai-analysis.spec.ts >> AI analysis uses one request, applies a chart, and preserves the draft
- Location: e2e/ai-analysis.spec.ts:12:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('section.layers-panel[aria-label="图层"]').locator('[data-layer-id="bar-1"]')
Expected: visible
Timeout: 8000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 8000ms
  - waiting for locator('section.layers-panel[aria-label="图层"]').locator('[data-layer-id="bar-1"]')

```

# Test source

```ts
  1   | import { expect, test } from "@playwright/test";
  2   | 
  3   | import {
  4   |   apiGet,
  5   |   apiPost,
  6   |   authenticate,
  7   |   ensureAnalyticsDataset,
  8   |   mutationHeaders,
  9   |   type ScreenRecord,
  10  | } from "./helpers.js";
  11  | 
  12  | test("AI analysis uses one request, applies a chart, and preserves the draft", async ({
  13  |   page,
  14  | }) => {
  15  |   await authenticate(page);
  16  |   const dataset = await ensureAnalyticsDataset(page);
  17  |   const status = await apiGet<{ status: string; model: string | null }>(
  18  |     page,
  19  |     "/api/admin/ai/status",
  20  |   );
  21  |   expect(status).toEqual({ status: "configured", model: "e2e-fake-model" });
  22  | 
  23  |   const screen = await apiPost<ScreenRecord>(page, "/api/admin/screens", {
  24  |     name: "E2E AI 图表应用",
  25  |     draft_document: {
  26  |       schema_version: 1,
  27  |       canvas: { width: 1920, height: 1080, background: {} },
  28  |       components: [
  29  |         {
  30  |           id: "bar-1",
  31  |           type: "builtin.bar",
  32  |           frame: { x: 80, y: 120, width: 900, height: 520, z_index: 0 },
  33  |           state: { locked: false, hidden: false },
  34  |           props: { orientation: "vertical", empty_text: "暂无数据" },
  35  |           style: {},
  36  |           data_binding: {
  37  |             chart_spec: {
  38  |               schema_version: 1,
  39  |               dataset_id: dataset.id,
  40  |               dimensions: ["month"],
  41  |               measures: [{ field: "amount", aggregation: "sum" }],
  42  |               filters: [],
  43  |               sort: [],
  44  |               limit: 100,
  45  |               visual: { type: "bar", title: "原始图表" },
  46  |             },
  47  |           },
  48  |           interactions: [],
  49  |         },
  50  |       ],
  51  |       parameters: [],
  52  |       refresh: { mode: "disabled", interval_seconds: null },
  53  |       theme: { id: "datapulse-dark", tokens: {} },
  54  |     },
  55  |   });
  56  | 
  57  |   const aiRequests: string[] = [];
  58  |   page.on("request", (request) => {
  59  |     const path = new URL(request.url()).pathname;
  60  |     if (path.includes("/api/admin/ai/") || path.endsWith("/publish")) {
  61  |       aiRequests.push(`${request.method()} ${path}`);
  62  |     }
  63  |   });
  64  |   await page.goto(`/studio/screens/${screen.id}/edit`);
  65  |   const layersPanel = page.locator('section.layers-panel[aria-label="图层"]');
  66  |   const barLayer = layersPanel.locator('[data-layer-id="bar-1"]');
> 67  |   await expect(barLayer).toBeVisible();
      |                          ^ Error: expect(locator).toBeVisible() failed
  68  |   await barLayer.locator("span").first().click();
  69  |   await expect(barLayer).toHaveClass(/is-selected/);
  70  |   const aiPanel = page.getByLabel("AI 分析面板");
  71  |   await expect(aiPanel).toBeVisible();
  72  |   const panelStyles = await aiPanel.evaluate((element) => {
  73  |     const panel = getComputedStyle(element);
  74  |     const description = element.querySelector(".ai-panel__header p");
  75  |     const descriptionStyle = description ? getComputedStyle(description) : null;
  76  |     return {
  77  |       background: panel.backgroundColor,
  78  |       descriptionColor: descriptionStyle?.color ?? "",
  79  |     };
  80  |   });
  81  |   expect(panelStyles).toEqual({
  82  |     background: "rgb(255, 255, 255)",
  83  |     descriptionColor: "rgb(95, 94, 91)",
  84  |   });
  85  |   await page
  86  |     .getByLabel("分析问题")
  87  |     .fill("E2E_MODE:valid-analysis 请按区域分析销售额");
  88  |   await page.getByRole("button", { name: "生成建议" }).click();
  89  | 
  90  |   await expect(page.getByLabel("AI 分析结果")).toContainText(
  91  |     "E2E AI 建议按区域汇总销售额",
  92  |   );
  93  |   await expect(page.getByText("预览 3 行")).toBeVisible();
  94  |   await page.getByRole("button", { name: "应用到当前组件" }).click();
  95  |   await expect(
  96  |     page.getByLabel("编辑器工具栏").getByText("已保存"),
  97  |   ).toBeVisible({ timeout: 10_000 });
  98  | 
  99  |   expect(aiRequests.filter((item) => item.endsWith("/ai/analyze"))).toHaveLength(1);
  100 |   expect(aiRequests.some((item) => item.endsWith("/ai/chart"))).toBe(false);
  101 |   expect(aiRequests.some((item) => item.endsWith("/publish"))).toBe(false);
  102 | 
  103 |   await page.reload();
  104 |   const persisted = await apiGet<ScreenRecord>(
  105 |     page,
  106 |     `/api/admin/screens/${screen.id}`,
  107 |   );
  108 |   const chartSpec = persisted.draft_document.components[0].data_binding.chart_spec;
  109 |   expect(chartSpec.dimensions).toEqual(["region"]);
  110 |   expect(chartSpec.visual.title).toBe("区域销售额");
  111 | });
  112 | 
  113 | test("AI analysis maps malformed, invalid-field, and timeout responses", async ({
  114 |   page,
  115 | }) => {
  116 |   test.setTimeout(60_000);
  117 |   await authenticate(page);
  118 |   const dataset = await ensureAnalyticsDataset(page);
  119 |   const headers = await mutationHeaders(page);
  120 | 
  121 |   for (const [mode, status, code] of [
  122 |     ["malformed-json", 422, "AI_INVALID_OUTPUT"],
  123 |     ["invalid-field", 422, "AI_CHART_INVALID"],
  124 |     ["timeout", 504, "AI_TIMEOUT"],
  125 |   ] as const) {
  126 |     const response = await page.request.post("/api/admin/ai/analyze", {
  127 |       headers,
  128 |       data: {
  129 |         question: `E2E_MODE:${mode}`,
  130 |         dataset_ids: [dataset.id],
  131 |         mode: "chart",
  132 |       },
  133 |     });
  134 |     expect(response.status(), await response.text()).toBe(status);
  135 |     expect((await response.json()).error.code).toBe(code);
  136 |   }
  137 | });
  138 | 
```