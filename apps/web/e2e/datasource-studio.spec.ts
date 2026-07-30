import { expect, test } from "@playwright/test";

const adminPassword = "datapulse-e2e-password";

test("administrator can configure and analyze a SQLite datasource", async ({
  page,
}) => {
  await page.goto("/studio");
  await expect(
    page.getByRole("heading", { name: "初始化 DataPulse" }),
  ).toBeVisible();

  await page.getByLabel("初始化代码").fill("e2e-setup-code");
  await page.getByLabel("管理员用户名").fill("admin");
  await page.getByLabel("密码", { exact: true }).fill(adminPassword);
  await page.getByLabel("确认密码").fill(adminPassword);
  await page
    .getByRole("button", { name: "创建管理员并进入工作区" })
    .click();
  await expect(page).toHaveURL(/\/studio\/datasources$/);
  await expect(page.locator("body")).not.toContainText(adminPassword);

  await page.getByRole("button", { name: "退出管理员账号" }).click();
  await expect(page).toHaveURL(/\/studio\/login$/);
  await page.getByLabel("用户名").fill("admin");
  await page.getByLabel("密码").fill(adminPassword);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page).toHaveURL(/\/studio\/datasources$/);

  await page.getByRole("link", { name: "新建数据源" }).first().click();
  await page.getByLabel("数据源名称").fill("销售数据库");
  await page.getByLabel("相对路径").fill("sales.db");
  await page.getByRole("button", { name: "创建数据源" }).click();
  await expect(
    page.getByRole("heading", { name: "销售数据库" }),
  ).toBeVisible();
  await expect(page.locator("body")).not.toContainText(adminPassword);

  await page.getByRole("link", { name: "数据源", exact: true }).click();
  await page
    .getByRole("button", { name: "测试连接：销售数据库" })
    .click();
  await expect(page.locator('[data-source-id] [data-status="available"]')).toContainText(
    "可用",
  );
  await page.getByRole("link", { name: "销售数据库" }).click();

  await page.getByRole("tab", { name: "Schema" }).click();
  await page.getByRole("button", { name: "展开关系 sales" }).click();
  await expect(page.locator('[data-field-name="region"]')).toContainText("string");
  await expect(page.locator('[data-field-name="amount"]')).toContainText("number");

  await page.getByRole("tab", { name: "SQL 调试" }).click();
  const editor = page.locator("[data-sql-editor] .cm-content");
  const validSql =
    "SELECT region, amount FROM sales WHERE amount >= :minimum ORDER BY amount";
  await editor.fill(validSql);
  await page.getByRole("button", { name: "添加参数" }).click();
  await page.locator('input[name="parameter-name.0"]').fill("minimum");
  await page.locator('select[name="parameter-type.0"]').selectOption("number");
  await page.locator('input[name="parameter.minimum"]').fill("100");
  await page.getByRole("button", { name: "运行", exact: true }).click();
  await expect(page.getByLabel("查询结果")).toContainText("120.5");
  await expect(page.getByLabel("查询结果")).toContainText("200");
  await expect(page.getByText("2 行", { exact: true })).toBeVisible();

  await editor.fill("DELETE FROM sales");
  await page.getByRole("button", { name: "运行", exact: true }).click();
  await expect(page.getByText("QUERY_NOT_READ_ONLY", { exact: true })).toBeVisible();

  await editor.fill(validSql);
  await page.getByRole("button", { name: "运行", exact: true }).click();
  await expect(page.getByText("2 行", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "保存为数据集" }).click();
  await page.getByLabel("数据集名称").fill("高价值销售");
  await page.getByRole("button", { name: "保存数据集" }).click();

  await expect(
    page.getByRole("heading", { name: "高价值销售" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "运行预览" }).click();
  await expect(page.getByLabel("查询结果")).toContainText("120.5");
  await expect(page.getByLabel("查询结果")).toContainText("200");
  await expect(page.locator("body")).not.toContainText(adminPassword);
});
