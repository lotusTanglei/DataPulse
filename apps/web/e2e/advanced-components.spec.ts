import { expect, test } from "@playwright/test";

import {
  authenticate,
  createPublishedScreen,
  generateDisplayKey,
} from "./helpers.js";

const components = [
  ["builtin.map_drilldown", "geo", { title: "区域下钻", empty_text: "暂无数据" }],
  ["builtin.flow_map", "geo", { title: "区域流向", empty_text: "暂无数据" }],
  ["builtin.bubble_map", "geo", { title: "网点分布", empty_text: "暂无数据" }],
  ["builtin.relation_graph", "table", { title: "业务关系", animation: false }],
  ["builtin.org_chart", "table", { title: "组织架构", animation: false }],
  ["builtin.sankey", "table", { title: "业务流量", animation: false }],
  ["builtin.steps", "table", { title: "交付步骤" }],
  ["builtin.gantt", "table", { title: "项目计划" }],
  ["builtin.calendar_heatmap", "series", { title: "年度活跃度", animation: false }],
  ["builtin.kpi_group", "table", { title: "核心指标" }],
  ["builtin.metric_comparison", "table", { title: "指标对比" }],
  ["builtin.video", null, { title: "视频监控", muted: true }],
  ["builtin.iframe", null, { title: "网页嵌入", url: "" }],
  ["builtin.word_cloud", "series", { title: "热点词", animation: false }],
  ["builtin.liquid_fill", "single", { title: "目标完成率", animation: false }],
  ["builtin.polar_bar", "series", { title: "环形对比", animation: false }],
  ["builtin.rich_table", "table", { title: "区域明细", merge_columns: 1, highlight_threshold: 80 }],
  ["builtin.screen_carousel", null, { title: "多屏轮播", screen_urls: "", interval_seconds: 10 }],
] as const;

function advancedComponentDocument() {
  return {
    schema_version: 1,
    canvas: {
      width: 3840,
      height: 2160,
      background: { color: "#071522" },
    },
    theme: {
      id: "datapulse-dark",
      tokens: {
        panel_background: "#0b1b2b",
        panel_background_alt: "#10253a",
        panel_border: "#1b4160",
        text_primary: "#f8fafc",
        text_secondary: "#94a3b8",
        accent: "#26d9c1",
        chart_colors: ["#26d9c1", "#4da3ff", "#f3b638", "#f16d75"],
      },
    },
    refresh: { mode: "disabled", interval_seconds: null },
    parameters: [],
    components: components.map(([type, preset, props], index) => ({
      id: `advanced-${index + 1}`,
      type,
      frame: {
        x: 20 + (index % 6) * 635,
        y: 20 + Math.floor(index / 6) * 705,
        width: 615,
        height: 685,
        z_index: index,
      },
      state: { locked: false, hidden: false },
      props,
      style: {},
      data_binding: preset === null
        ? {}
        : {
            source: "mock",
            mock_data: {
              schema_version: 1,
              preset,
              seed: 100 + index,
              row_count: 8,
              value_min: 10,
              value_max: 100,
              trend: "up",
            },
          },
      interactions: [],
    })),
  };
}

test("batch two and three components publish and render as one stable gallery", async ({
  page,
}) => {
  test.setTimeout(75_000);
  const browserErrors: string[] = [];
  page.on("pageerror", (error) => browserErrors.push(error.message));
  await authenticate(page);
  const screen = await createPublishedScreen(
    page,
    "E2E 高级组件总览",
    advancedComponentDocument(),
  );
  const key = await generateDisplayKey(page, screen.id);

  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto(`/play/${screen.id}?key=${encodeURIComponent(key)}`);
  await expect(page).toHaveURL(new RegExp(`/play/${screen.id}$`));
  await expect(page.locator("[data-component-id]")).toHaveCount(components.length);
  await expect(page.getByText("正在加载…")).toHaveCount(0, { timeout: 15_000 });

  for (let index = 0; index < components.length; index += 1) {
    await expect(page.locator(`[data-component-id="advanced-${index + 1}"]`)).toBeVisible();
  }
  await expect(page.getByText(/暂不支持组件类型|组件渲染失败|数据加载失败|图表加载失败/)).toHaveCount(0);
  for (const index of [1, 2, 3, 4, 5, 6, 9, 14, 15, 16]) {
    await expect(
      page.locator(`[data-component-id="advanced-${index}"] canvas`).first(),
    ).toBeVisible();
  }
  expect(browserErrors).toEqual([]);
  await expect(page).toHaveScreenshot("advanced-components-gallery.png", {
    animations: "disabled",
    maxDiffPixels: 10_000,
  });
});
