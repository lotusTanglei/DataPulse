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
}, testInfo) => {
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
    await library
      .getByRole("button", { name: new RegExp(`^${label}(?:\\s+数据)?$`) })
      .click();
  }
  const layersPanel = page.locator('section.layers-panel[aria-label="图层"]');
  const layers = layersPanel.locator("[data-layer-id]");
  await expect(layers).toHaveCount(9);

  const textLayer = layers.filter({ hasText: "文本" }).first();
  await textLayer.locator("span").first().click();
  await expect(textLayer).toHaveClass(/is-selected/);
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
  const movedFrame = await selected.evaluate((element) => {
    const target = element as HTMLElement;
    return {
      x: Number.parseFloat(target.style.left),
      y: Number.parseFloat(target.style.top),
    };
  });
  expect(movedFrame.x).toBeGreaterThan(40);
  expect(movedFrame.y).toBeGreaterThan(40);

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
  await expect(layersPanel.locator("[data-layer-id]")).toHaveCount(9);
  const reloadedTextLayer = layersPanel
    .locator("[data-layer-id]")
    .filter({ hasText: "文本" })
    .first();
  await reloadedTextLayer.locator("span").first().click();
  await expect(reloadedTextLayer).toHaveClass(/is-selected/);
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
  await expect(page.getByText("正在加载…")).toHaveCount(0, {
    timeout: 12_000,
  });
  for (const panel of [
    page.locator("aside.editor-panel--left"),
    page.locator("aside.editor-panel--right"),
  ]) {
    await panel.evaluate((element) => {
      element.scrollTop = 0;
    });
    await expect.poll(() => panel.evaluate((element) => element.scrollTop)).toBe(0);
  }
  await page.locator(":focus").evaluateAll((elements) => {
    for (const element of elements) {
      if (element instanceof HTMLElement) {
        element.blur();
      }
    }
  });
  const editorSnapshot = testInfo.project.name === "chromium"
    ? "editor-shell.png"
    : `editor-shell-${testInfo.project.name}.png`;
  await expect(page).toHaveScreenshot(editorSnapshot, {
    animations: "disabled",
  });
  await page.screenshot({
    path: testInfo.outputPath("editor-shell-actual.png"),
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
    { x: 156, y: 82 },
    { x: 290, y: 176 },
    { x: 460, y: 238 },
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

test("multi-selection drags as one group and persists the same canvas delta", async ({
  page,
}) => {
  test.setTimeout(45_000);
  await page.setViewportSize({ width: 1600, height: 1000 });
  await authenticate(page);
  await page.goto("/studio/screens");
  await page.getByRole("button", { name: /新建大屏/ }).first().click();
  await page.getByLabel("大屏名称").fill("E2E 多选拖拽");
  await page.getByRole("button", { name: "创建并编辑" }).click();

  const library = page.getByLabel("组件库");
  await library.getByRole("button", { name: "文本", exact: true }).click();
  await library.getByRole("button", { name: /^指标\s+数据$/ }).click();
  const components = page.locator("[data-canvas-component]");
  await expect(components).toHaveCount(2);
  await components.nth(0).click();
  await components.nth(1).click({ modifiers: ["Meta"] });
  await expect(page.locator(".editor-canvas-component.is-selected")).toHaveCount(2);

  const before = await components.evaluateAll((items) =>
    items.map((item) => ({
      x: Number.parseFloat((item as HTMLElement).style.left),
      y: Number.parseFloat((item as HTMLElement).style.top),
    })),
  );
  const firstBox = await components.nth(0).boundingBox();
  expect(firstBox).not.toBeNull();
  await page.mouse.move(
    firstBox!.x + firstBox!.width / 2,
    firstBox!.y + firstBox!.height / 2,
  );
  await page.mouse.down();
  await page.mouse.move(
    firstBox!.x + firstBox!.width / 2 + 50,
    firstBox!.y + firstBox!.height / 2 + 30,
    { steps: 6 },
  );
  await page.mouse.up();

  const after = await components.evaluateAll((items) =>
    items.map((item) => ({
      x: Number.parseFloat((item as HTMLElement).style.left),
      y: Number.parseFloat((item as HTMLElement).style.top),
    })),
  );
  const deltas = after.map((position, index) => ({
    x: position.x - before[index]!.x,
    y: position.y - before[index]!.y,
  }));
  expect(deltas[0]!.x).toBeGreaterThan(20);
  expect(deltas[0]!.y).toBeGreaterThan(10);
  expect(Math.abs(deltas[0]!.x - deltas[1]!.x)).toBeLessThanOrEqual(1);
  expect(Math.abs(deltas[0]!.y - deltas[1]!.y)).toBeLessThanOrEqual(1);

  const beforeSizes = await components.evaluateAll((items) =>
    items.map((item) => ({
      width: Number.parseFloat((item as HTMLElement).style.width),
      height: Number.parseFloat((item as HTMLElement).style.height),
    })),
  );
  const groupResizeHandle = page.locator(".moveable-control-box .moveable-se");
  await expect(groupResizeHandle).toBeVisible();
  const resizeBox = await groupResizeHandle.boundingBox();
  expect(resizeBox).not.toBeNull();
  await page.mouse.move(
    resizeBox!.x + resizeBox!.width / 2,
    resizeBox!.y + resizeBox!.height / 2,
  );
  await page.mouse.down();
  await page.mouse.move(
    resizeBox!.x + resizeBox!.width / 2 + 40,
    resizeBox!.y + resizeBox!.height / 2 + 30,
    { steps: 6 },
  );
  await page.mouse.up();
  const resized = await components.evaluateAll((items) =>
    items.map((item) => ({
      x: Number.parseFloat((item as HTMLElement).style.left),
      y: Number.parseFloat((item as HTMLElement).style.top),
      width: Number.parseFloat((item as HTMLElement).style.width),
      height: Number.parseFloat((item as HTMLElement).style.height),
    })),
  );
  expect(resized[0]!.width).toBeGreaterThan(beforeSizes[0]!.width);
  expect(resized[0]!.height).toBeGreaterThan(beforeSizes[0]!.height);
  expect(resized[1]!.width).toBeGreaterThan(beforeSizes[1]!.width);
  expect(resized[1]!.height).toBeGreaterThan(beforeSizes[1]!.height);

  await expect(
    page.getByLabel("编辑器工具栏").getByText("未保存"),
  ).toBeVisible();
  await expect(
    page.getByLabel("编辑器工具栏").getByText("已保存"),
  ).toBeVisible({ timeout: 10_000 });
  await page.reload();
  await expect(components).toHaveCount(2);
  const persisted = await page.locator("[data-canvas-component]").evaluateAll((items) =>
    items.map((item) => ({
      x: Number.parseFloat((item as HTMLElement).style.left),
      y: Number.parseFloat((item as HTMLElement).style.top),
    })),
  );
  expect(persisted).toEqual(
    resized.map(({ x, y }) => ({ x, y })),
  );
});
