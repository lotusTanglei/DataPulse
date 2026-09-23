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

  1874 pixels (ratio 0.01 of all image pixels) are different.

  Snapshot: editor-shell-webkit.png

Call log:
  - Expect "toHaveScreenshot(editor-shell-webkit.png)" with timeout 8000ms
    - verifying given screenshot expectation
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - 15130 pixels (ratio 0.01 of all image pixels) are different.
  - waiting 100ms before taking screenshot
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - 11571 pixels (ratio 0.01 of all image pixels) are different.
  - waiting 250ms before taking screenshot
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - 3053 pixels (ratio 0.01 of all image pixels) are different.
  - waiting 500ms before taking screenshot
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - captured a stable screenshot
  - 1874 pixels (ratio 0.01 of all image pixels) are different.

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
      - link "概览" [ref=f2e10]:
        - /url: /studio/overview
      - link "数据源" [ref=f2e17]:
        - /url: /studio/datasources
      - link "数据集" [ref=f2e23]:
        - /url: /studio/datasets
      - link "大屏" [ref=f2e28]:
        - /url: /studio/screens
    - link "资源共享" [ref=f2e33]:
      - /url: /studio/sharing
    - link "模板与插件" [ref=f2e38]:
      - /url: /studio/ecosystem
    - link "用户管理" [ref=f2e43]:
      - /url: /studio/users
    - region "最近访问" [ref=f2e48]:
      - paragraph [ref=f2e49]: 最近访问
      - paragraph [ref=f2e50]: 暂无最近项目
    - link "系统设置" [ref=f2e52]:
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
        - strong [ref=f2e69]: 大屏编辑器
      - generic [ref=f2e70]: 本地工作区
    - region "大屏编辑器" [ref=f2e72]:
      - generic "编辑器工具栏" [ref=f2e73]:
        - link "返回大屏列表" [ref=f2e74] [cursor=pointer]:
          - /url: /studio/screens
        - generic [ref=f2e77]:
          - strong [ref=f2e78]: E2E 运营大屏
          - generic [ref=f2e79]: 已保存
        - button "左对齐" [disabled] [ref=f2e80]
        - button "水平居中" [disabled] [ref=f2e82]
        - button "右对齐" [disabled] [ref=f2e84]
        - button "组合" [disabled] [ref=f2e86]
        - button "取消组合" [disabled] [ref=f2e87]
        - button "顶部对齐" [disabled] [ref=f2e88]
        - button "垂直居中" [disabled] [ref=f2e94]
        - button "底部对齐" [disabled] [ref=f2e100]
        - button "水平等间距" [disabled] [ref=f2e106]
        - button "垂直等间距" [disabled] [ref=f2e109]
        - button "网格" [ref=f2e112] [cursor=pointer]
        - button "吸附" [ref=f2e115] [cursor=pointer]
        - button "缩小" [ref=f2e120] [cursor=pointer]
        - generic [ref=f2e124]: 50%
        - button "放大" [ref=f2e125] [cursor=pointer]
        - button "撤销" [disabled] [ref=f2e129]
        - button "重做" [disabled] [ref=f2e133]
        - button "刷新数据" [ref=f2e137] [cursor=pointer]
        - link "预览" [ref=f2e143]:
          - /url: /studio/screens/7a2a4cdf-ae2b-472e-b370-bbc4ee9282e6/preview
        - button "保存" [ref=f2e147]
        - button "发布" [ref=f2e152] [cursor=pointer]
      - generic [ref=f2e156]:
        - complementary "组件与图层" [ref=f2e157]:
          - region "组件库" [ref=f2e158]:
            - heading "组件" [level=2] [ref=f2e159]
            - generic [ref=f2e160]:
              - heading "基础与装饰" [level=3] [ref=f2e161]
              - generic [ref=f2e162]:
                - button "文本" [ref=f2e163] [cursor=pointer]
                - button "图片" [ref=f2e174] [cursor=pointer]
                - button "面板" [ref=f2e182] [cursor=pointer]
                - button "分割线" [ref=f2e188] [cursor=pointer]
                - button "数字翻牌 数据" [ref=f2e198] [cursor=pointer]:
                  - generic [ref=f2e204]: 数字翻牌
                  - generic [ref=f2e205]: 数据
                - button "数字人 数据" [ref=f2e206] [cursor=pointer]:
                  - generic [ref=f2e213]: 数字人
                  - generic [ref=f2e214]: 数据
            - generic [ref=f2e215]:
              - heading "指标与状态" [level=3] [ref=f2e216]
              - generic [ref=f2e217]:
                - button "指标 数据" [ref=f2e218] [cursor=pointer]:
                  - generic [ref=f2e223]: 指标
                  - generic [ref=f2e224]: 数据
                - button "进度 数据" [ref=f2e225] [cursor=pointer]:
                  - generic [ref=f2e235]: 进度
                  - generic [ref=f2e236]: 数据
                - button "仪表盘 数据" [ref=f2e237] [cursor=pointer]:
                  - generic [ref=f2e243]: 仪表盘
                  - generic [ref=f2e244]: 数据
                - button "状态矩阵 数据" [ref=f2e245] [cursor=pointer]:
                  - generic [ref=f2e250]: 状态矩阵
                  - generic [ref=f2e251]: 数据
            - generic [ref=f2e252]:
              - heading "列表与分析" [level=3] [ref=f2e253]
              - generic [ref=f2e254]:
                - button "表格 数据" [ref=f2e255] [cursor=pointer]:
                  - generic [ref=f2e260]: 表格
                  - generic [ref=f2e261]: 数据
                - button "排行榜 数据" [ref=f2e262] [cursor=pointer]:
                  - generic [ref=f2e275]: 排行榜
                  - generic [ref=f2e276]: 数据
                - button "告警列表 数据" [ref=f2e277] [cursor=pointer]:
                  - generic [ref=f2e285]: 告警列表
                  - generic [ref=f2e286]: 数据
                - button "时间线 数据" [ref=f2e287] [cursor=pointer]:
                  - generic [ref=f2e293]: 时间线
                  - generic [ref=f2e294]: 数据
            - generic [ref=f2e295]:
              - heading "图表" [level=3] [ref=f2e296]
              - generic [ref=f2e297]:
                - button "折线图 数据" [ref=f2e298] [cursor=pointer]:
                  - generic [ref=f2e309]: 折线图
                  - generic [ref=f2e310]: 数据
                - button "柱状图 数据" [ref=f2e311] [cursor=pointer]:
                  - generic [ref=f2e320]: 柱状图
                  - generic [ref=f2e321]: 数据
                - button "饼图 数据" [ref=f2e322] [cursor=pointer]:
                  - generic [ref=f2e328]: 饼图
                  - generic [ref=f2e329]: 数据
                - button "雷达图 数据" [ref=f2e330] [cursor=pointer]:
                  - generic [ref=f2e345]: 雷达图
                  - generic [ref=f2e346]: 数据
                - button "热力图 数据" [ref=f2e347] [cursor=pointer]:
                  - generic [ref=f2e357]: 热力图
                  - generic [ref=f2e358]: 数据
                - button "散点图 数据" [ref=f2e359] [cursor=pointer]:
                  - generic [ref=f2e370]: 散点图
                  - generic [ref=f2e371]: 数据
                - button "漏斗图 数据" [ref=f2e372] [cursor=pointer]:
                  - generic [ref=f2e382]: 漏斗图
                  - generic [ref=f2e383]: 数据
            - generic [ref=f2e384]:
              - heading "地图" [level=3] [ref=f2e385]
              - button "地图 数据" [ref=f2e387] [cursor=pointer]:
                - generic [ref=f2e392]: 地图
                - generic [ref=f2e393]: 数据
            - region "已安装插件" [ref=f2e394]:
              - heading "已安装插件" [level=3] [ref=f2e395]
              - paragraph [ref=f2e396]: 在模板与插件目录导入组件包。
          - region "图层" [ref=f2e397]:
            - heading "图层" [level=2] [ref=f2e398]
            - button "地图 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e399] [cursor=pointer]:
              - generic [ref=f2e400]: 地图
              - button "移到最底层" [ref=f2e401]: ↓
              - button "移到最顶层" [ref=f2e402]: ↑
              - button "隐藏图层" [ref=f2e403]
              - button "锁定图层" [ref=f2e407]
            - button "饼图 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e411] [cursor=pointer]:
              - generic [ref=f2e412]: 饼图
              - button "移到最底层" [ref=f2e413]: ↓
              - button "移到最顶层" [ref=f2e414]: ↑
              - button "隐藏图层" [ref=f2e415]
              - button "锁定图层" [ref=f2e419]
            - button "柱状图 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e423] [cursor=pointer]:
              - generic [ref=f2e424]: 柱状图
              - button "移到最底层" [ref=f2e425]: ↓
              - button "移到最顶层" [ref=f2e426]: ↑
              - button "隐藏图层" [ref=f2e427]
              - button "锁定图层" [ref=f2e431]
            - button "折线图 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e435] [cursor=pointer]:
              - generic [ref=f2e436]: 折线图
              - button "移到最底层" [ref=f2e437]: ↓
              - button "移到最顶层" [ref=f2e438]: ↑
              - button "隐藏图层" [ref=f2e439]
              - button "锁定图层" [ref=f2e443]
            - button "进度 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e447] [cursor=pointer]:
              - generic [ref=f2e448]: 进度
              - button "移到最底层" [ref=f2e449]: ↓
              - button "移到最顶层" [ref=f2e450]: ↑
              - button "隐藏图层" [ref=f2e451]
              - button "锁定图层" [ref=f2e455]
            - button "表格 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e459] [cursor=pointer]:
              - generic [ref=f2e460]: 表格
              - button "移到最底层" [ref=f2e461]: ↓
              - button "移到最顶层" [ref=f2e462]: ↑
              - button "隐藏图层" [ref=f2e463]
              - button "锁定图层" [ref=f2e467]
            - button "指标 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e471] [cursor=pointer]:
              - generic [ref=f2e472]: 指标
              - button "移到最底层" [ref=f2e473]: ↓
              - button "移到最顶层" [ref=f2e474]: ↑
              - button "隐藏图层" [ref=f2e475]
              - button "锁定图层" [ref=f2e479]
            - button "图片 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e483] [cursor=pointer]:
              - generic [ref=f2e484]: 图片
              - button "移到最底层" [ref=f2e485]: ↓
              - button "移到最顶层" [ref=f2e486]: ↑
              - button "隐藏图层" [ref=f2e487]
              - button "锁定图层" [ref=f2e491]
            - button "文本 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e495] [cursor=pointer]:
              - generic [ref=f2e496]: 文本
              - button "移到最底层" [ref=f2e497]: ↓
              - button "移到最顶层" [ref=f2e498]: ↑
              - button "隐藏图层" [ref=f2e499]
              - button "锁定图层" [ref=f2e503]
        - main "大屏画布" [ref=f2e507]:
          - generic [ref=f2e508]:
            - generic [ref=f2e510]:
              - button "DataPulse 运营态势总览" [ref=f2e511]
              - button [ref=f2e514]:
                - img "品牌图像" [ref=f2e517]
              - button [ref=f2e518]:
                - generic [ref=f2e520]:
                  - paragraph [ref=f2e521]: 销售总额
                  - strong [ref=f2e522]: "561"
              - button [ref=f2e523]:
                - table [ref=f2e527]:
                  - rowgroup [ref=f2e528]:
                    - row [ref=f2e529]:
                      - columnheader "month" [ref=f2e530]
                      - columnheader "region" [ref=f2e531]
                      - columnheader "amount" [ref=f2e532]
                  - rowgroup [ref=f2e533]:
                    - row [ref=f2e534]:
                      - cell "2026-01" [ref=f2e535]
                      - cell "华东" [ref=f2e536]
                      - cell "120.5" [ref=f2e537]
                    - row [ref=f2e538]:
                      - cell "2026-02" [ref=f2e539]
                      - cell "华南" [ref=f2e540]
                      - cell "80" [ref=f2e541]
                    - row [ref=f2e542]:
                      - cell "2026-03" [ref=f2e543]
                      - cell "华东" [ref=f2e544]
                      - cell "200" [ref=f2e545]
                    - row [ref=f2e546]:
                      - cell "2026-04" [ref=f2e547]
                      - cell "华北" [ref=f2e548]
                      - cell "160" [ref=f2e549]
              - button "目标值 100% 100" [ref=f2e550]:
                - generic [ref=f2e552]:
                  - generic [ref=f2e553]:
                    - generic [ref=f2e554]: 目标值
                    - strong [ref=f2e555]: 100%
                  - progressbar "目标值" [ref=f2e556]
              - button [ref=f2e558]
              - button [ref=f2e564]
              - button [ref=f2e570]
              - button [ref=f2e576]
            - generic:
              - generic: 1920 × 1080
              - generic: 50%
              - generic: 网格 10px
              - generic: 吸附开启
        - complementary "属性面板" [ref=f2e582]:
          - region "属性面板" [ref=f2e583]:
            - heading "属性" [level=2] [ref=f2e584]
            - paragraph [ref=f2e585]: 选择一个组件后编辑属性。
          - region "AI 使用说明" [ref=f2e586]:
            - heading "AI 分析" [level=2] [ref=f2e587]
            - paragraph [ref=f2e588]: 选中一个可绑定数据的组件后，就可以生成图表建议并直接应用。
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