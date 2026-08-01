import { expect, test } from "@playwright/test";

import { authenticate } from "./helpers.js";

test("administrator previews, maintains, and removes a Chinese CSV dataset", async ({
  page,
}) => {
  await authenticate(page);
  await page.goto("/studio/datasets/files/new");
  await page
    .getByRole("button", { name: "选择文件", exact: true })
    .setInputFiles("e2e/fixtures/file-dataset-zh.csv");

  await expect(page.getByLabel("查询结果")).toContainText("华东");
  await expect(page.getByLabel("查询结果")).toContainText("华南");
  await page.getByLabel("数据集名称").fill("E2E 中文文件数据集");
  await page.getByRole("button", { name: "创建数据集" }).click();
  await expect(
    page.getByRole("heading", { name: "E2E 中文文件数据集" }),
  ).toBeVisible();

  await page.getByLabel("名称").fill("E2E 中文文件明细");
  await page.getByLabel("最大行数").fill("100");
  await page.getByLabel("超时（秒）").fill("12");
  await page.getByRole("button", { name: "保存" }).click();
  await expect(
    page.getByRole("heading", { name: "E2E 中文文件明细" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "运行预览" }).click();
  await expect(page.getByLabel("查询结果")).toContainText("华东");

  const detailUrl = page.url();
  await page.goto("/studio/datasets/files/new");
  await page.getByLabel("已上传文件").selectOption({
    label: "file-dataset-zh.csv",
  });
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "删除文件" }).click();
  await expect(page.getByText("The file asset is referenced by a dataset")).toBeVisible();
  await page.goto(detailUrl);

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "删除", exact: true }).click();
  await expect(page).toHaveURL(/\/studio\/datasets$/);

  await page.getByRole("link", { name: "导入文件" }).first().click();
  await page.getByLabel("已上传文件").selectOption({
    label: "file-dataset-zh.csv",
  });
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "删除文件" }).click();
  await expect(
    page.getByLabel("已上传文件").getByRole("option", {
      name: "file-dataset-zh.csv",
    }),
  ).toHaveCount(0);
});

test("administrator previews Excel sheets, JSON, and Parquet files", async ({
  page,
}) => {
  await authenticate(page);
  await page.goto("/studio/datasets/files/new");

  const fileInput = page.getByRole("button", {
    name: "选择文件",
    exact: true,
  });
  await fileInput.setInputFiles("e2e/fixtures/file-dataset.xlsx");
  await expect(page.getByLabel("Excel Sheet")).toHaveValue("汇总");
  await expect(page.getByLabel("查询结果")).toContainText("华东");
  await page.getByLabel("Excel Sheet").selectOption("明细");
  await expect(page.getByLabel("查询结果")).toContainText("订单-001");

  await fileInput.setInputFiles("e2e/fixtures/file-dataset.json");
  await expect(page.getByLabel("查询结果")).toContainText("华南");
  await expect(page.getByLabel("Excel Sheet")).toHaveCount(0);

  await fileInput.setInputFiles("e2e/fixtures/file-dataset.parquet");
  await expect(page.getByLabel("查询结果")).toContainText("120.5");
  await expect(page.getByLabel("Excel Sheet")).toHaveCount(0);
});
