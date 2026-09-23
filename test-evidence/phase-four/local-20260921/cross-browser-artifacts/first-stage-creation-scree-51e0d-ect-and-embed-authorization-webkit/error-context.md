# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: first-stage-creation.spec.ts >> screen access policy controls direct and embed authorization
- Location: e2e/first-stage-creation.spec.ts:136:1

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
    - dialog "新建大屏":
      - heading "新建大屏" [level=2]
      - paragraph: 创建后将直接进入编辑器。
      - button "关闭"
      - text: 大屏名称
      - textbox "大屏名称 A screen with this name already exists.":
        - /placeholder: 例如：运营总览
        - text: E2E 第一阶段访问限制
      - text: A screen with this name already exists.
      - button "取消"
      - button "创建并编辑"
```

# Test source

```ts
  44  |   await page.getByLabel("大屏名称").fill("E2E 第一阶段交替创作");
  45  |   await page.getByRole("button", { name: "创建并编辑" }).click();
  46  |   await expect(page.getByLabel("大屏编辑器")).toBeVisible();
  47  | 
  48  |   await page
  49  |     .getByLabel("组件库")
  50  |     .getByRole("button", { name: "文本", exact: true })
  51  |     .click();
  52  |   const layersPanel = page.locator('section.layers-panel[aria-label="图层"]');
  53  |   const textLayer = layersPanel
  54  |     .locator("[data-layer-id]")
  55  |     .filter({ hasText: "文本" });
  56  |   await expect(textLayer).toHaveCount(1);
  57  |   await textLayer.locator("span").first().click();
  58  |   await expect(textLayer).toHaveClass(/is-selected/);
  59  |   const textInput = page.getByLabel("文本内容");
  60  |   await textInput.fill("手工修改后的标题");
  61  |   await textInput.blur();
  62  |   await expect(textInput).toHaveValue("手工修改后的标题");
  63  | 
  64  |   const aiPanel = page.getByLabel("AI 修改");
  65  |   const editPanelStyles = await aiPanel.evaluate((element) => {
  66  |     const panel = getComputedStyle(element);
  67  |     const description = element.querySelector(".ai-edit-panel__header p");
  68  |     const descriptionStyle = description ? getComputedStyle(description) : null;
  69  |     return {
  70  |       background: panel.backgroundColor,
  71  |       descriptionColor: descriptionStyle?.color ?? "",
  72  |     };
  73  |   });
  74  |   expect(editPanelStyles).toEqual({
  75  |     background: "rgb(255, 255, 255)",
  76  |     descriptionColor: "rgb(95, 94, 91)",
  77  |   });
  78  |   await aiPanel
  79  |     .getByLabel("修改要求")
  80  |     .fill("E2E_MODE:edit-title 把选中的标题改成 AI 版本");
  81  |   await aiPanel.getByRole("button", { name: "生成修改预览" }).click();
  82  |   await expect(page.getByLabel("AI 修改预览")).toBeVisible();
  83  |   await expect(page.getByText("E2E AI 已修改选中标题。", { exact: true })).toBeVisible();
  84  |   expect(publishRequests).toHaveLength(0);
  85  |   await expect(textInput).toHaveValue("手工修改后的标题");
  86  | 
  87  |   await page.getByRole("button", { name: "应用修改" }).click();
  88  |   await expect(textInput).toHaveValue("E2E AI 局部修改标题");
  89  | 
  90  |   await page.getByRole("button", { name: "撤销" }).click();
  91  |   await expect(textInput).toHaveValue("手工修改后的标题");
  92  |   await page.getByRole("button", { name: "重做" }).click();
  93  |   await expect(textInput).toHaveValue("E2E AI 局部修改标题");
  94  | 
  95  |   await textInput.fill("第二次手工修改标题");
  96  |   await textInput.blur();
  97  |   await aiPanel
  98  |     .getByLabel("修改要求")
  99  |     .fill("E2E_MODE:edit-title 再次基于最新画布调整标题");
  100 |   await aiPanel.getByRole("button", { name: "生成修改预览" }).click();
  101 |   await expect(page.getByLabel("AI 修改预览")).toBeVisible();
  102 |   await expect(textInput).toHaveValue("第二次手工修改标题");
  103 |   await page.getByRole("button", { name: "应用修改" }).click();
  104 |   await expect(textInput).toHaveValue("E2E AI 局部修改标题");
  105 | 
  106 |   await expect(page.getByLabel("编辑器工具栏").getByText("已保存")).toBeVisible({
  107 |     timeout: 12_000,
  108 |   });
  109 |   expect(publishRequests).toHaveLength(0);
  110 | 
  111 |   await page.getByRole("button", { name: "发布", exact: true }).click();
  112 |   await expect(page.getByRole("heading", { name: "确认发布大屏" })).toBeVisible();
  113 |   await page.getByRole("button", { name: "确认发布" }).click();
  114 |   await expect(page.getByText("发布完成")).toBeVisible();
  115 |   expect(publishRequests).toHaveLength(1);
  116 | 
  117 |   const screenId = page.url().match(/\/screens\/([^/]+)\/edit/)?.[1];
  118 |   expect(screenId).toBeTruthy();
  119 |   const stored = await apiGet<ScreenRecord>(
  120 |     page,
  121 |     `/api/admin/screens/${screenId}`,
  122 |   );
  123 |   expect(stored.draft_document.components?.[0]?.props?.text).toBe(
  124 |     "E2E AI 局部修改标题",
  125 |   );
  126 |   expect(stored.published_document?.components?.[0]?.props?.text).toBe(
  127 |     "E2E AI 局部修改标题",
  128 |   );
  129 | 
  130 |   const displayKey = await generateDisplayKey(page, screenId!);
  131 |   await page.goto(`/play/${screenId}?key=[REDACTED]`);
  132 |   await expect(page).toHaveURL(new RegExp(`/play/${screenId}$`));
  133 |   await expect(page.getByText("E2E AI 局部修改标题")).toBeVisible();
  134 | });
  135 | 
  136 | test("screen access policy controls direct and embed authorization", async ({
  137 |   page,
  138 | }) => {
  139 |   await authenticate(page);
  140 |   await page.goto("/studio/screens");
  141 |   await page.getByRole("button", { name: /新建大屏/ }).first().click();
  142 |   await page.getByLabel("大屏名称").fill("E2E 第一阶段访问限制");
  143 |   await page.getByRole("button", { name: "创建并编辑" }).click();
> 144 |   await expect(page.getByLabel("大屏编辑器")).toBeVisible();
      |                                          ^ Error: expect(locator).toBeVisible() failed
  145 | 
  146 |   const screenId = page.url().match(/\/screens\/([^/]+)\/edit/)?.[1];
  147 |   expect(screenId).toBeTruthy();
  148 |   await page.getByRole("button", { name: "发布", exact: true }).click();
  149 |   await expect(page.getByRole("heading", { name: "确认发布大屏" })).toBeVisible();
  150 |   await page.getByRole("button", { name: "确认发布" }).click();
  151 |   await expect(page.getByText("发布完成")).toBeVisible();
  152 | 
  153 |   const accessPanel = page.getByLabel("访问限制");
  154 |   await accessPanel
  155 |     .getByLabel("允许的域名 / Origin")
  156 |     .fill("https://safe.example.com");
  157 |   await accessPanel.getByRole("button", { name: "保存访问限制" }).click();
  158 |   await expect(accessPanel.getByRole("button", { name: "保存访问限制" })).toBeEnabled();
  159 |   const policy = await apiGet<ScreenRecord>(
  160 |     page,
  161 |     `/api/admin/screens/${screenId}`,
  162 |   );
  163 |   expect(policy.access_policy).toEqual({
  164 |     allowed_origins: ["https://safe.example.com"],
  165 |     allowed_ips: [],
  166 |   });
  167 | 
  168 |   await page.reload();
  169 |   await expect(page.getByLabel("访问限制")).toBeVisible();
  170 | 
  171 |   const saved = await apiPatch<ScreenRecord>(
  172 |     page,
  173 |     `/api/admin/screens/${screenId}`,
  174 |     {
  175 |       draft_document: policy.draft_document,
  176 |       expected_revision: policy.draft_revision,
  177 |     },
  178 |   );
  179 |   const published = await apiPost<ScreenRecord>(
  180 |     page,
  181 |     `/api/admin/screens/${screenId}/publish`,
  182 |     { expected_revision: saved.draft_revision },
  183 |   );
  184 |   const displayKey = await generateDisplayKey(page, published.id);
  185 |   const denied = await page.request.post(
  186 |     `${appOrigin()}/api/player/screens/${published.id}/session`,
  187 |     {
  188 |       headers: { Origin: "https://evil.example.com" },
  189 |       data: { key: displayKey },
  190 |     },
  191 |   );
  192 |   expect(denied.status()).toBe(403);
  193 |   const allowed = await page.request.post(
  194 |     `${appOrigin()}/api/player/screens/${published.id}/session`,
  195 |     {
  196 |       headers: { Origin: "https://safe.example.com" },
  197 |       data: { key: displayKey },
  198 |     },
  199 |   );
  200 |   expect(allowed.status()).toBe(204);
  201 | 
  202 |   const ipPolicy = await apiPatch<ScreenRecord>(
  203 |     page,
  204 |     `/api/admin/screens/${screenId}/access-policy`,
  205 |     {
  206 |       allowed_origins: ["https://safe.example.com", appOrigin()],
  207 |       allowed_ips: ["127.0.0.1/32"],
  208 |     },
  209 |   );
  210 |   expect(ipPolicy.access_policy?.allowed_ips).toEqual(["127.0.0.1/32"]);
  211 |   const ipAllowed = await page.request.post(
  212 |     `${appOrigin()}/api/player/screens/${published.id}/session`,
  213 |     {
  214 |       headers: { Origin: "https://evil.example.com" },
  215 |       data: { key: displayKey },
  216 |     },
  217 |   );
  218 |   expect(ipAllowed.status()).toBe(204);
  219 | 
  220 |   const embedKey = await apiPost<{ api_key: string }>(page, "/api/admin/embed/api-key");
  221 |   const ticket = await apiPost<{ ticket: string }>(
  222 |     page,
  223 |     "/api/embed/tickets",
  224 |     {
  225 |       screen_id: published.id,
  226 |       allowed_origin: "https://safe.example.com",
  227 |       lifetime_seconds: 3600,
  228 |     },
  229 |     embedKey.api_key,
  230 |   );
  231 |   const backendOrigin = `http://127.0.0.1:${loadRuntimeConfig().backendPort}`;
  232 | 
  233 |   const iframeTicket = await apiPost<{ ticket: string }>(
  234 |     page,
  235 |     "/api/embed/tickets",
  236 |     {
  237 |       screen_id: published.id,
  238 |       allowed_origin: appOrigin(),
  239 |       lifetime_seconds: 3600,
  240 |     },
  241 |     embedKey.api_key,
  242 |   );
  243 |   await page.goto(
  244 |     `/e2e/embed-host.html?screen=${encodeURIComponent(published.id)}&ticket=[REDACTED]`,
```