# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ai-screen-generation.spec.ts >> AI screen preview cancels cleanly and confirms with one atomic create
- Location: e2e/ai-screen-generation.spec.ts:10:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByLabel('大屏编辑器')
Expected: visible
Timeout: 8000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 8000ms
  - waiting for getByLabel('大屏编辑器')

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
    - strong: 大屏
  - text: 本地工作区
  - region "大屏":
    - paragraph: 可视化工作区
    - heading "大屏" [level=1]
    - paragraph: 创建、调试并发布可独立播放或安全嵌入业务系统的数据大屏。
    - button "从模板创建"
    - button "AI 生成大屏"
    - button "新建大屏"
    - alert:
      - paragraph: A screen with this name already exists.
      - code: 7ff0f819-7192-4bff-88ca-391d5b795ebc
    - article:
      - link "E2E AI 图表应用 草稿 暂无描述 最后更新 2026/09/21 11:36":
        - /url: /studio/screens/71e8a6e6-e035-4541-bd49-919a2069bc07/edit
        - strong: E2E AI 图表应用
        - text: 草稿 暂无描述 最后更新 2026/09/21 11:36
      - button "复制大屏 E2E AI 图表应用": 复制
      - button "删除大屏 E2E AI 图表应用": 删除
    - article:
      - link "E2E AI 原子草稿 草稿 暂无描述 最后更新 2026/09/21 11:37":
        - /url: /studio/screens/dbaf7fd0-51a5-47d0-a90e-4c2985c67980/edit
        - strong: E2E AI 原子草稿
        - text: 草稿 暂无描述 最后更新 2026/09/21 11:37
      - button "复制大屏 E2E AI 原子草稿": 复制
      - button "删除大屏 E2E AI 原子草稿": 删除
    - article:
      - link "数字人发布 1789961873359 已发布 暂无描述 最后更新 2026/09/21 11:37":
        - /url: /studio/screens/c51e911b-f676-423e-99d2-277599133db8/edit
        - strong: 数字人发布 1789961873359
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:37
      - button "复制大屏 数字人发布 1789961873359": 复制
      - button "删除大屏 数字人发布 1789961873359": 删除
    - article:
      - link "结构化话术持久化 1789961877288 已发布 暂无描述 最后更新 2026/09/21 11:37":
        - /url: /studio/screens/ea13b953-91d0-4bce-ae15-1b80b29a5172/edit
        - strong: 结构化话术持久化 1789961877288
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:37
      - button "复制大屏 结构化话术持久化 1789961877288": 复制
      - button "删除大屏 结构化话术持久化 1789961877288": 删除
    - article:
      - link "数字人 TTS 闭环 1789961879427 已发布 暂无描述 最后更新 2026/09/21 11:38":
        - /url: /studio/screens/bbda80ba-093b-4d34-ad19-f2f9d63a9292/edit
        - strong: 数字人 TTS 闭环 1789961879427
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:38
      - button "复制大屏 数字人 TTS 闭环 1789961879427": 复制
      - button "删除大屏 数字人 TTS 闭环 1789961879427": 删除
    - article:
      - link "数字人嵌入 1789961890481 已发布 暂无描述 最后更新 2026/09/21 11:38":
        - /url: /studio/screens/603050a7-ba0c-4d78-89c2-c9eaddc41fa6/edit
        - strong: 数字人嵌入 1789961890481
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:38
      - button "复制大屏 数字人嵌入 1789961890481": 复制
      - button "删除大屏 数字人嵌入 1789961890481": 删除
    - article:
      - link "数字人跨源嵌入 1789961891849 已发布 暂无描述 最后更新 2026/09/21 11:38":
        - /url: /studio/screens/3c1c255c-974d-4488-b1c2-619847b5170f/edit
        - strong: 数字人跨源嵌入 1789961891849
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:38
      - button "复制大屏 数字人跨源嵌入 1789961891849": 复制
      - button "删除大屏 数字人跨源嵌入 1789961891849": 删除
    - article:
      - link "数字人访问撤销 1789961893417 已发布 暂无描述 最后更新 2026/09/21 11:38":
        - /url: /studio/screens/040fa544-65b3-4698-b704-475164038553/edit
        - strong: 数字人访问撤销 1789961893417
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:38
      - button "复制大屏 数字人访问撤销 1789961893417": 复制
      - button "删除大屏 数字人访问撤销 1789961893417": 删除
    - article:
      - link "真实视频播报 1789961897121 已发布 暂无描述 最后更新 2026/09/21 11:38":
        - /url: /studio/screens/d321370a-2462-4a14-990a-ea9e1724de55/edit
        - strong: 真实视频播报 1789961897121
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:38
      - button "复制大屏 真实视频播报 1789961897121": 复制
      - button "删除大屏 真实视频播报 1789961897121": 删除
    - article:
      - link "资源版本测试 1789961905880 已发布 暂无描述 最后更新 2026/09/21 11:38":
        - /url: /studio/screens/e2955248-077a-4bbb-bd9d-1aa117618adc/edit
        - strong: 资源版本测试 1789961905880
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:38
      - button "复制大屏 资源版本测试 1789961905880": 复制
      - button "删除大屏 资源版本测试 1789961905880": 删除
    - article:
      - link "Plugin firefox 1789961928884 已发布 暂无描述 最后更新 2026/09/21 11:38":
        - /url: /studio/screens/041a3e06-fd2a-4e7e-b2b7-078cd5faceaf/edit
        - strong: Plugin firefox 1789961928884
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:38
      - button "复制大屏 Plugin firefox 1789961928884": 复制
      - button "删除大屏 Plugin firefox 1789961928884": 删除
    - article:
      - link "E2E 第一阶段模板入口 草稿 标题、核心指标、趋势、排行和明细表的通用起始布局。 最后更新 2026/09/21 11:39":
        - /url: /studio/screens/7c6441b0-4817-4570-b09c-ad314fc6f198/edit
        - strong: E2E 第一阶段模板入口
        - text: 草稿 标题、核心指标、趋势、排行和明细表的通用起始布局。 最后更新 2026/09/21 11:39
      - button "复制大屏 E2E 第一阶段模板入口": 复制
      - button "删除大屏 E2E 第一阶段模板入口": 删除
    - article:
      - link "E2E 第一阶段交替创作 已发布 暂无描述 最后更新 2026/09/21 11:39":
        - /url: /studio/screens/e4ff2538-9f25-40e7-8ac7-3fbb20a05b59/edit
        - strong: E2E 第一阶段交替创作
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:39
      - button "复制大屏 E2E 第一阶段交替创作": 复制
      - button "删除大屏 E2E 第一阶段交替创作": 删除
    - article:
      - link "E2E 第一阶段访问限制 已发布 暂无描述 最后更新 2026/09/21 11:39":
        - /url: /studio/screens/801bd7b8-8309-4a39-8f69-649927d7efd5/edit
        - strong: E2E 第一阶段访问限制
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:39
      - button "复制大屏 E2E 第一阶段访问限制": 复制
      - button "删除大屏 E2E 第一阶段访问限制": 删除
    - article:
      - link "E2E 窄视口编辑器 草稿 暂无描述 最后更新 2026/09/21 11:39":
        - /url: /studio/screens/30fc260a-5f7e-4ff2-a807-6c0699c6dd06/edit
        - strong: E2E 窄视口编辑器
        - text: 草稿 暂无描述 最后更新 2026/09/21 11:39
      - button "复制大屏 E2E 窄视口编辑器": 复制
      - button "删除大屏 E2E 窄视口编辑器": 删除
    - article:
      - link "协作权限 firefox-1789961964312 草稿 暂无描述 最后更新 2026/09/21 11:39":
        - /url: /studio/screens/c0e8ba41-26b0-4dc2-a9a4-c3a1f51add9b/edit
        - strong: 协作权限 firefox-1789961964312
        - text: 草稿 暂无描述 最后更新 2026/09/21 11:39
      - button "复制大屏 协作权限 firefox-1789961964312": 复制
      - button "删除大屏 协作权限 firefox-1789961964312": 删除
    - article:
      - link "E2E 运营大屏 草稿 暂无描述 最后更新 2026/09/21 11:39":
        - /url: /studio/screens/097312f2-a80a-4ae5-bee9-df702a502876/edit
        - strong: E2E 运营大屏
        - text: 草稿 暂无描述 最后更新 2026/09/21 11:39
      - button "复制大屏 E2E 运营大屏": 复制
      - button "删除大屏 E2E 运营大屏": 删除
    - article:
      - link "E2E 多选拖拽 草稿 暂无描述 最后更新 2026/09/21 11:39":
        - /url: /studio/screens/f7fb2bdc-b5df-4270-b8e9-af04fa8c6926/edit
        - strong: E2E 多选拖拽
        - text: 草稿 暂无描述 最后更新 2026/09/21 11:39
      - button "复制大屏 E2E 多选拖拽": 复制
      - button "删除大屏 E2E 多选拖拽": 删除
    - article:
      - link "E2E 深色播放 已发布 暂无描述 最后更新 2026/09/21 11:39":
        - /url: /studio/screens/ccc31183-baac-4e54-a788-1f361a360931/edit
        - strong: E2E 深色播放
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:39
      - button "复制大屏 E2E 深色播放": 复制
      - button "删除大屏 E2E 深色播放": 删除
    - article:
      - link "E2E 浅色播放 已发布 暂无描述 最后更新 2026/09/21 11:39":
        - /url: /studio/screens/d09d55a2-387d-40e1-a744-95e2165bc9d8/edit
        - strong: E2E 浅色播放
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:39
      - button "复制大屏 E2E 浅色播放": 复制
      - button "删除大屏 E2E 浅色播放": 删除
    - article:
      - link "E2E 组件错误隔离 已发布 暂无描述 最后更新 2026/09/21 11:39":
        - /url: /studio/screens/d0c1e66d-502a-4a46-a716-80f04381bc0c/edit
        - strong: E2E 组件错误隔离
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:39
      - button "复制大屏 E2E 组件错误隔离": 复制
      - button "删除大屏 E2E 组件错误隔离": 删除
    - article:
      - link "E2E 直连嵌入 已发布 暂无描述 最后更新 2026/09/21 11:39":
        - /url: /studio/screens/3fd3777e-da69-404e-a3ea-25a218792e2b/edit
        - strong: E2E 直连嵌入
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:39
      - button "复制大屏 E2E 直连嵌入": 复制
      - button "删除大屏 E2E 直连嵌入": 删除
    - article:
      - link "E2E 安全嵌入 已发布 暂无描述 最后更新 2026/09/21 11:39":
        - /url: /studio/screens/41131c4a-7de7-4a37-92aa-d5e3e74cb74d/edit
        - strong: E2E 安全嵌入
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:39
      - button "复制大屏 E2E 安全嵌入": 复制
      - button "删除大屏 E2E 安全嵌入": 删除
    - dialog "AI 生成大屏":
      - heading "AI 生成大屏" [level=2]
      - paragraph: 先生成草稿，确认后再创建到工作区。
      - button "关闭"
      - text: 大屏名称
      - textbox "大屏名称":
        - /placeholder: 例如：区域经营驾驶舱
        - text: E2E AI 原子草稿
      - text: 需求描述
      - textbox "需求描述":
        - /placeholder: 例如：做一个区域经营总览，突出销售额、订单数、趋势和区域对比。
        - text: E2E_MODE:valid-screen 生成经营总览
      - group "数据集":
        - text: 数据集
        - checkbox "E2E 大屏销售数据 1082dfa0-48e5-4525-80ec-4890245f26d8" [checked]
        - strong: E2E 大屏销售数据
        - code: 1082dfa0-48e5-4525-80ec-4890245f26d8
        - checkbox "高价值销售 64c67221-cec3-43e5-a74f-d853c615e5c0"
        - strong: 高价值销售
        - code: 64c67221-cec3-43e5-a74f-d853c615e5c0
      - button "取消"
      - button "生成草稿"
      - region "AI 大屏草稿结果":
        - heading "生成结果" [level=3]
        - paragraph: E2E AI 已生成标题和区域销售额图表。
        - text: 画布 1920 × 1080 组件 2 E2E AI 经营总览
        - button "创建草稿并进入编辑器"
```

# Test source

```ts
  1   | import { expect, test } from "@playwright/test";
  2   | 
  3   | import {
  4   |   apiGet,
  5   |   authenticate,
  6   |   ensureAnalyticsDataset,
  7   |   type ScreenRecord,
  8   | } from "./helpers.js";
  9   | 
  10  | test("AI screen preview cancels cleanly and confirms with one atomic create", async ({
  11  |   page,
  12  | }) => {
  13  |   await authenticate(page);
  14  |   const dataset = await ensureAnalyticsDataset(page);
  15  |   const initial = await apiGet<ScreenRecord[]>(page, "/api/admin/screens");
  16  |   const requests: Array<{ method: string; path: string }> = [];
  17  |   page.on("request", (request) => {
  18  |     const path = new URL(request.url()).pathname;
  19  |     if (path.startsWith("/api/admin/screens") || path.endsWith("/publish")) {
  20  |       requests.push({ method: request.method(), path });
  21  |     }
  22  |   });
  23  | 
  24  |   const generate = async (name: string, question: string) => {
  25  |     await page.getByRole("button", { name: "AI 生成大屏" }).first().click();
  26  |     const dialog = page.getByRole("dialog", { name: "AI 生成大屏" });
  27  |     await dialog.getByLabel("大屏名称").fill(name);
  28  |     await dialog.getByLabel("需求描述").fill(question);
  29  |     await dialog
  30  |       .locator("label", { hasText: dataset.id })
  31  |       .getByRole("checkbox")
  32  |       .check();
  33  |     await dialog.getByRole("button", { name: "生成草稿" }).click();
  34  |     return dialog;
  35  |   };
  36  | 
  37  |   await page.goto("/studio/screens");
  38  |   let dialog = await generate(
  39  |     "E2E AI 取消草稿",
  40  |     "E2E_MODE:valid-screen 生成经营总览",
  41  |   );
  42  |   await expect(dialog.getByLabel("AI 大屏草稿预览")).toBeVisible();
  43  |   await expect(dialog.getByText("E2E AI 已生成标题和区域销售额图表")).toBeVisible();
  44  |   expect(
  45  |     requests.filter(
  46  |       (item) => item.method === "POST" && item.path === "/api/admin/screens",
  47  |     ),
  48  |   ).toHaveLength(0);
  49  |   await dialog.getByRole("button", { name: "取消" }).click();
  50  |   await expect(dialog).toBeHidden();
  51  |   expect(await apiGet<ScreenRecord[]>(page, "/api/admin/screens")).toHaveLength(
  52  |     initial.length,
  53  |   );
  54  | 
  55  |   dialog = await generate(
  56  |     "E2E AI 原子草稿",
  57  |     "E2E_MODE:valid-screen 生成经营总览",
  58  |   );
  59  |   await expect(dialog.getByLabel("AI 大屏草稿预览")).toBeVisible();
  60  |   await dialog
  61  |     .getByRole("button", { name: "创建草稿并进入编辑器" })
  62  |     .click();
> 63  |   await expect(page.getByLabel("大屏编辑器")).toBeVisible();
      |                                          ^ Error: expect(locator).toBeVisible() failed
  64  |   await expect(page.getByText("E2E AI 经营总览")).toBeVisible();
  65  | 
  66  |   const createRequests = requests.filter(
  67  |     (item) => item.method === "POST" && item.path === "/api/admin/screens",
  68  |   );
  69  |   expect(createRequests).toHaveLength(1);
  70  |   expect(
  71  |     requests.some(
  72  |       (item) => item.method === "PATCH" && item.path.startsWith("/api/admin/screens/"),
  73  |     ),
  74  |   ).toBe(false);
  75  |   expect(requests.some((item) => item.path.endsWith("/publish"))).toBe(false);
  76  | 
  77  |   await page.reload();
  78  |   await expect(page.getByText("E2E AI 经营总览")).toBeVisible();
  79  | });
  80  | 
  81  | test("invalid AI screens never create a draft", async ({ page }) => {
  82  |   await authenticate(page);
  83  |   const dataset = await ensureAnalyticsDataset(page);
  84  |   const initial = await apiGet<ScreenRecord[]>(page, "/api/admin/screens");
  85  |   await page.goto("/studio/screens");
  86  |   await page.getByRole("button", { name: "AI 生成大屏" }).first().click();
  87  |   const dialog = page.getByRole("dialog", { name: "AI 生成大屏" });
  88  |   await dialog.getByLabel("大屏名称").fill("E2E 非法 AI 草稿");
  89  |   await dialog.getByLabel("需求描述").fill("E2E_MODE:invalid-field");
  90  |   await dialog
  91  |     .locator("label", { hasText: dataset.id })
  92  |     .getByRole("checkbox")
  93  |     .check();
  94  |   await dialog.getByRole("button", { name: "生成草稿" }).click();
  95  |   await expect(dialog).toContainText("The AI analysis request is invalid");
  96  | 
  97  |   await dialog
  98  |     .getByLabel("需求描述")
  99  |     .fill("E2E_MODE:valid-screen E2E_UNAUTHORIZED_DATASET");
  100 |   await dialog.getByRole("button", { name: "生成草稿" }).click();
  101 |   await expect(dialog).toContainText("The AI analysis request is invalid");
  102 |   expect(await apiGet<ScreenRecord[]>(page, "/api/admin/screens")).toHaveLength(
  103 |     initial.length,
  104 |   );
  105 | });
  106 | 
```