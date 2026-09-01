import { expect, test } from "@playwright/test";

import {
  appOrigin,
  authenticate,
  createPublishedScreen,
  ensureAnalyticsDataset,
  generateDisplayKey,
  issueEmbedTicket,
  nineComponentDocument,
  rotateEmbedApiKey,
  uploadVisualAssets,
} from "./helpers.js";

const visualSnapshotOptions = {
  animations: "disabled" as const,
  maxDiffPixels: 10_000,
};

async function openStandalone(
  page: import("@playwright/test").Page,
  screenId: string,
): Promise<void> {
  const key = await generateDisplayKey(page, screenId);
  await page.goto(`/play/${screenId}?key=${encodeURIComponent(key)}`);
  await expect(page).toHaveURL(new RegExp(`/play/${screenId}$`));
  await expect(page.getByText("DataPulse 运营态势总览")).toBeVisible();
  await expect(page.getByText("正在加载…")).toHaveCount(0, {
    timeout: 12_000,
  });
}

test("published screens retain stable dark, light, isolated-error, and letterbox visuals", async ({
  page,
}) => {
  test.setTimeout(90_000);
  const queryFailures: string[] = [];
  page.on("response", (response) => {
    if (response.url().includes("/query") && !response.ok()) {
      queryFailures.push(`${response.status()} ${response.url()}`);
    }
  });
  await authenticate(page);
  const dataset = await ensureAnalyticsDataset(page);
  const assets = await uploadVisualAssets(page);

  const dark = await createPublishedScreen(
    page,
    "E2E 深色播放",
    nineComponentDocument(dataset.id, assets, "dark"),
  );
  await page.setViewportSize({ width: 1920, height: 1080 });
  await openStandalone(page, dark.id);
  await expect(
    page.getByText("数据加载失败"),
    queryFailures.join("\n"),
  ).toHaveCount(0);
  await expect(page).toHaveScreenshot("dark-player.png", {
    ...visualSnapshotOptions,
  });

  await page.setViewportSize({ width: 1200, height: 900 });
  await expect(page).toHaveScreenshot(
    "letterboxed-player.png",
    visualSnapshotOptions,
  );

  const light = await createPublishedScreen(
    page,
    "E2E 浅色播放",
    nineComponentDocument(dataset.id, assets, "light"),
  );
  await page.setViewportSize({ width: 1920, height: 1080 });
  await openStandalone(page, light.id);
  await expect(
    page.getByText("数据加载失败"),
    queryFailures.join("\n"),
  ).toHaveCount(0);
  await expect
    .poll(() =>
      page
        .locator(".screen-runtime__canvas")
        .evaluate((element) =>
          getComputedStyle(element).getPropertyValue("--screen-text-primary"),
        ),
    )
    .toBe("#0f172a");
  await expect(page).toHaveScreenshot("light-player.png", visualSnapshotOptions);

  const isolatedError = nineComponentDocument(dataset.id, assets, "dark");
  const broken = isolatedError.components.find(
    (component: { type: string }) => component.type === "builtin.line",
  );
  broken.data_binding.chart_spec.dimensions = ["missing_field"];
  const errorScreen = await createPublishedScreen(
    page,
    "E2E 组件错误隔离",
    isolatedError,
  );
  await openStandalone(page, errorScreen.id);
  await expect(page.getByText("数据加载失败")).toHaveCount(1);
  await expect(page.getByText("DataPulse 运营态势总览")).toBeVisible();
  await expect(page).toHaveScreenshot(
    "component-error-isolation.png",
    visualSnapshotOptions,
  );
});

test("direct iframe embeds load without an instance_id query parameter", async ({
  page,
}) => {
  test.setTimeout(60_000);
  await authenticate(page);
  const dataset = await ensureAnalyticsDataset(page);
  const assets = await uploadVisualAssets(page);
  const screen = await createPublishedScreen(
    page,
    "E2E 直连嵌入",
    nineComponentDocument(dataset.id, assets, "dark"),
  );
  const apiKey = await rotateEmbedApiKey(page);
  const ticket = await issueEmbedTicket(page, {
    apiKey,
    screenId: screen.id,
  });

  await page.goto(
    `/embed/${encodeURIComponent(screen.id)}?ticket=${encodeURIComponent(ticket)}`,
  );
  await expect(page.getByText("DataPulse 运营态势总览")).toBeVisible({
    timeout: 12_000,
  });
  await expect(page).toHaveURL(new RegExp(`/embed/${screen.id}$`));
  await expect(page.getByText("无法播放此大屏")).toHaveCount(0);
  await expect(page.getByText("正在加载…")).toHaveCount(0, {
    timeout: 12_000,
  });
});

test("host SDK controls an embedded screen and rejects unsafe access", async ({
  page,
}) => {
  test.setTimeout(75_000);
  await authenticate(page);
  const dataset = await ensureAnalyticsDataset(page);
  const assets = await uploadVisualAssets(page);
  const screen = await createPublishedScreen(
    page,
    "E2E 安全嵌入",
    nineComponentDocument(dataset.id, assets, "dark"),
  );
  const firstApiKey = await rotateEmbedApiKey(page);
  const ticket = await issueEmbedTicket(page, {
    apiKey: firstApiKey,
    screenId: screen.id,
  });
  await page.goto(
    `/e2e/embed-host.html?screen=${encodeURIComponent(screen.id)}&ticket=${encodeURIComponent(ticket)}`,
  );
  const status = page.getByLabel("嵌入状态");
  await expect(status).toHaveText("ready", { timeout: 12_000 });

  await page.getByRole("button", { name: "切换华南" }).click();
  await expect(status).toHaveText("region:华南");
  await page.getByRole("button", { name: "刷新大屏" }).click();
  await expect(status).toHaveText("refreshed");
  await page.getByRole("button", { name: "请求退出全屏" }).click();
  await expect(status).toHaveText("fullscreen-requested");
  await page.getByRole("button", { name: "修改禁用参数" }).click();
  await expect(status).toHaveText("error:EMBED_PARAMETER_DENIED");

  const wrongOriginTicket = await issueEmbedTicket(page, {
    apiKey: firstApiKey,
    screenId: screen.id,
    allowedOrigin: "https://wrong.example.com",
  });
  await page.goto(
    `/e2e/embed-host.html?screen=${encodeURIComponent(screen.id)}&ticket=${encodeURIComponent(wrongOriginTicket)}`,
  );
  await expect(page.getByLabel("嵌入状态")).toHaveText("loading");
  await page.waitForTimeout(800);
  await expect(page.getByLabel("嵌入状态")).toHaveText("loading");

  const expiringTicket = await issueEmbedTicket(page, {
    apiKey: firstApiKey,
    screenId: screen.id,
    lifetimeSeconds: 1,
  });
  await page.waitForTimeout(1200);
  await page.goto(
    `/e2e/embed-host.html?screen=${encodeURIComponent(screen.id)}&ticket=${encodeURIComponent(expiringTicket)}`,
  );
  const expiredFrame = page.locator("iframe");
  await expect(
    expiredFrame.contentFrame().getByText("无法播放此大屏"),
  ).toBeVisible();

  await rotateEmbedApiKey(page);
  const rejected = await page.request.post(`${appOrigin()}/api/embed/tickets`, {
    headers: { Authorization: `Bearer ${firstApiKey}` },
    data: {
      screen_id: screen.id,
      allowed_origin: appOrigin(),
      lifetime_seconds: 3600,
    },
  });
  expect(rejected.status()).toBe(401);
});
