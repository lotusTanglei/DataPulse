import { expect, test } from "@playwright/test";

import { authenticate } from "./helpers.js";

test("administrator can upload a file and preview it as a dataset", async ({
  page,
}) => {
  await authenticate(page);
  await page.goto("/studio/datasets");

  await page.getByRole("link", { name: "导入文件" }).first().click();
  await expect(
    page.getByRole("heading", { name: "导入文件数据集" }),
  ).toBeVisible();

  await page
    .locator('input[name="fileAsset"]')
    .setInputFiles("e2e/fixtures/file-dataset.csv");

  await expect(page.locator(".dataset-file-asset strong")).toHaveText(
    "file-dataset.csv",
  );
  await page.getByLabel("数据集名称").fill("E2E 文件数据集");
  await page.getByRole("button", { name: "创建数据集" }).click();

  await expect(
    page.getByRole("heading", { name: "E2E 文件数据集" }),
  ).toBeVisible();
  await expect(page.getByText("文件数据集当前为只读")).toBeVisible();

  await page.getByRole("button", { name: "运行预览" }).click();
  await expect(page.getByLabel("查询结果")).toContainText("north");
  await expect(page.getByLabel("查询结果")).toContainText("south");
  await expect(page.getByText("2 行", { exact: true })).toBeVisible();
});
