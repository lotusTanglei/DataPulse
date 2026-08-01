import { expect, test } from "@playwright/test";

import {
  apiGet,
  authenticate,
  ensureAnalyticsDataset,
  type ScreenRecord,
} from "./helpers.js";

test("AI screen preview cancels cleanly and confirms with one atomic create", async ({
  page,
}) => {
  await authenticate(page);
  const dataset = await ensureAnalyticsDataset(page);
  const initial = await apiGet<ScreenRecord[]>(page, "/api/admin/screens");
  const requests: Array<{ method: string; path: string }> = [];
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path.startsWith("/api/admin/screens") || path.endsWith("/publish")) {
      requests.push({ method: request.method(), path });
    }
  });

  const generate = async (name: string, question: string) => {
    await page.getByRole("button", { name: "AI 生成大屏" }).first().click();
    const dialog = page.getByRole("dialog", { name: "AI 生成大屏" });
    await dialog.getByLabel("大屏名称").fill(name);
    await dialog.getByLabel("需求描述").fill(question);
    await dialog
      .locator("label", { hasText: dataset.id })
      .getByRole("checkbox")
      .check();
    await dialog.getByRole("button", { name: "生成草稿" }).click();
    return dialog;
  };

  await page.goto("/studio/screens");
  let dialog = await generate(
    "E2E AI 取消草稿",
    "E2E_MODE:valid-screen 生成经营总览",
  );
  await expect(dialog.getByLabel("AI 大屏草稿预览")).toBeVisible();
  await expect(dialog.getByText("E2E AI 已生成标题和区域销售额图表")).toBeVisible();
  expect(
    requests.filter(
      (item) => item.method === "POST" && item.path === "/api/admin/screens",
    ),
  ).toHaveLength(0);
  await dialog.getByRole("button", { name: "取消" }).click();
  await expect(dialog).toBeHidden();
  expect(await apiGet<ScreenRecord[]>(page, "/api/admin/screens")).toHaveLength(
    initial.length,
  );

  dialog = await generate(
    "E2E AI 原子草稿",
    "E2E_MODE:valid-screen 生成经营总览",
  );
  await expect(dialog.getByLabel("AI 大屏草稿预览")).toBeVisible();
  await dialog
    .getByRole("button", { name: "创建草稿并进入编辑器" })
    .click();
  await expect(page.getByLabel("大屏编辑器")).toBeVisible();
  await expect(page.getByText("E2E AI 经营总览")).toBeVisible();

  const createRequests = requests.filter(
    (item) => item.method === "POST" && item.path === "/api/admin/screens",
  );
  expect(createRequests).toHaveLength(1);
  expect(
    requests.some(
      (item) => item.method === "PATCH" && item.path.startsWith("/api/admin/screens/"),
    ),
  ).toBe(false);
  expect(requests.some((item) => item.path.endsWith("/publish"))).toBe(false);

  await page.reload();
  await expect(page.getByText("E2E AI 经营总览")).toBeVisible();
});

test("invalid AI screens never create a draft", async ({ page }) => {
  await authenticate(page);
  const dataset = await ensureAnalyticsDataset(page);
  const initial = await apiGet<ScreenRecord[]>(page, "/api/admin/screens");
  await page.goto("/studio/screens");
  await page.getByRole("button", { name: "AI 生成大屏" }).first().click();
  const dialog = page.getByRole("dialog", { name: "AI 生成大屏" });
  await dialog.getByLabel("大屏名称").fill("E2E 非法 AI 草稿");
  await dialog.getByLabel("需求描述").fill("E2E_MODE:invalid-field");
  await dialog
    .locator("label", { hasText: dataset.id })
    .getByRole("checkbox")
    .check();
  await dialog.getByRole("button", { name: "生成草稿" }).click();
  await expect(dialog).toContainText("The AI analysis request is invalid");

  await dialog
    .getByLabel("需求描述")
    .fill("E2E_MODE:valid-screen E2E_UNAUTHORIZED_DATASET");
  await dialog.getByRole("button", { name: "生成草稿" }).click();
  await expect(dialog).toContainText("The AI analysis request is invalid");
  expect(await apiGet<ScreenRecord[]>(page, "/api/admin/screens")).toHaveLength(
    initial.length,
  );
});
