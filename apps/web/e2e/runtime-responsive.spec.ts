import { expect, test, type Page } from "@playwright/test";

import {
  authenticate,
  createPublishedScreen,
  generateDisplayKey,
  issueEmbedTicket,
  rotateEmbedApiKey,
} from "./helpers.js";

function responsiveDocument() {
  return {
    canvas: {
      width: 1920,
      height: 1080,
      background: { color: "#07111f" },
    },
    theme: {
      id: "datapulse-dark",
      tokens: { text_primary: "#f8fafc" },
    },
    parameters: [
      {
        id: "region",
        name: "region",
        data_type: "string",
        default: "华东",
        mutable: true,
      },
    ],
    components: [
      {
        id: "responsive-title",
        type: "builtin.text",
        frame: { x: 48, y: 32, width: 1824, height: 96, z_index: 1 },
        props: {
          text: "多分辨率经营总览",
          align: "center",
          font_size: 34,
        },
      },
    ],
  };
}

async function runtimeMetrics(page: Page) {
  return page.evaluate(() => {
    const runtime = document.querySelector<HTMLElement>(".screen-runtime")!;
    const viewport = document.querySelector<HTMLElement>(
      ".screen-runtime__viewport",
    )!;
    const viewportRect = viewport.getBoundingClientRect();
    return {
      density: runtime.dataset.density,
      overflow: runtime.dataset.overflow,
      documentOverflow: {
        horizontal: document.documentElement.scrollWidth > innerWidth,
        vertical: document.documentElement.scrollHeight > innerHeight,
      },
      runtime: {
        clientWidth: runtime.clientWidth,
        clientHeight: runtime.clientHeight,
        scrollWidth: runtime.scrollWidth,
        scrollHeight: runtime.scrollHeight,
      },
      viewport: {
        width: viewportRect.width,
        height: viewportRect.height,
      },
    };
  });
}

test("runtime adapts across desktop, windowed, and narrow iframe containers", async ({
  page,
}, testInfo) => {
  test.setTimeout(60_000);
  await authenticate(page);
  const screen = await createPublishedScreen(
    page,
    `响应式运行时 ${Date.now()}`,
    responsiveDocument(),
  );
  const key = await generateDisplayKey(page, screen.id);

  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto(`/play/${screen.id}?key=${encodeURIComponent(key)}`);
  await expect(page.getByText("多分辨率经营总览")).toBeVisible();
  await expect(page.locator(".screen-runtime")).toHaveAttribute(
    "data-density",
    "comfortable",
  );
  const desktop = await runtimeMetrics(page);
  expect(desktop.documentOverflow).toEqual({ horizontal: false, vertical: false });
  expect(desktop.viewport).toEqual({ width: 1920, height: 1080 });

  await page.setViewportSize({ width: 1280, height: 720 });
  await expect(page.locator(".screen-runtime")).toHaveAttribute(
    "data-density",
    "compact",
  );
  const windowed = await runtimeMetrics(page);
  expect(windowed.documentOverflow).toEqual({ horizontal: false, vertical: false });
  expect(windowed.viewport.width).toBeCloseTo(1280, 0);
  expect(windowed.viewport.height).toBeCloseTo(720, 0);

  const apiKey = await rotateEmbedApiKey(page);
  const ticket = await issueEmbedTicket(page, {
    apiKey,
    screenId: screen.id,
  });
  await page.setViewportSize({ width: 800, height: 640 });
  await page.goto(
    `/e2e/embed-host.html?screen=${encodeURIComponent(screen.id)}&ticket=${encodeURIComponent(ticket)}`,
  );
  await expect(page.getByLabel("嵌入状态")).toHaveText("ready", {
    timeout: 12_000,
  });
  await page.locator("#embed-root").evaluate((element) => {
    const target = element as HTMLElement;
    target.style.width = "360px";
    target.style.height = "480px";
  });
  const frame = page.frameLocator("iframe");
  await expect(frame.locator(".screen-runtime")).toHaveAttribute(
    "data-density",
    "scroll",
  );
  await expect(frame.getByText("多分辨率经营总览")).toBeVisible();
  const embedded = await frame.locator("body").evaluate(() => {
    const runtime = document.querySelector<HTMLElement>(".screen-runtime")!;
    const viewport = document.querySelector<HTMLElement>(
      ".screen-runtime__viewport",
    )!;
    const viewportRect = viewport.getBoundingClientRect();
    const title = document.querySelector<HTMLElement>(
      '[data-component-id="responsive-title"]',
    )!;
    const titleRect = title.getBoundingClientRect();
    return {
      documentOverflow: {
        horizontal: document.documentElement.scrollWidth > innerWidth,
        vertical: document.documentElement.scrollHeight > innerHeight,
      },
      runtime: {
        clientWidth: runtime.clientWidth,
        clientHeight: runtime.clientHeight,
        scrollWidth: runtime.scrollWidth,
        scrollHeight: runtime.scrollHeight,
      },
      viewport: { width: viewportRect.width, height: viewportRect.height },
      title: { height: titleRect.height, width: titleRect.width },
    };
  });
  expect(embedded.documentOverflow).toEqual({ horizontal: false, vertical: false });
  expect(embedded.viewport).toEqual({ width: 1920, height: 1080 });
  expect(embedded.title).toEqual({ width: 1824, height: 96 });
  expect(embedded.runtime.scrollWidth).toBeGreaterThan(embedded.runtime.clientWidth);
  await testInfo.attach("runtime-responsive-iframe.png", {
    body: await page.screenshot({ animations: "disabled" }),
    contentType: "image/png",
  });
});
