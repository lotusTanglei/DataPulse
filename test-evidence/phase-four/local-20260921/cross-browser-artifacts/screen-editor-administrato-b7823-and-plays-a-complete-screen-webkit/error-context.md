# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: screen-editor.spec.ts >> administrator builds, previews, publishes, and plays a complete screen
- Location: e2e/screen-editor.spec.ts:14:1

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
    - article:
      - link "数字人发布 1789962032984 已发布 暂无描述 最后更新 2026/09/21 11:40":
        - /url: /studio/screens/ccef2eef-6619-4e8a-bfeb-c7482f807d5e/edit
        - strong: 数字人发布 1789962032984
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:40
      - button "复制大屏 数字人发布 1789962032984": 复制
      - button "删除大屏 数字人发布 1789962032984": 删除
    - article:
      - link "结构化话术持久化 1789962035495 已发布 暂无描述 最后更新 2026/09/21 11:40":
        - /url: /studio/screens/c4f1c52b-a063-4e4c-b526-afcaa2643979/edit
        - strong: 结构化话术持久化 1789962035495
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:40
      - button "复制大屏 结构化话术持久化 1789962035495": 复制
      - button "删除大屏 结构化话术持久化 1789962035495": 删除
    - article:
      - link "数字人 TTS 闭环 1789962037336 已发布 暂无描述 最后更新 2026/09/21 11:40":
        - /url: /studio/screens/f3dd4381-fe3b-4030-94c7-f27f3b190422/edit
        - strong: 数字人 TTS 闭环 1789962037336
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:40
      - button "复制大屏 数字人 TTS 闭环 1789962037336": 复制
      - button "删除大屏 数字人 TTS 闭环 1789962037336": 删除
    - article:
      - link "数字人嵌入 1789962041243 已发布 暂无描述 最后更新 2026/09/21 11:40":
        - /url: /studio/screens/fc48d75e-b38e-4bca-ae4e-7770578c16fb/edit
        - strong: 数字人嵌入 1789962041243
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:40
      - button "复制大屏 数字人嵌入 1789962041243": 复制
      - button "删除大屏 数字人嵌入 1789962041243": 删除
    - article:
      - link "数字人跨源嵌入 1789962042251 已发布 暂无描述 最后更新 2026/09/21 11:40":
        - /url: /studio/screens/476c74c5-decb-4c1c-9a8f-18d1637b6df4/edit
        - strong: 数字人跨源嵌入 1789962042251
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:40
      - button "复制大屏 数字人跨源嵌入 1789962042251": 复制
      - button "删除大屏 数字人跨源嵌入 1789962042251": 删除
    - article:
      - link "数字人访问撤销 1789962043870 已发布 暂无描述 最后更新 2026/09/21 11:40":
        - /url: /studio/screens/9f22b79d-58d2-4af0-a159-c565de541180/edit
        - strong: 数字人访问撤销 1789962043870
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:40
      - button "复制大屏 数字人访问撤销 1789962043870": 复制
      - button "删除大屏 数字人访问撤销 1789962043870": 删除
    - article:
      - link "真实视频播报 1789962045751 已发布 暂无描述 最后更新 2026/09/21 11:40":
        - /url: /studio/screens/e5f3a3a3-b644-4bc7-b686-7f7934b95c8e/edit
        - strong: 真实视频播报 1789962045751
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:40
      - button "复制大屏 真实视频播报 1789962045751": 复制
      - button "删除大屏 真实视频播报 1789962045751": 删除
    - article:
      - link "资源版本测试 1789962053466 已发布 暂无描述 最后更新 2026/09/21 11:40":
        - /url: /studio/screens/4f50188f-0219-4339-a863-3de3fd1c9903/edit
        - strong: 资源版本测试 1789962053466
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:40
      - button "复制大屏 资源版本测试 1789962053466": 复制
      - button "删除大屏 资源版本测试 1789962053466": 删除
    - article:
      - link "Plugin webkit 1789962080153 已发布 暂无描述 最后更新 2026/09/21 11:41":
        - /url: /studio/screens/9d484436-6607-4952-989a-75b27f863c0b/edit
        - strong: Plugin webkit 1789962080153
        - text: 已发布 暂无描述 最后更新 2026/09/21 11:41
      - button "复制大屏 Plugin webkit 1789962080153": 复制
      - button "删除大屏 Plugin webkit 1789962080153": 删除
    - article:
      - link "协作权限 webkit-1789962148721 草稿 暂无描述 最后更新 2026/09/21 11:42":
        - /url: /studio/screens/e043dd03-34ab-441b-926d-5d37f37a1fbd/edit
        - strong: 协作权限 webkit-1789962148721
        - text: 草稿 暂无描述 最后更新 2026/09/21 11:42
      - button "复制大屏 协作权限 webkit-1789962148721": 复制
      - button "删除大屏 协作权限 webkit-1789962148721": 删除
    - dialog "新建大屏":
      - heading "新建大屏" [level=2]
      - paragraph: 创建后将直接进入编辑器。
      - button "关闭"
      - text: 大屏名称
      - textbox "大屏名称 A screen with this name already exists.":
        - /placeholder: 例如：运营总览
        - text: E2E 运营大屏
      - text: A screen with this name already exists.
      - button "取消"
      - button "创建并编辑"
```

# Test source

```ts
  1   | import { expect, test } from "@playwright/test";
  2   | 
  3   | import {
  4   |   apiGet,
  5   |   apiPatch,
  6   |   authenticate,
  7   |   configureNineComponentDocument,
  8   |   ensureAnalyticsDataset,
  9   |   generateDisplayKey,
  10  |   type ScreenRecord,
  11  |   uploadVisualAssets,
  12  | } from "./helpers.js";
  13  | 
  14  | test("administrator builds, previews, publishes, and plays a complete screen", async ({
  15  |   page,
  16  | }, testInfo) => {
  17  |   test.setTimeout(75_000);
  18  |   await page.setViewportSize({ width: 1920, height: 1080 });
  19  |   await authenticate(page);
  20  |   const dataset = await ensureAnalyticsDataset(page);
  21  |   const assets = await uploadVisualAssets(page);
  22  | 
  23  |   await page.goto("/studio/screens");
  24  |   await page.getByRole("button", { name: /新建大屏/ }).first().click();
  25  |   await page.getByLabel("大屏名称").fill("E2E 运营大屏");
  26  |   await page.getByRole("button", { name: "创建并编辑" }).click();
> 27  |   await expect(page.getByLabel("大屏编辑器")).toBeVisible();
      |                                          ^ Error: expect(locator).toBeVisible() failed
  28  | 
  29  |   const library = page.getByLabel("组件库");
  30  |   for (const label of [
  31  |     "文本",
  32  |     "图片",
  33  |     "指标",
  34  |     "表格",
  35  |     "进度",
  36  |     "折线图",
  37  |     "柱状图",
  38  |     "饼图",
  39  |     "地图",
  40  |   ]) {
  41  |     await library
  42  |       .getByRole("button", { name: new RegExp(`^${label}(?:\\s+数据)?$`) })
  43  |       .click();
  44  |   }
  45  |   const layersPanel = page.locator('section.layers-panel[aria-label="图层"]');
  46  |   const layers = layersPanel.locator("[data-layer-id]");
  47  |   await expect(layers).toHaveCount(9);
  48  | 
  49  |   const textLayer = layers.filter({ hasText: "文本" }).first();
  50  |   await textLayer.locator("span").first().click();
  51  |   await expect(textLayer).toHaveClass(/is-selected/);
  52  |   await page.getByLabel("文本内容").fill("编辑器自动保存验证");
  53  |   await page.getByLabel("文本内容").blur();
  54  | 
  55  |   const selected = page.locator(".editor-canvas-component.is-selected");
  56  |   const selectedBox = await selected.boundingBox();
  57  |   expect(selectedBox).not.toBeNull();
  58  |   await page.mouse.move(
  59  |     selectedBox!.x + selectedBox!.width / 2,
  60  |     selectedBox!.y + selectedBox!.height / 2,
  61  |   );
  62  |   await page.mouse.down();
  63  |   await page.mouse.move(
  64  |     selectedBox!.x + selectedBox!.width / 2 + 40,
  65  |     selectedBox!.y + selectedBox!.height / 2 + 20,
  66  |     { steps: 5 },
  67  |   );
  68  |   await page.mouse.up();
  69  |   const movedFrame = await selected.evaluate((element) => {
  70  |     const target = element as HTMLElement;
  71  |     return {
  72  |       x: Number.parseFloat(target.style.left),
  73  |       y: Number.parseFloat(target.style.top),
  74  |     };
  75  |   });
  76  |   expect(movedFrame.x).toBeGreaterThan(40);
  77  |   expect(movedFrame.y).toBeGreaterThan(40);
  78  | 
  79  |   const resizeHandle = page.locator(".moveable-control-box .moveable-e");
  80  |   await expect(resizeHandle).toBeVisible();
  81  |   const handleBox = await resizeHandle.boundingBox();
  82  |   expect(handleBox).not.toBeNull();
  83  |   await page.mouse.move(
  84  |     handleBox!.x + handleBox!.width / 2,
  85  |     handleBox!.y + handleBox!.height / 2,
  86  |   );
  87  |   await page.mouse.down();
  88  |   await page.mouse.move(
  89  |     handleBox!.x + handleBox!.width / 2 + 60,
  90  |     handleBox!.y + handleBox!.height / 2,
  91  |     { steps: 5 },
  92  |   );
  93  |   await page.mouse.up();
  94  | 
  95  |   await page.getByRole("button", { name: "撤销" }).click();
  96  |   await page.getByRole("button", { name: "重做" }).click();
  97  |   await expect(
  98  |     page.getByLabel("编辑器工具栏").getByText("已保存"),
  99  |   ).toBeVisible({ timeout: 10_000 });
  100 | 
  101 |   await page.reload();
  102 |   await expect(layersPanel.locator("[data-layer-id]")).toHaveCount(9);
  103 |   const reloadedTextLayer = layersPanel
  104 |     .locator("[data-layer-id]")
  105 |     .filter({ hasText: "文本" })
  106 |     .first();
  107 |   await reloadedTextLayer.locator("span").first().click();
  108 |   await expect(reloadedTextLayer).toHaveClass(/is-selected/);
  109 |   await expect(page.getByLabel("文本内容")).toHaveValue(
  110 |     "编辑器自动保存验证",
  111 |   );
  112 | 
  113 |   const screenId = page.url().match(/\/screens\/([^/]+)\/edit/)?.[1];
  114 |   expect(screenId).toBeTruthy();
  115 |   const current = await apiGet<ScreenRecord>(
  116 |     page,
  117 |     `/api/admin/screens/${screenId}`,
  118 |   );
  119 |   const configured = configureNineComponentDocument(
  120 |     current.draft_document,
  121 |     dataset.id,
  122 |     assets,
  123 |   );
  124 |   await apiPatch<ScreenRecord>(
  125 |     page,
  126 |     `/api/admin/screens/${screenId}`,
  127 |     {
```