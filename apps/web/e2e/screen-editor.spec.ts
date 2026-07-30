import { expect, test } from "@playwright/test";

import {
  apiGet,
  apiPatch,
  authenticate,
  configureNineComponentDocument,
  ensureAnalyticsDataset,
  generateDisplayKey,
  type ScreenRecord,
  uploadVisualAssets,
} from "./helpers.js";

test("administrator builds, previews, publishes, and plays a complete screen", async ({
  page,
}) => {
  test.setTimeout(75_000);
  await page.setViewportSize({ width: 1920, height: 1080 });
  await authenticate(page);
  const dataset = await ensureAnalyticsDataset(page);
  const assets = await uploadVisualAssets(page);

  await page.goto("/studio/screens");
  await page.getByRole("button", { name: /新建大屏/ }).first().click();
  await page.getByLabel("大屏名称").fill("E2E 运营大屏");
  await page.getByRole("button", { name: "创建并编辑" }).click();
  await expect(page.getByLabel("大屏编辑器")).toBeVisible();

  const library = page.getByLabel("组件库");
  for (const label of [
    "文本",
    "图片",
    "指标",
    "表格",
    "进度",
    "折线图",
    "柱状图",
    "饼图",
    "地图",
  ]) {
    await library.getByRole("button", { name: `＋ ${label}` }).click();
  }
  const layers = page.getByLabel("图层").locator("[data-layer-id]");
  await expect(layers).toHaveCount(9);

  await page.getByLabel("图层").getByText("文本", { exact: true }).click();
  await page.getByLabel("文本内容").fill("编辑器自动保存验证");
  await page.getByLabel("文本内容").blur();

  const selected = page.locator(".editor-canvas-component.is-selected");
  const selectedBox = await selected.boundingBox();
  expect(selectedBox).not.toBeNull();
  await page.mouse.move(
    selectedBox!.x + selectedBox!.width / 2,
    selectedBox!.y + selectedBox!.height / 2,
  );
  await page.mouse.down();
  await page.mouse.move(
    selectedBox!.x + selectedBox!.width / 2 + 40,
    selectedBox!.y + selectedBox!.height / 2 + 20,
    { steps: 5 },
  );
  await page.mouse.up();

  const resizeHandle = page.locator(".moveable-control-box .moveable-e");
  await expect(resizeHandle).toBeVisible();
  const handleBox = await resizeHandle.boundingBox();
  expect(handleBox).not.toBeNull();
  await page.mouse.move(
    handleBox!.x + handleBox!.width / 2,
    handleBox!.y + handleBox!.height / 2,
  );
  await page.mouse.down();
  await page.mouse.move(
    handleBox!.x + handleBox!.width / 2 + 60,
    handleBox!.y + handleBox!.height / 2,
    { steps: 5 },
  );
  await page.mouse.up();

  await page.getByRole("button", { name: "撤销" }).click();
  await page.getByRole("button", { name: "重做" }).click();
  await expect(
    page.getByLabel("编辑器工具栏").getByText("已保存"),
  ).toBeVisible({ timeout: 10_000 });

  await page.reload();
  await expect(page.getByLabel("图层").locator("[data-layer-id]")).toHaveCount(
    9,
  );
  await page.getByLabel("图层").getByText("文本", { exact: true }).click();
  await expect(page.getByLabel("文本内容")).toHaveValue(
    "编辑器自动保存验证",
  );

  const screenId = page.url().match(/\/screens\/([^/]+)\/edit/)?.[1];
  expect(screenId).toBeTruthy();
  const current = await apiGet<ScreenRecord>(
    page,
    `/api/admin/screens/${screenId}`,
  );
  const configured = configureNineComponentDocument(
    current.draft_document,
    dataset.id,
    assets,
  );
  await apiPatch<ScreenRecord>(
    page,
    `/api/admin/screens/${screenId}`,
    {
      draft_document: configured,
      expected_revision: current.draft_revision,
    },
  );
  await page.reload();
  await expect(page.getByText("DataPulse 运营态势总览")).toBeVisible();
  await expect(page).toHaveScreenshot("editor-shell.png", {
    animations: "disabled",
  });

  const previewPromise = page.waitForEvent("popup");
  await page.getByRole("link", { name: "预览" }).click();
  const preview = await previewPromise;
  await expect(preview.getByText("DataPulse 运营态势总览")).toBeVisible();
  await expect(preview.getByText("草稿预览")).toBeVisible();
  await preview.close();

  await page.getByRole("button", { name: "发布", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "确认发布大屏" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "确认发布" }).click();
  await expect(page.getByText("发布成功")).toBeVisible();

  const displayKey = await generateDisplayKey(page, screenId!);
  let queryCount = 0;
  page.on("request", (request) => {
    if (
      request.method() === "POST" &&
      request.url().includes(`/api/player/screens/${screenId}/query`)
    ) {
      queryCount += 1;
    }
  });
  await page.goto(`/play/${screenId}?key=${encodeURIComponent(displayKey)}`);
  await expect(page).toHaveURL(new RegExp(`/play/${screenId}$`));
  await expect(page.getByText("DataPulse 运营态势总览")).toBeVisible();
  await expect.poll(() => queryCount).toBeGreaterThanOrEqual(7);

  const beforeInteraction = queryCount;
  const chart = page.locator(".screen-chart canvas").first();
  await expect(chart).toBeVisible();
  for (const position of [
    { x: 130, y: 59 },
    { x: 292, y: 185 },
    { x: 453, y: 248 },
  ]) {
    await chart.click({ position });
    await page.waitForTimeout(250);
    if (queryCount > beforeInteraction) {
      break;
    }
  }
  expect(queryCount).toBeGreaterThan(beforeInteraction);

  const beforeTimer = queryCount;
  await expect
    .poll(() => queryCount, { timeout: 12_000 })
    .toBeGreaterThan(beforeTimer);
});
