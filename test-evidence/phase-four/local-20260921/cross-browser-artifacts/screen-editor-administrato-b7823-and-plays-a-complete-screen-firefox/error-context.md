# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: screen-editor.spec.ts >> administrator builds, previews, publishes, and plays a complete screen
- Location: e2e/screen-editor.spec.ts:14:1

# Error details

```
Error: expect(page).toHaveScreenshot(expected) failed

  2063 pixels (ratio 0.01 of all image pixels) are different.

  Snapshot: editor-shell-firefox.png

Call log:
  - Expect "toHaveScreenshot(editor-shell-firefox.png)" with timeout 8000ms
    - verifying given screenshot expectation
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - 14630 pixels (ratio 0.01 of all image pixels) are different.
  - waiting 100ms before taking screenshot
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - 11808 pixels (ratio 0.01 of all image pixels) are different.
  - waiting 250ms before taking screenshot
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - 1273 pixels (ratio 0.01 of all image pixels) are different.
  - waiting 500ms before taking screenshot
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - captured a stable screenshot
  - 2063 pixels (ratio 0.01 of all image pixels) are different.

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
  - main [ref=f2e65]:
    - generic [ref=f2e66]:
      - navigation "面包屑" [ref=f2e67]:
        - generic [ref=f2e68]: DataPulse
        - generic [ref=f2e69]: /
        - strong [ref=f2e70]: 大屏编辑器
      - generic [ref=f2e71]: 本地工作区
    - region "大屏编辑器" [ref=f2e73]:
      - generic "编辑器工具栏" [ref=f2e74]:
        - link "返回大屏列表" [ref=f2e75] [cursor=pointer]:
          - /url: /studio/screens
        - generic [ref=f2e79]:
          - strong [ref=f2e80]: E2E 运营大屏
          - generic [ref=f2e81]: 已保存
        - button "左对齐" [disabled] [ref=f2e82]
        - button "水平居中" [disabled] [ref=f2e87]
        - button "右对齐" [disabled] [ref=f2e92]
        - button "组合" [disabled] [ref=f2e97]
        - button "取消组合" [disabled] [ref=f2e98]
        - button "顶部对齐" [disabled] [ref=f2e99]
        - button "垂直居中" [disabled] [ref=f2e106]
        - button "底部对齐" [disabled] [ref=f2e113]
        - button "水平等间距" [disabled] [ref=f2e120]
        - button "垂直等间距" [disabled] [ref=f2e123]
        - button "网格" [ref=f2e126] [cursor=pointer]
        - button "吸附" [ref=f2e133] [cursor=pointer]
        - button "缩小" [ref=f2e138] [cursor=pointer]
        - generic [ref=f2e143]: 50%
        - button "放大" [ref=f2e144] [cursor=pointer]
        - button "撤销" [disabled] [ref=f2e150]
        - button "重做" [disabled] [ref=f2e154]
        - button "刷新数据" [ref=f2e158] [cursor=pointer]
        - link "预览" [ref=f2e164] [cursor=pointer]:
          - /url: /studio/screens/097312f2-a80a-4ae5-bee9-df702a502876/preview
        - button "保存" [ref=f2e168]
        - button "发布" [ref=f2e173] [cursor=pointer]
      - generic [ref=f2e177]:
        - complementary "组件与图层" [ref=f2e178]:
          - region "组件库" [ref=f2e179]:
            - heading "组件" [level=2] [ref=f2e180]
            - generic [ref=f2e181]:
              - heading "基础与装饰" [level=3] [ref=f2e182]
              - generic [ref=f2e183]:
                - button "文本" [ref=f2e184] [cursor=pointer]
                - button "图片" [ref=f2e197] [cursor=pointer]
                - button "面板" [ref=f2e205] [cursor=pointer]
                - button "分割线" [ref=f2e212] [cursor=pointer]
                - button "数字翻牌 数据" [ref=f2e223] [cursor=pointer]:
                  - generic [ref=f2e231]: 数字翻牌
                  - generic [ref=f2e232]: 数据
                - button "数字人 数据" [ref=f2e233] [cursor=pointer]:
                  - generic [ref=f2e241]: 数字人
                  - generic [ref=f2e242]: 数据
            - generic [ref=f2e243]:
              - heading "指标与状态" [level=3] [ref=f2e244]
              - generic [ref=f2e245]:
                - button "指标 数据" [ref=f2e246] [cursor=pointer]:
                  - generic [ref=f2e251]: 指标
                  - generic [ref=f2e252]: 数据
                - button "进度 数据" [ref=f2e253] [cursor=pointer]:
                  - generic [ref=f2e265]: 进度
                  - generic [ref=f2e266]: 数据
                - button "仪表盘 数据" [ref=f2e267] [cursor=pointer]:
                  - generic [ref=f2e273]: 仪表盘
                  - generic [ref=f2e274]: 数据
                - button "状态矩阵 数据" [ref=f2e275] [cursor=pointer]:
                  - generic [ref=f2e282]: 状态矩阵
                  - generic [ref=f2e283]: 数据
            - generic [ref=f2e284]:
              - heading "列表与分析" [level=3] [ref=f2e285]
              - generic [ref=f2e286]:
                - button "表格 数据" [ref=f2e287] [cursor=pointer]:
                  - generic [ref=f2e292]: 表格
                  - generic [ref=f2e293]: 数据
                - button "排行榜 数据" [ref=f2e294] [cursor=pointer]:
                  - generic [ref=f2e308]: 排行榜
                  - generic [ref=f2e309]: 数据
                - button "告警列表 数据" [ref=f2e310] [cursor=pointer]:
                  - generic [ref=f2e318]: 告警列表
                  - generic [ref=f2e319]: 数据
                - button "时间线 数据" [ref=f2e320] [cursor=pointer]:
                  - generic [ref=f2e326]: 时间线
                  - generic [ref=f2e327]: 数据
            - generic [ref=f2e328]:
              - heading "图表" [level=3] [ref=f2e329]
              - generic [ref=f2e330]:
                - button "折线图 数据" [ref=f2e331] [cursor=pointer]:
                  - generic [ref=f2e342]: 折线图
                  - generic [ref=f2e343]: 数据
                - button "柱状图 数据" [ref=f2e344] [cursor=pointer]:
                  - generic [ref=f2e356]: 柱状图
                  - generic [ref=f2e357]: 数据
                - button "饼图 数据" [ref=f2e358] [cursor=pointer]:
                  - generic [ref=f2e364]: 饼图
                  - generic [ref=f2e365]: 数据
                - button "雷达图 数据" [ref=f2e366] [cursor=pointer]:
                  - generic [ref=f2e383]: 雷达图
                  - generic [ref=f2e384]: 数据
                - button "热力图 数据" [ref=f2e385] [cursor=pointer]:
                  - generic [ref=f2e397]: 热力图
                  - generic [ref=f2e398]: 数据
                - button "散点图 数据" [ref=f2e399] [cursor=pointer]:
                  - generic [ref=f2e410]: 散点图
                  - generic [ref=f2e411]: 数据
                - button "漏斗图 数据" [ref=f2e412] [cursor=pointer]:
                  - generic [ref=f2e422]: 漏斗图
                  - generic [ref=f2e423]: 数据
            - generic [ref=f2e424]:
              - heading "地图" [level=3] [ref=f2e425]
              - button "地图 数据" [ref=f2e427] [cursor=pointer]:
                - generic [ref=f2e434]: 地图
                - generic [ref=f2e435]: 数据
            - region "已安装插件" [ref=f2e436]:
              - heading "已安装插件" [level=3] [ref=f2e437]
              - generic [ref=f2e438]:
                - heading "示例指标插件 1.0.0" [level=4] [ref=f2e439]
                - button "示例指标" [ref=f2e440]
              - generic [ref=f2e441]:
                - heading "示例指标插件 2.0.0" [level=4] [ref=f2e442]
                - button "示例指标" [ref=f2e443]
          - region "图层" [ref=f2e444]:
            - heading "图层" [level=2] [ref=f2e445]
            - button "地图 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e446] [cursor=pointer]:
              - generic [ref=f2e447]: 地图
              - button "移到最底层" [ref=f2e448]: ↓
              - button "移到最顶层" [ref=f2e449]: ↑
              - button "隐藏图层" [ref=f2e450]
              - button "锁定图层" [ref=f2e454]
            - button "饼图 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e458] [cursor=pointer]:
              - generic [ref=f2e459]: 饼图
              - button "移到最底层" [ref=f2e460]: ↓
              - button "移到最顶层" [ref=f2e461]: ↑
              - button "隐藏图层" [ref=f2e462]
              - button "锁定图层" [ref=f2e466]
            - button "柱状图 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e470] [cursor=pointer]:
              - generic [ref=f2e471]: 柱状图
              - button "移到最底层" [ref=f2e472]: ↓
              - button "移到最顶层" [ref=f2e473]: ↑
              - button "隐藏图层" [ref=f2e474]
              - button "锁定图层" [ref=f2e478]
            - button "折线图 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e482] [cursor=pointer]:
              - generic [ref=f2e483]: 折线图
              - button "移到最底层" [ref=f2e484]: ↓
              - button "移到最顶层" [ref=f2e485]: ↑
              - button "隐藏图层" [ref=f2e486]
              - button "锁定图层" [ref=f2e490]
            - button "进度 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e494] [cursor=pointer]:
              - generic [ref=f2e495]: 进度
              - button "移到最底层" [ref=f2e496]: ↓
              - button "移到最顶层" [ref=f2e497]: ↑
              - button "隐藏图层" [ref=f2e498]
              - button "锁定图层" [ref=f2e502]
            - button "表格 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e506] [cursor=pointer]:
              - generic [ref=f2e507]: 表格
              - button "移到最底层" [ref=f2e508]: ↓
              - button "移到最顶层" [ref=f2e509]: ↑
              - button "隐藏图层" [ref=f2e510]
              - button "锁定图层" [ref=f2e514]
            - button "指标 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e518] [cursor=pointer]:
              - generic [ref=f2e519]: 指标
              - button "移到最底层" [ref=f2e520]: ↓
              - button "移到最顶层" [ref=f2e521]: ↑
              - button "隐藏图层" [ref=f2e522]
              - button "锁定图层" [ref=f2e526]
            - button "图片 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e530] [cursor=pointer]:
              - generic [ref=f2e531]: 图片
              - button "移到最底层" [ref=f2e532]: ↓
              - button "移到最顶层" [ref=f2e533]: ↑
              - button "隐藏图层" [ref=f2e534]
              - button "锁定图层" [ref=f2e538]
            - button "文本 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e542] [cursor=pointer]:
              - generic [ref=f2e543]: 文本
              - button "移到最底层" [ref=f2e544]: ↓
              - button "移到最顶层" [ref=f2e545]: ↑
              - button "隐藏图层" [ref=f2e546]
              - button "锁定图层" [ref=f2e550]
        - main "大屏画布" [ref=f2e554]:
          - generic [ref=f2e555]:
            - generic [ref=f2e557]:
              - button "DataPulse 运营态势总览" [ref=f2e558]
              - button [ref=f2e561]:
                - img "品牌图像" [ref=f2e564]
              - button [ref=f2e565]:
                - generic [ref=f2e567]:
                  - paragraph [ref=f2e568]: 销售总额
                  - strong [ref=f2e569]: "561"
              - button [ref=f2e570]:
                - table [ref=f2e574]:
                  - rowgroup [ref=f2e575]:
                    - row [ref=f2e576]:
                      - columnheader "month" [ref=f2e577]
                      - columnheader "region" [ref=f2e578]
                      - columnheader "amount" [ref=f2e579]
                  - rowgroup [ref=f2e580]:
                    - row [ref=f2e581]:
                      - cell "2026-01" [ref=f2e582]
                      - cell "华东" [ref=f2e583]
                      - cell "120.5" [ref=f2e584]
                    - row [ref=f2e585]:
                      - cell "2026-02" [ref=f2e586]
                      - cell "华南" [ref=f2e587]
                      - cell "80" [ref=f2e588]
                    - row [ref=f2e589]:
                      - cell "2026-03" [ref=f2e590]
                      - cell "华东" [ref=f2e591]
                      - cell "200" [ref=f2e592]
                    - row [ref=f2e593]:
                      - cell "2026-04" [ref=f2e594]
                      - cell "华北" [ref=f2e595]
                      - cell "160" [ref=f2e596]
              - button "目标值 100% 100" [ref=f2e597]:
                - generic [ref=f2e599]:
                  - generic [ref=f2e600]:
                    - generic [ref=f2e601]: 目标值
                    - strong [ref=f2e602]: 100%
                  - progressbar "目标值" [ref=f2e603]
              - button [ref=f2e605]
              - button [ref=f2e611]
              - button [ref=f2e617]
              - button [ref=f2e623]
            - generic:
              - generic: 1920 × 1080
              - generic: 50%
              - generic: 网格 10px
              - generic: 吸附开启
        - complementary "属性面板" [ref=f2e629]:
          - region "属性面板" [ref=f2e630]:
            - heading "属性" [level=2] [ref=f2e631]
            - paragraph [ref=f2e632]: 选择一个组件后编辑属性。
          - region "AI 使用说明" [ref=f2e633]:
            - heading "AI 分析" [level=2] [ref=f2e634]
            - paragraph [ref=f2e635]: 选中一个可绑定数据的组件后，就可以生成图表建议并直接应用。
```

# Test source

```ts
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
  128 |       draft_document: configured,
  129 |       expected_revision: current.draft_revision,
  130 |     },
  131 |   );
  132 |   await page.reload();
  133 |   await expect(page.getByText("DataPulse 运营态势总览")).toBeVisible();
  134 |   await expect(page.getByText("正在加载…")).toHaveCount(0, {
  135 |     timeout: 12_000,
  136 |   });
  137 |   for (const panel of [
  138 |     page.locator("aside.editor-panel--left"),
  139 |     page.locator("aside.editor-panel--right"),
  140 |   ]) {
  141 |     await panel.evaluate((element) => {
  142 |       element.scrollTop = 0;
  143 |     });
  144 |     await expect.poll(() => panel.evaluate((element) => element.scrollTop)).toBe(0);
  145 |   }
  146 |   await page.locator(":focus").evaluateAll((elements) => {
  147 |     for (const element of elements) {
  148 |       if (element instanceof HTMLElement) {
  149 |         element.blur();
  150 |       }
  151 |     }
  152 |   });
  153 |   const editorSnapshot = testInfo.project.name === "chromium"
  154 |     ? "editor-shell.png"
  155 |     : `editor-shell-${testInfo.project.name}.png`;
> 156 |   await expect(page).toHaveScreenshot(editorSnapshot, {
      |                      ^ Error: expect(page).toHaveScreenshot(expected) failed
  157 |     animations: "disabled",
  158 |   });
  159 | 
  160 |   const previewPromise = page.waitForEvent("popup");
  161 |   await page.getByRole("link", { name: "预览" }).click();
  162 |   const preview = await previewPromise;
  163 |   await expect(preview.getByText("DataPulse 运营态势总览")).toBeVisible();
  164 |   await expect(preview.getByText("草稿预览")).toBeVisible();
  165 |   await preview.close();
  166 | 
  167 |   await page.getByRole("button", { name: "发布", exact: true }).click();
  168 |   await expect(
  169 |     page.getByRole("heading", { name: "确认发布大屏" }),
  170 |   ).toBeVisible();
  171 |   await page.getByRole("button", { name: "确认发布" }).click();
  172 |   await expect(page.getByText("发布成功")).toBeVisible();
  173 | 
  174 |   const displayKey = await generateDisplayKey(page, screenId!);
  175 |   let queryCount = 0;
  176 |   page.on("request", (request) => {
  177 |     if (
  178 |       request.method() === "POST" &&
  179 |       request.url().includes(`/api/player/screens/${screenId}/query`)
  180 |     ) {
  181 |       queryCount += 1;
  182 |     }
  183 |   });
  184 |   await page.goto(`/play/${screenId}?key=[REDACTED]`);
  185 |   await expect(page).toHaveURL(new RegExp(`/play/${screenId}$`));
  186 |   await expect(page.getByText("DataPulse 运营态势总览")).toBeVisible();
  187 |   await expect.poll(() => queryCount).toBeGreaterThanOrEqual(7);
  188 | 
  189 |   const beforeInteraction = queryCount;
  190 |   const chart = page.locator(".screen-chart canvas").first();
  191 |   await expect(chart).toBeVisible();
  192 |   for (const position of [
  193 |     { x: 156, y: 82 },
  194 |     { x: 290, y: 176 },
  195 |     { x: 460, y: 238 },
  196 |   ]) {
  197 |     await chart.click({ position });
  198 |     await page.waitForTimeout(250);
  199 |     if (queryCount > beforeInteraction) {
  200 |       break;
  201 |     }
  202 |   }
  203 |   expect(queryCount).toBeGreaterThan(beforeInteraction);
  204 | 
  205 |   const beforeTimer = queryCount;
  206 |   await expect
  207 |     .poll(() => queryCount, { timeout: 12_000 })
  208 |     .toBeGreaterThan(beforeTimer);
  209 | });
  210 | 
  211 | test("multi-selection drags as one group and persists the same canvas delta", async ({
  212 |   page,
  213 | }) => {
  214 |   test.setTimeout(45_000);
  215 |   await page.setViewportSize({ width: 1600, height: 1000 });
  216 |   await authenticate(page);
  217 |   await page.goto("/studio/screens");
  218 |   await page.getByRole("button", { name: /新建大屏/ }).first().click();
  219 |   await page.getByLabel("大屏名称").fill("E2E 多选拖拽");
  220 |   await page.getByRole("button", { name: "创建并编辑" }).click();
  221 | 
  222 |   const library = page.getByLabel("组件库");
  223 |   await library.getByRole("button", { name: "文本", exact: true }).click();
  224 |   await library.getByRole("button", { name: /^指标\s+数据$/ }).click();
  225 |   const components = page.locator("[data-canvas-component]");
  226 |   await expect(components).toHaveCount(2);
  227 |   await components.nth(0).click();
  228 |   await components.nth(1).click({ modifiers: ["Meta"] });
  229 |   await expect(page.locator(".editor-canvas-component.is-selected")).toHaveCount(2);
  230 | 
  231 |   const before = await components.evaluateAll((items) =>
  232 |     items.map((item) => ({
  233 |       x: Number.parseFloat((item as HTMLElement).style.left),
  234 |       y: Number.parseFloat((item as HTMLElement).style.top),
  235 |     })),
  236 |   );
  237 |   const firstBox = await components.nth(0).boundingBox();
  238 |   expect(firstBox).not.toBeNull();
  239 |   await page.mouse.move(
  240 |     firstBox!.x + firstBox!.width / 2,
  241 |     firstBox!.y + firstBox!.height / 2,
  242 |   );
  243 |   await page.mouse.down();
  244 |   await page.mouse.move(
  245 |     firstBox!.x + firstBox!.width / 2 + 50,
  246 |     firstBox!.y + firstBox!.height / 2 + 30,
  247 |     { steps: 6 },
  248 |   );
  249 |   await page.mouse.up();
  250 | 
  251 |   const after = await components.evaluateAll((items) =>
  252 |     items.map((item) => ({
  253 |       x: Number.parseFloat((item as HTMLElement).style.left),
  254 |       y: Number.parseFloat((item as HTMLElement).style.top),
  255 |     })),
  256 |   );
```