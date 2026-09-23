# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: datasource-studio.spec.ts >> administrator can configure and analyze a SQLite datasource
- Location: e2e/datasource-studio.spec.ts:5:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('heading', { name: '销售数据库' })
Expected: visible
Timeout: 8000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 8000ms
  - waiting for getByRole('heading', { name: '销售数据库' })

```

```yaml
- complementary:
  - text: DataPulse
  - navigation "主导航":
    - link "概览":
      - /url: /studio/overview
    - link "数据源":
      - /url: /studio/datasources
    - link "数据集":
      - /url: /studio/datasets
    - link "大屏":
      - /url: /studio/screens
  - link "资源共享":
    - /url: /studio/sharing
  - link "模板与插件":
    - /url: /studio/ecosystem
  - link "用户管理":
    - /url: /studio/users
  - region "最近访问":
    - paragraph: 最近访问
    - paragraph: 暂无最近项目
  - link "系统设置":
    - /url: /studio/settings
  - text: admin
  - button "退出管理员账号"
- main:
  - navigation "面包屑":
    - text: DataPulse
    - strong: 新建数据源
  - text: 本地工作区
  - region "新建数据源":
    - paragraph: Datasource
    - heading "新建数据源" [level=1]
    - paragraph: 添加一个可用于分析的数据连接。
    - link "返回列表":
      - /url: /studio/datasources
    - alert:
      - paragraph: A datasource with this name already exists.
      - code: 45956139-6f35-491c-9a74-4b8d6f4fb724
    - heading "基本信息" [level=2]
    - paragraph: 名称仅用于 DataPulse 工作区内识别。
    - text: 数据源名称
    - textbox "数据源名称": 销售数据库
    - text: 连接器
    - combobox "连接器":
      - option "SQLite" [selected]
      - option "PostgreSQL"
      - option "MySQL / MariaDB"
      - option "HTTP API"
    - heading "连接配置" [level=2]
    - paragraph: 只保存必要信息，地址不会包含密码。
    - text: 相对路径
    - textbox "相对路径":
      - /placeholder: sales.db
      - text: sales.db
    - paragraph: 相对于 sources 目录，例如 sales/warehouse.db
    - link "取消":
      - /url: /studio/datasources
    - button "测试连接"
    - button "创建数据源"
```

# Test source

```ts
  1  | import { expect, test } from "@playwright/test";
  2  | 
  3  | import { adminPassword, authenticate } from "./helpers.js";
  4  | 
  5  | test("administrator can configure and analyze a SQLite datasource", async ({
  6  |   page,
  7  | }) => {
  8  |   await authenticate(page);
  9  |   await page.goto("/studio/datasources");
  10 | 
  11 |   await page.getByRole("link", { name: "新建数据源" }).first().click();
  12 |   await page.getByLabel("数据源名称").fill("销售数据库");
  13 |   await page.getByLabel("相对路径").fill("sales.db");
  14 |   await page.getByRole("button", { name: "创建数据源" }).click();
  15 |   await expect(
  16 |     page.getByRole("heading", { name: "销售数据库" }),
> 17 |   ).toBeVisible();
     |     ^ Error: expect(locator).toBeVisible() failed
  18 |   await expect(page.locator("body")).not.toContainText(adminPassword);
  19 | 
  20 |   await page.getByRole("link", { name: "数据源", exact: true }).click();
  21 |   await page
  22 |     .getByRole("button", { name: "测试连接：销售数据库" })
  23 |     .click();
  24 |   await expect(page.locator('[data-source-id] [data-status="available"]')).toContainText(
  25 |     "可用",
  26 |   );
  27 |   await page.getByRole("link", { name: "销售数据库" }).click();
  28 | 
  29 |   await page.getByRole("tab", { name: "Schema" }).click();
  30 |   await page.getByRole("button", { name: "展开关系 sales" }).click();
  31 |   await expect(page.locator('[data-field-name="region"]')).toContainText("string");
  32 |   await expect(page.locator('[data-field-name="amount"]')).toContainText("number");
  33 | 
  34 |   await page.getByRole("tab", { name: "SQL 调试" }).click();
  35 |   const editor = page.locator("[data-sql-editor] .cm-content");
  36 |   const validSql =
  37 |     "SELECT region, amount FROM sales WHERE amount >= :minimum ORDER BY amount";
  38 |   await editor.fill(validSql);
  39 |   await page.getByRole("button", { name: "添加参数" }).click();
  40 |   await page.locator('input[name="parameter-name.0"]').fill("minimum");
  41 |   await page.locator('select[name="parameter-type.0"]').selectOption("number");
  42 |   await page.locator('input[name="parameter.minimum"]').fill("100");
  43 |   await page.getByRole("button", { name: "运行", exact: true }).click();
  44 |   await expect(page.getByLabel("查询结果")).toContainText("120.5");
  45 |   await expect(page.getByLabel("查询结果")).toContainText("200");
  46 |   await expect(page.getByText("3 行", { exact: true })).toBeVisible();
  47 | 
  48 |   await editor.fill("DELETE FROM sales");
  49 |   await page.getByRole("button", { name: "运行", exact: true }).click();
  50 |   await expect(page.getByText("QUERY_NOT_READ_ONLY", { exact: true })).toBeVisible();
  51 | 
  52 |   await editor.fill(validSql);
  53 |   await page.getByRole("button", { name: "运行", exact: true }).click();
  54 |   await expect(page.getByText("3 行", { exact: true })).toBeVisible();
  55 |   await page.getByRole("button", { name: "保存为数据集" }).click();
  56 |   await page.getByLabel("数据集名称").fill("高价值销售");
  57 |   await page.getByRole("button", { name: "保存数据集" }).click();
  58 | 
  59 |   await expect(
  60 |     page.getByRole("heading", { name: "高价值销售" }),
  61 |   ).toBeVisible();
  62 |   await page.getByRole("button", { name: "运行预览" }).click();
  63 |   await expect(page.getByLabel("查询结果")).toContainText("120.5");
  64 |   await expect(page.getByLabel("查询结果")).toContainText("200");
  65 |   await expect(page.locator("body")).not.toContainText(adminPassword);
  66 | });
  67 | 
```