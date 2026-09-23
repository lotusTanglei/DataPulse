# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: file-dataset.spec.ts >> administrator previews, maintains, and removes a Chinese CSV dataset
- Location: e2e/file-dataset.spec.ts:5:1

# Error details

```
Error: expect(locator).toHaveCount(expected) failed

Locator:  getByLabel('已上传文件').getByRole('option', { name: 'file-dataset-zh.csv' })
Expected: 0
Received: 1
Timeout:  8000ms

Call log:
  - Expect "toHaveCount" with timeout 8000ms
  - waiting for getByLabel('已上传文件').getByRole('option', { name: 'file-dataset-zh.csv' })
    20 × locator resolved to 1 element
       - unexpected value "1"

```

# Page snapshot

```yaml
- generic [ref=f2e3]:
  - complementary [ref=f2e4]:
    - generic "工作区导航" [ref=f2e5]:
      - generic [ref=f2e6]: D
      - generic [ref=f2e7]: DataPulse
      - generic [ref=f2e8]: ⌄
    - navigation "主导航" [ref=f2e9]:
      - link "概览" [ref=f2e10] [cursor=pointer]:
        - /url: /studio/overview
      - link "数据源" [ref=f2e17] [cursor=pointer]:
        - /url: /studio/datasources
      - link "数据集" [ref=f2e23] [cursor=pointer]:
        - /url: /studio/datasets
      - link "大屏" [ref=f2e28] [cursor=pointer]:
        - /url: /studio/screens
    - link "资源共享" [ref=f2e33] [cursor=pointer]:
      - /url: /studio/sharing
    - link "模板与插件" [ref=f2e38] [cursor=pointer]:
      - /url: /studio/ecosystem
    - link "用户管理" [ref=f2e43] [cursor=pointer]:
      - /url: /studio/users
    - region "最近访问" [ref=f2e48]:
      - paragraph [ref=f2e49]: 最近访问
      - paragraph [ref=f2e50]: 暂无最近项目
    - link "系统设置" [ref=f2e52] [cursor=pointer]:
      - /url: /studio/settings
    - generic [ref=f2e57]:
      - generic [ref=f2e58]: A
      - generic [ref=f2e59]: admin
      - button "退出管理员账号" [ref=f2e60] [cursor=pointer]
  - main [ref=f2e64]:
    - generic [ref=f2e65]:
      - navigation "面包屑" [ref=f2e66]:
        - generic [ref=f2e67]: DataPulse
        - generic [ref=f2e68]: /
        - strong [ref=f2e69]: 导入文件数据集
      - generic [ref=f2e70]: 本地工作区
    - region [ref=f2e72]:
      - generic [ref=f2e74]:
        - paragraph [ref=f2e75]: 文件工作台
        - heading "导入文件数据集" [level=1] [ref=f2e76]
        - paragraph [ref=f2e77]: 上传 CSV、Excel、JSON 或 Parquet 文件，生成可预览的只读数据集。
      - generic [ref=f2e78]:
        - generic [ref=f2e79]:
          - generic [ref=f2e80]:
            - generic [ref=f2e81]:
              - heading "上传文件" [level=2] [ref=f2e82]
              - paragraph [ref=f2e83]: 选择一个文件后会立即上传并解析字段。
            - generic [ref=f2e84]:
              - text: 选择文件
              - button "选择文件" [ref=f2e89] [cursor=pointer]
          - alert [ref=f2e90]:
            - generic [ref=f2e91]: "!"
            - paragraph [ref=f2e93]: 请求失败，请稍后重试。
          - generic [ref=f2e94]:
            - text: 已上传文件
            - combobox "已上传文件" [ref=f2e95]:
              - option "请选择文件"
              - option "file-dataset-zh.csv" [selected]
          - generic [ref=f2e96]:
            - generic [ref=f2e97]:
              - strong [ref=f2e98]: file-dataset-zh.csv
              - generic [ref=f2e99]:
                - generic [ref=f2e100]: CSV
                - button "删除文件" [ref=f2e101]
            - paragraph [ref=f2e105]: 2 行 · 2 个字段
            - list [ref=f2e106]:
              - listitem [ref=f2e107]:
                - code [ref=f2e108]: region
                - generic [ref=f2e109]: string
              - listitem [ref=f2e110]:
                - code [ref=f2e111]: amount
                - generic [ref=f2e112]: string
        - generic [ref=f2e113]:
          - heading "数据集配置" [level=2] [ref=f2e114]
          - generic [ref=f2e115]:
            - generic [ref=f2e116]:
              - generic [ref=f2e117]: 数据集名称
              - textbox "数据集名称" [ref=f2e118]:
                - /placeholder: 例如：销售文件数据集
            - generic [ref=f2e119]:
              - generic [ref=f2e120]: 最大行数
              - spinbutton "最大行数" [ref=f2e121]: "5000"
            - generic [ref=f2e122]:
              - generic [ref=f2e123]: 超时（秒）
              - spinbutton "超时（秒）" [ref=f2e124]: "30"
          - button "创建数据集" [disabled] [ref=f2e126]
      - generic [ref=f2e127]:
        - generic [ref=f2e128]:
          - strong [ref=f2e129]: 2 行样例
          - generic [ref=f2e130]: 1,147 ms
          - code [ref=f2e131]: 040df3c6-50b1-4749-87bb-a4a43190e6a3
        - region "查询结果" [ref=f2e132]:
          - table [ref=f2e133]:
            - row [ref=f2e134]:
              - columnheader "region string" [ref=f2e135]:
                - strong [ref=f2e136]: region
                - generic [ref=f2e137]: string
              - columnheader "amount string" [ref=f2e138]:
                - strong [ref=f2e139]: amount
                - generic [ref=f2e140]: string
            - generic [ref=f2e141]:
              - row [ref=f2e142]:
                - cell "华东" [ref=f2e143]
                - cell "120" [ref=f2e144]
              - row [ref=f2e145]:
                - cell "华南" [ref=f2e146]
                - cell "98" [ref=f2e147]
```

# Test source

```ts
  1  | import { expect, test } from "@playwright/test";
  2  | 
  3  | import { authenticate } from "./helpers.js";
  4  | 
  5  | test("administrator previews, maintains, and removes a Chinese CSV dataset", async ({
  6  |   page,
  7  | }) => {
  8  |   await authenticate(page);
  9  |   await page.goto("/studio/datasets/files/new");
  10 |   await page
  11 |     .getByRole("button", { name: "选择文件", exact: true })
  12 |     .setInputFiles("e2e/fixtures/file-dataset-zh.csv");
  13 | 
  14 |   await expect(page.getByLabel("查询结果")).toContainText("华东");
  15 |   await expect(page.getByLabel("查询结果")).toContainText("华南");
  16 |   await page.getByLabel("数据集名称").fill("E2E 中文文件数据集");
  17 |   await page.getByRole("button", { name: "创建数据集" }).click();
  18 |   await expect(
  19 |     page.getByRole("heading", { name: "E2E 中文文件数据集" }),
  20 |   ).toBeVisible();
  21 | 
  22 |   await page.getByLabel("名称").fill("E2E 中文文件明细");
  23 |   await page.getByLabel("最大行数").fill("100");
  24 |   await page.getByLabel("超时（秒）").fill("12");
  25 |   await page.getByRole("button", { name: "保存" }).click();
  26 |   await expect(
  27 |     page.getByRole("heading", { name: "E2E 中文文件明细" }),
  28 |   ).toBeVisible();
  29 |   await page.getByRole("button", { name: "运行预览" }).click();
  30 |   await expect(page.getByLabel("查询结果")).toContainText("华东");
  31 | 
  32 |   const detailUrl = page.url();
  33 |   await page.goto("/studio/datasets/files/new");
  34 |   await page.getByLabel("已上传文件").selectOption({
  35 |     label: "file-dataset-zh.csv",
  36 |   });
  37 |   page.once("dialog", (dialog) => dialog.accept());
  38 |   await page.getByRole("button", { name: "删除文件" }).click();
  39 |   await expect(page.getByText("The file asset is referenced by a dataset")).toBeVisible();
  40 |   await page.goto(detailUrl);
  41 | 
  42 |   page.once("dialog", (dialog) => dialog.accept());
  43 |   await page.getByRole("button", { name: "删除", exact: true }).click();
  44 |   await expect(page).toHaveURL(/\/studio\/datasets$/);
  45 | 
  46 |   await page.getByRole("link", { name: "导入文件" }).first().click();
  47 |   await page.getByLabel("已上传文件").selectOption({
  48 |     label: "file-dataset-zh.csv",
  49 |   });
  50 |   page.once("dialog", (dialog) => dialog.accept());
  51 |   await page.getByRole("button", { name: "删除文件" }).click();
  52 |   await expect(
  53 |     page.getByLabel("已上传文件").getByRole("option", {
  54 |       name: "file-dataset-zh.csv",
  55 |     }),
> 56 |   ).toHaveCount(0);
     |     ^ Error: expect(locator).toHaveCount(expected) failed
  57 | });
  58 | 
  59 | test("administrator previews Excel sheets, JSON, and Parquet files", async ({
  60 |   page,
  61 | }) => {
  62 |   await authenticate(page);
  63 |   await page.goto("/studio/datasets/files/new");
  64 | 
  65 |   const fileInput = page.getByRole("button", {
  66 |     name: "选择文件",
  67 |     exact: true,
  68 |   });
  69 |   await fileInput.setInputFiles("e2e/fixtures/file-dataset.xlsx");
  70 |   await expect(page.getByLabel("Excel Sheet")).toHaveValue("汇总");
  71 |   await expect(page.getByLabel("查询结果")).toContainText("华东");
  72 |   await page.getByLabel("Excel Sheet").selectOption("明细");
  73 |   await expect(page.getByLabel("查询结果")).toContainText("订单-001");
  74 | 
  75 |   await fileInput.setInputFiles("e2e/fixtures/file-dataset.json");
  76 |   await expect(page.getByLabel("查询结果")).toContainText("华南");
  77 |   await expect(page.getByLabel("Excel Sheet")).toHaveCount(0);
  78 | 
  79 |   await fileInput.setInputFiles("e2e/fixtures/file-dataset.parquet");
  80 |   await expect(page.getByLabel("查询结果")).toContainText("120.5");
  81 |   await expect(page.getByLabel("Excel Sheet")).toHaveCount(0);
  82 | });
  83 | 
```