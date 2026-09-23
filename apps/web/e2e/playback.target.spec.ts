import { expect, test, type Page, type TestInfo } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

import {
  appOrigin,
  authenticate,
  createPublishedScreen,
  ensureAnalyticsDataset,
  generateDisplayKey,
  nineComponentDocument,
  uploadVisualAssets,
} from "./helpers.js";

async function createTargetScreen(page: Page, name: string): Promise<string> {
  await authenticate(page);
  const dataset = await ensureAnalyticsDataset(page);
  const assets = await uploadVisualAssets(page);
  const document = nineComponentDocument(dataset.id, assets, "dark");
  document.components.push({
    id: "target-digital-human",
    type: "builtin.digital_human",
    frame: { x: 40, y: 690, width: 480, height: 350, z_index: 20 },
    props: {
      name: "长期播报员",
      role: "稳定性门禁",
      speech_template: "销售总额 {{sales.value | number}} 元。",
      muted: true,
      auto_play: false,
      subtitle_font_size: 22,
    },
    data_binding: {
      source: "components",
      variables: [{ name: "sales.value", component_id: "component-3", field: "amount" }],
    },
  });
  const screen = await createPublishedScreen(
    page,
    name,
    document,
  );
  return screen.id;
}

async function openStandalone(page: Page, screenId: string): Promise<void> {
  const key = await generateDisplayKey(page, screenId);
  await page.goto(`/play/${screenId}?key=${encodeURIComponent(key)}`);
  await expect(page).toHaveURL(new RegExp(`/play/${screenId}$`));
  await expect(page.getByText("DataPulse 运营态势总览")).toBeVisible();
  await expect(page.getByText("正在加载…")).toHaveCount(0, {
    timeout: 12_000,
  });
  await expect(page.locator("[data-component-id='target-digital-human'] .digital-human__subtitle")).toContainText("销售总额");
}

test("@display initial state and data subtitle meet playback baselines", async ({
  page,
}, testInfo) => {
  test.setTimeout(90_000);
  await page.setViewportSize({ width: 1920, height: 1080 });
  const screenId = await createTargetScreen(page, "Target Playback Baseline");

  const startedAt = Date.now();
  const key = await generateDisplayKey(page, screenId);
  const firstQueryResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("/api/player/screens/") &&
      response.url().endsWith("/query") &&
      response.status() >= 200 &&
      response.status() < 300,
    { timeout: 10_000 },
  );
  await page.goto(`/play/${screenId}?key=${encodeURIComponent(key)}`);
  await expect(page.locator(".screen-runtime")).toBeVisible();
  const firstVisibleMs = Date.now() - startedAt;
  const firstQueryResponse = await firstQueryResponsePromise;
  const firstQueryResponseAt = Date.now();
  const subtitle = page.locator(
    "[data-component-id='target-digital-human'] .digital-human__subtitle",
  );
  await expect(subtitle).toContainText("销售总额", { timeout: 5_000 });
  const subtitleVisibleAt = Date.now();
  const dataToSubtitleMs = Math.max(0, subtitleVisibleAt - firstQueryResponseAt);
  const metrics = {
    firstVisibleMs,
    subtitleMs: subtitleVisibleAt - startedAt,
    dataToSubtitleMs,
    firstQueryResponseObserved: true,
    firstQueryStatus: firstQueryResponse.status(),
  };
  console.log(`PLAYBACK_BASELINE_METRICS ${JSON.stringify(metrics)}`);
  await attachPageEvidence(page, testInfo, "playback-baseline", metrics);
  expect(firstVisibleMs).toBeLessThanOrEqual(2_000);
  expect(metrics.subtitleMs).toBeLessThanOrEqual(5_000);
  expect(dataToSubtitleMs).toBeLessThanOrEqual(5_000);
});

function redactUrl(value: string): string {
  try {
    const parsed = new URL(value);
    return `${parsed.origin}${parsed.pathname}`;
  } catch {
    return "unknown URL";
  }
}

async function attachPageEvidence(
  page: Page,
  testInfo: TestInfo,
  name: string,
  metrics: object,
): Promise<void> {
  // Playwright cannot disable animation already being painted into a canvas.
  await page.waitForTimeout(1_200);
  const screenshot = await page.screenshot({ animations: "disabled", scale: "css" });
  const serialized = Buffer.from(`${JSON.stringify(metrics, null, 2)}\n`);
  await testInfo.attach(`${name}-metrics.json`, {
    body: serialized,
    contentType: "application/json",
  });
  await testInfo.attach(`${name}.png`, {
    body: screenshot,
    contentType: "image/png",
  });
  const evidenceDirectory = process.env.DATAPULSE_TARGET_EVIDENCE_DIR;
  if (evidenceDirectory) {
    const target = resolve(evidenceDirectory);
    await mkdir(target, { recursive: true });
    await writeFile(resolve(target, `${name}-metrics.json`), serialized);
    await writeFile(resolve(target, `${name}.png`), screenshot);
  }
}

test("@display physical Retina playback remains readable", async ({ page }, testInfo) => {
  test.setTimeout(90_000);
  const screenId = await createTargetScreen(page, "Target Retina Display");
  await openStandalone(page, screenId);

  const metrics = await page.evaluate(() => {
    const viewport = document.querySelector<HTMLElement>(".screen-runtime__viewport");
    const viewportRect = viewport?.getBoundingClientRect();
    const canvasBackingRatios = Array.from(
      document.querySelectorAll<HTMLCanvasElement>("canvas"),
    ).map((canvas) => {
      const rect = canvas.getBoundingClientRect();
      return {
        backingWidth: canvas.width,
        cssWidth: rect.width,
        ratio: rect.width > 0 ? canvas.width / rect.width : 0,
      };
    });
    return {
      devicePixelRatio: window.devicePixelRatio,
      screenCss: { width: screen.width, height: screen.height },
      screenPhysical: {
        width: screen.width * window.devicePixelRatio,
        height: screen.height * window.devicePixelRatio,
      },
      viewportCss: { width: innerWidth, height: innerHeight },
      runtimeViewport: viewportRect
        ? { width: viewportRect.width, height: viewportRect.height }
        : null,
      documentOverflow: {
        horizontal: document.documentElement.scrollWidth > innerWidth,
        vertical: document.documentElement.scrollHeight > innerHeight,
      },
      canvasBackingRatios,
    };
  });

  expect(metrics.devicePixelRatio).toBeGreaterThanOrEqual(2);
  expect(metrics.screenPhysical.width).toBeGreaterThanOrEqual(3000);
  expect(metrics.screenPhysical.height).toBeGreaterThanOrEqual(1900);
  expect(metrics.runtimeViewport).not.toBeNull();
  expect(metrics.documentOverflow).toEqual({ horizontal: false, vertical: false });
  expect(metrics.canvasBackingRatios.length).toBeGreaterThan(0);
  expect(metrics.canvasBackingRatios.every((item) => item.ratio >= 2)).toBe(true);
  console.log(`DISPLAY_METRICS ${JSON.stringify(metrics)}`);
  await attachPageEvidence(page, testInfo, "physical-retina", metrics);
});

test("@display emulated 4K high-DPI playback preserves 16:9 layout", async ({
  browser,
}, testInfo) => {
  test.setTimeout(90_000);
  const context = await browser.newContext({
    baseURL: appOrigin(),
    deviceScaleFactor: 2,
    reducedMotion: "reduce",
    viewport: { width: 3840, height: 2160 },
  });
  const page = await context.newPage();
  try {
    const screenId = await createTargetScreen(page, "Target Emulated 4K Display");
    await openStandalone(page, screenId);
    const metrics = await page.evaluate(() => {
      const viewport = document.querySelector<HTMLElement>(".screen-runtime__viewport");
      const rect = viewport?.getBoundingClientRect();
      const media = matchMedia("(prefers-reduced-motion: reduce)");
      return {
        devicePixelRatio,
        inner: { width: innerWidth, height: innerHeight },
        runtimeViewport: rect ? { width: rect.width, height: rect.height } : null,
        reducedMotion: media.matches,
        documentOverflow: {
          horizontal: document.documentElement.scrollWidth > innerWidth,
          vertical: document.documentElement.scrollHeight > innerHeight,
        },
      };
    });
    expect(metrics).toMatchObject({
      devicePixelRatio: 2,
      inner: { width: 3840, height: 2160 },
      reducedMotion: true,
      documentOverflow: { horizontal: false, vertical: false },
    });
    expect(metrics.runtimeViewport).not.toBeNull();
    expect(metrics.runtimeViewport!.width / metrics.runtimeViewport!.height).toBeCloseTo(
      16 / 9,
      2,
    );
    console.log(`DISPLAY_METRICS ${JSON.stringify(metrics)}`);
    await attachPageEvidence(page, testInfo, "emulated-4k", metrics);
  } finally {
    await context.close();
  }
});

test("@soak published playback refreshes without overlap or stale errors", async ({
  page,
}, testInfo) => {
  const durationSeconds = Number(process.env.DATAPULSE_E2E_SOAK_SECONDS ?? "600");
  expect(Number.isInteger(durationSeconds)).toBe(true);
  expect(durationSeconds).toBeGreaterThanOrEqual(60);
  expect(durationSeconds).toBeLessThanOrEqual(8 * 60 * 60);
  test.setTimeout((durationSeconds + 90) * 1000);

  let queryStarted = 0;
  let queryFinished = 0;
  let inFlight = 0;
  let maxInFlight = 0;
  const failedRequests: string[] = [];
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/player/screens/") && request.url().endsWith("/query")) {
      queryStarted += 1;
      inFlight += 1;
      maxInFlight = Math.max(maxInFlight, inFlight);
    }
  });
  page.on("requestfinished", (request) => {
    if (request.url().includes("/api/player/screens/") && request.url().endsWith("/query")) {
      queryFinished += 1;
      inFlight -= 1;
    }
  });
  page.on("requestfailed", (request) => {
    if (request.url().includes("/api/player/screens/") && request.url().endsWith("/query")) {
      queryFinished += 1;
      inFlight -= 1;
      failedRequests.push(
        `${request.failure()?.errorText ?? "request failed"} [${redactUrl(request.url())}]`,
      );
    }
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(
        `${message.text()} [${redactUrl(message.location().url)}]`,
      );
    }
  });

  await page.setViewportSize({ width: 1920, height: 1080 });
  const screenId = await createTargetScreen(page, "Target Playback Soak");
  await openStandalone(page, screenId);
  const initialHeap = await page.evaluate(() => {
    const memory = (performance as Performance & {
      memory?: { usedJSHeapSize: number };
    }).memory;
    return memory?.usedJSHeapSize ?? null;
  });

  const heapSamples: Array<{
    elapsedSeconds: number;
    usedJSHeapSize: number | null;
    queryStarted: number;
    queryFinished: number;
    inFlight: number;
    resourceTransferBytes: number;
  }> = [];
  const sampleRuntimeMetrics = async (elapsed: number): Promise<void> => {
    const sample = await page.evaluate(() => {
      const memory = (performance as Performance & {
        memory?: { usedJSHeapSize: number };
      }).memory;
      const resourceTransferBytes = performance
        .getEntriesByType("resource")
        .reduce((total, entry) => {
          const resource = entry as PerformanceResourceTiming;
          return total + (resource.transferSize || resource.encodedBodySize || 0);
        }, 0);
      return { usedJSHeapSize: memory?.usedJSHeapSize ?? null, resourceTransferBytes };
    });
    heapSamples.push({
      elapsedSeconds: elapsed,
      usedJSHeapSize: sample.usedJSHeapSize,
      queryStarted,
      queryFinished,
      inFlight,
      resourceTransferBytes: sample.resourceTransferBytes,
    });
  };
  await sampleRuntimeMetrics(0);
  let elapsedSeconds = 0;
  while (elapsedSeconds < durationSeconds) {
    const sampleSeconds = Math.min(60, durationSeconds - elapsedSeconds);
    await page.waitForTimeout(sampleSeconds * 1000);
    elapsedSeconds += sampleSeconds;
    await sampleRuntimeMetrics(elapsedSeconds);
  }
  await expect(page.getByText("正在加载…")).toHaveCount(0, { timeout: 12_000 });
  await expect(page.getByText("数据加载失败")).toHaveCount(0);
  await expect(page.getByText("地图加载失败")).toHaveCount(0);
  await expect(page.getByText("DataPulse 运营态势总览")).toBeVisible();
  const finalHeap = await page.evaluate(() => {
    const memory = (performance as Performance & {
      memory?: { usedJSHeapSize: number };
    }).memory;
    return memory?.usedJSHeapSize ?? null;
  });
  const minimumRefreshCycles = Math.max(1, Math.floor(durationSeconds / 10) - 2);
  const metrics = {
    durationSeconds,
    queryStarted,
    queryFinished,
    maxInFlight,
    failedRequests,
    pageErrors,
    consoleErrors,
    initialHeap,
    finalHeap,
    heapGrowth: initialHeap !== null && finalHeap !== null ? finalHeap - initialHeap : null,
    heapSamples,
    resourceTiming: await page.evaluate(() => {
      const entries = performance.getEntriesByType("resource") as PerformanceResourceTiming[];
      return {
        count: entries.length,
        transferBytes: entries.reduce(
          (total, entry) => total + (entry.transferSize || entry.encodedBodySize || 0),
          0,
        ),
        failedOrOpaque: entries.filter((entry) => entry.transferSize === 0 && entry.duration > 0).length,
      };
    }),
  };

  console.log(`SOAK_METRICS ${JSON.stringify(metrics)}`);
  await attachPageEvidence(page, testInfo, "playback-soak", metrics);
  expect(queryStarted).toBeGreaterThanOrEqual(7 * (1 + minimumRefreshCycles));
  expect(queryFinished).toBe(queryStarted);
  expect(inFlight).toBe(0);
  expect(maxInFlight).toBeLessThanOrEqual(7);
  expect(failedRequests).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(consoleErrors).toEqual([]);
  if (metrics.heapGrowth !== null) {
    expect(metrics.heapGrowth).toBeLessThan(128 * 1024 * 1024);
  }
});
