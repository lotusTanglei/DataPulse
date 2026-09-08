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

  18400 pixels (ratio 0.01 of all image pixels) are different.

  Snapshot: editor-shell.png

Call log:
  - Expect "toHaveScreenshot(editor-shell.png)" with timeout 8000ms
    - verifying given screenshot expectation
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - 49040 pixels (ratio 0.03 of all image pixels) are different.
  - waiting 100ms before taking screenshot
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - 21675 pixels (ratio 0.02 of all image pixels) are different.
  - waiting 250ms before taking screenshot
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - 10742 pixels (ratio 0.01 of all image pixels) are different.
  - waiting 500ms before taking screenshot
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - 61 pixels (ratio 0.01 of all image pixels) are different.
  - waiting 1000ms before taking screenshot
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - captured a stable screenshot
  - 18400 pixels (ratio 0.01 of all image pixels) are different.

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
    - region "最近访问" [ref=f2e33]:
      - paragraph [ref=f2e34]: 最近访问
      - paragraph [ref=f2e35]: 暂无最近项目
    - link "系统设置" [ref=f2e37]:
      - /url: /studio/settings
    - generic [ref=f2e42]:
      - generic [ref=f2e43]: A
      - generic [ref=f2e44]: admin
      - button "退出管理员账号" [ref=f2e45] [cursor=pointer]
  - main [ref=f2e49]:
    - generic [ref=f2e50]:
      - navigation "面包屑" [ref=f2e51]:
        - generic [ref=f2e52]: DataPulse
        - generic [ref=f2e53]: /
        - strong [ref=f2e54]: 大屏编辑器
      - generic [ref=f2e55]: 本地工作区
    - region "大屏编辑器" [ref=f2e57]:
      - generic "编辑器工具栏" [ref=f2e58]:
        - link "返回大屏列表" [ref=f2e59] [cursor=pointer]:
          - /url: /studio/screens
        - generic [ref=f2e62]:
          - strong [ref=f2e63]: E2E 运营大屏
          - generic [ref=f2e64]: 已保存
        - button "左对齐" [disabled] [ref=f2e65]
        - button "水平居中" [disabled] [ref=f2e67]
        - button "右对齐" [disabled] [ref=f2e69]
        - button "组合" [disabled] [ref=f2e71]
        - button "取消组合" [disabled] [ref=f2e72]
        - button "顶部对齐" [disabled] [ref=f2e73]
        - button "垂直居中" [disabled] [ref=f2e79]
        - button "底部对齐" [disabled] [ref=f2e85]
        - button "水平等间距" [disabled] [ref=f2e91]
        - button "垂直等间距" [disabled] [ref=f2e94]
        - button "网格" [ref=f2e97] [cursor=pointer]
        - button "吸附" [ref=f2e100] [cursor=pointer]
        - button "缩小" [ref=f2e105] [cursor=pointer]
        - generic [ref=f2e109]: 50%
        - button "放大" [ref=f2e110] [cursor=pointer]
        - button "撤销" [disabled] [ref=f2e114]
        - button "重做" [disabled] [ref=f2e118]
        - button "刷新数据" [ref=f2e122] [cursor=pointer]
        - link "预览" [ref=f2e128]:
          - /url: /studio/screens/7f626ca7-6383-40a0-8902-64e41ef82045/preview
        - button "保存" [ref=f2e132]
        - button "发布" [ref=f2e137] [cursor=pointer]
      - generic [ref=f2e141]:
        - complementary "组件与图层" [ref=f2e142]:
          - region "组件库" [ref=f2e143]:
            - heading "组件" [level=2] [ref=f2e144]
            - generic [ref=f2e145]:
              - heading "基础与装饰" [level=3] [ref=f2e146]
              - generic [ref=f2e147]:
                - button "文本" [ref=f2e148] [cursor=pointer]
                - button "图片" [ref=f2e159] [cursor=pointer]
                - button "面板" [ref=f2e167] [cursor=pointer]
                - button "分割线" [ref=f2e173] [cursor=pointer]
                - button "数字翻牌 数据" [ref=f2e183] [cursor=pointer]:
                  - generic [ref=f2e189]: 数字翻牌
                  - generic [ref=f2e190]: 数据
            - generic [ref=f2e191]:
              - heading "指标与状态" [level=3] [ref=f2e192]
              - generic [ref=f2e193]:
                - button "指标 数据" [ref=f2e194] [cursor=pointer]:
                  - generic [ref=f2e199]: 指标
                  - generic [ref=f2e200]: 数据
                - button "进度 数据" [ref=f2e201] [cursor=pointer]:
                  - generic [ref=f2e211]: 进度
                  - generic [ref=f2e212]: 数据
                - button "仪表盘 数据" [ref=f2e213] [cursor=pointer]:
                  - generic [ref=f2e219]: 仪表盘
                  - generic [ref=f2e220]: 数据
                - button "状态矩阵 数据" [ref=f2e221] [cursor=pointer]:
                  - generic [ref=f2e226]: 状态矩阵
                  - generic [ref=f2e227]: 数据
            - generic [ref=f2e228]:
              - heading "列表与分析" [level=3] [ref=f2e229]
              - generic [ref=f2e230]:
                - button "表格 数据" [ref=f2e231] [cursor=pointer]:
                  - generic [ref=f2e236]: 表格
                  - generic [ref=f2e237]: 数据
                - button "排行榜 数据" [ref=f2e238] [cursor=pointer]:
                  - generic [ref=f2e251]: 排行榜
                  - generic [ref=f2e252]: 数据
                - button "告警列表 数据" [ref=f2e253] [cursor=pointer]:
                  - generic [ref=f2e261]: 告警列表
                  - generic [ref=f2e262]: 数据
                - button "时间线 数据" [ref=f2e263] [cursor=pointer]:
                  - generic [ref=f2e269]: 时间线
                  - generic [ref=f2e270]: 数据
            - generic [ref=f2e271]:
              - heading "图表" [level=3] [ref=f2e272]
              - generic [ref=f2e273]:
                - button "折线图 数据" [ref=f2e274] [cursor=pointer]:
                  - generic [ref=f2e285]: 折线图
                  - generic [ref=f2e286]: 数据
                - button "柱状图 数据" [ref=f2e287] [cursor=pointer]:
                  - generic [ref=f2e296]: 柱状图
                  - generic [ref=f2e297]: 数据
                - button "饼图 数据" [ref=f2e298] [cursor=pointer]:
                  - generic [ref=f2e304]: 饼图
                  - generic [ref=f2e305]: 数据
                - button "雷达图 数据" [ref=f2e306] [cursor=pointer]:
                  - generic [ref=f2e321]: 雷达图
                  - generic [ref=f2e322]: 数据
                - button "热力图 数据" [ref=f2e323] [cursor=pointer]:
                  - generic [ref=f2e333]: 热力图
                  - generic [ref=f2e334]: 数据
                - button "散点图 数据" [ref=f2e335] [cursor=pointer]:
                  - generic [ref=f2e346]: 散点图
                  - generic [ref=f2e347]: 数据
                - button "漏斗图 数据" [ref=f2e348] [cursor=pointer]:
                  - generic [ref=f2e358]: 漏斗图
                  - generic [ref=f2e359]: 数据
            - generic [ref=f2e360]:
              - heading "地图" [level=3] [ref=f2e361]
              - button "地图 数据" [ref=f2e363] [cursor=pointer]:
                - generic [ref=f2e368]: 地图
                - generic [ref=f2e369]: 数据
          - region "图层" [ref=f2e370]:
            - heading "图层" [level=2] [ref=f2e371]
            - button "地图 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e372] [cursor=pointer]:
              - generic [ref=f2e373]: 地图
              - button "移到最底层" [ref=f2e374]: ↓
              - button "移到最顶层" [ref=f2e375]: ↑
              - button "隐藏图层" [ref=f2e376]
              - button "锁定图层" [ref=f2e380]
            - button "饼图 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e384] [cursor=pointer]:
              - generic [ref=f2e385]: 饼图
              - button "移到最底层" [ref=f2e386]: ↓
              - button "移到最顶层" [ref=f2e387]: ↑
              - button "隐藏图层" [ref=f2e388]
              - button "锁定图层" [ref=f2e392]
            - button "柱状图 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e396] [cursor=pointer]:
              - generic [ref=f2e397]: 柱状图
              - button "移到最底层" [ref=f2e398]: ↓
              - button "移到最顶层" [ref=f2e399]: ↑
              - button "隐藏图层" [ref=f2e400]
              - button "锁定图层" [ref=f2e404]
            - button "折线图 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e408] [cursor=pointer]:
              - generic [ref=f2e409]: 折线图
              - button "移到最底层" [ref=f2e410]: ↓
              - button "移到最顶层" [ref=f2e411]: ↑
              - button "隐藏图层" [ref=f2e412]
              - button "锁定图层" [ref=f2e416]
            - button "进度 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e420] [cursor=pointer]:
              - generic [ref=f2e421]: 进度
              - button "移到最底层" [ref=f2e422]: ↓
              - button "移到最顶层" [ref=f2e423]: ↑
              - button "隐藏图层" [ref=f2e424]
              - button "锁定图层" [ref=f2e428]
            - button "表格 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e432] [cursor=pointer]:
              - generic [ref=f2e433]: 表格
              - button "移到最底层" [ref=f2e434]: ↓
              - button "移到最顶层" [ref=f2e435]: ↑
              - button "隐藏图层" [ref=f2e436]
              - button "锁定图层" [ref=f2e440]
            - button "指标 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e444] [cursor=pointer]:
              - generic [ref=f2e445]: 指标
              - button "移到最底层" [ref=f2e446]: ↓
              - button "移到最顶层" [ref=f2e447]: ↑
              - button "隐藏图层" [ref=f2e448]
              - button "锁定图层" [ref=f2e452]
            - button "图片 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e456] [cursor=pointer]:
              - generic [ref=f2e457]: 图片
              - button "移到最底层" [ref=f2e458]: ↓
              - button "移到最顶层" [ref=f2e459]: ↑
              - button "隐藏图层" [ref=f2e460]
              - button "锁定图层" [ref=f2e464]
            - button "文本 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e468] [cursor=pointer]:
              - generic [ref=f2e469]: 文本
              - button "移到最底层" [ref=f2e470]: ↓
              - button "移到最顶层" [ref=f2e471]: ↑
              - button "隐藏图层" [ref=f2e472]
              - button "锁定图层" [ref=f2e476]
        - main "大屏画布" [ref=f2e480]:
          - generic [ref=f2e481]:
            - generic [ref=f2e483]:
              - button "DataPulse 运营态势总览" [ref=f2e484]
              - button [ref=f2e487]:
                - img "品牌图像" [ref=f2e490]
              - button [ref=f2e491]:
                - generic [ref=f2e493]:
                  - paragraph [ref=f2e494]: 销售总额
                  - strong [ref=f2e495]: "561"
              - button [ref=f2e496]:
                - table [ref=f2e500]:
                  - rowgroup [ref=f2e501]:
                    - row [ref=f2e502]:
                      - columnheader "month" [ref=f2e503]
                      - columnheader "region" [ref=f2e504]
                      - columnheader "amount" [ref=f2e505]
                  - rowgroup [ref=f2e506]:
                    - row [ref=f2e507]:
                      - cell "2026-01" [ref=f2e508]
                      - cell "华东" [ref=f2e509]
                      - cell "120.5" [ref=f2e510]
                    - row [ref=f2e511]:
                      - cell "2026-02" [ref=f2e512]
                      - cell "华南" [ref=f2e513]
                      - cell "80" [ref=f2e514]
                    - row [ref=f2e515]:
                      - cell "2026-03" [ref=f2e516]
                      - cell "华东" [ref=f2e517]
                      - cell "200" [ref=f2e518]
                    - row [ref=f2e519]:
                      - cell "2026-04" [ref=f2e520]
                      - cell "华北" [ref=f2e521]
                      - cell "160" [ref=f2e522]
              - button "目标值 100% 100" [ref=f2e523]:
                - generic [ref=f2e525]:
                  - generic [ref=f2e526]:
                    - generic [ref=f2e527]: 目标值
                    - strong [ref=f2e528]: 100%
                  - progressbar "目标值" [ref=f2e529]
              - button [ref=f2e531]
              - button [ref=f2e537]
              - button [ref=f2e543]
              - button [ref=f2e549]
            - generic:
              - generic: 1920 × 1080
              - generic: 50%
              - generic: 网格 10px
              - generic: 吸附开启
        - complementary "属性面板" [ref=f2e555]:
          - region "属性面板" [ref=f2e556]:
            - heading "属性" [level=2] [ref=f2e557]
            - paragraph [ref=f2e558]: 选择一个组件后编辑属性。
          - region "AI 使用说明" [ref=f2e559]:
            - heading "AI 分析" [level=2] [ref=f2e560]
            - paragraph [ref=f2e561]: 选中一个可绑定数据的组件后，就可以生成图表建议并直接应用。
```

# Test source

```ts
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
  128 |       draft_document: configured,
  129 |       expected_revision: current.draft_revision,
  130 |     },
  131 |   );
  132 |   await page.reload();
  133 |   await expect(page.getByText("DataPulse 运营态势总览")).toBeVisible();
> 134 |   await expect(page).toHaveScreenshot("editor-shell.png", {
      |                      ^ Error: expect(page).toHaveScreenshot(expected) failed
  135 |     animations: "disabled",
  136 |   });
  137 |
  138 |   const previewPromise = page.waitForEvent("popup");
  139 |   await page.getByRole("link", { name: "预览" }).click();
  140 |   const preview = await previewPromise;
  141 |   await expect(preview.getByText("DataPulse 运营态势总览")).toBeVisible();
  142 |   await expect(preview.getByText("草稿预览")).toBeVisible();
  143 |   await preview.close();
  144 |
  145 |   await page.getByRole("button", { name: "发布", exact: true }).click();
  146 |   await expect(
  147 |     page.getByRole("heading", { name: "确认发布大屏" }),
  148 |   ).toBeVisible();
  149 |   await page.getByRole("button", { name: "确认发布" }).click();
  150 |   await expect(page.getByText("发布成功")).toBeVisible();
  151 |
  152 |   const displayKey = await generateDisplayKey(page, screenId!);
  153 |   let queryCount = 0;
  154 |   page.on("request", (request) => {
  155 |     if (
  156 |       request.method() === "POST" &&
  157 |       request.url().includes(`/api/player/screens/${screenId}/query`)
  158 |     ) {
  159 |       queryCount += 1;
  160 |     }
  161 |   });
  162 |   await page.goto(`/play/${screenId}?key=${encodeURIComponent(displayKey)}`);
  163 |   await expect(page).toHaveURL(new RegExp(`/play/${screenId}$`));
  164 |   await expect(page.getByText("DataPulse 运营态势总览")).toBeVisible();
  165 |   await expect.poll(() => queryCount).toBeGreaterThanOrEqual(7);
  166 |
  167 |   const beforeInteraction = queryCount;
  168 |   const chart = page.locator(".screen-chart canvas").first();
  169 |   await expect(chart).toBeVisible();
  170 |   for (const position of [
  171 |     { x: 156, y: 82 },
  172 |     { x: 290, y: 176 },
  173 |     { x: 460, y: 238 },
  174 |   ]) {
  175 |     await chart.click({ position });
  176 |     await page.waitForTimeout(250);
  177 |     if (queryCount > beforeInteraction) {
  178 |       break;
  179 |     }
  180 |   }
  181 |   expect(queryCount).toBeGreaterThan(beforeInteraction);
  182 |
  183 |   const beforeTimer = queryCount;
  184 |   await expect
  185 |     .poll(() => queryCount, { timeout: 12_000 })
  186 |     .toBeGreaterThan(beforeTimer);
  187 | });
  188 |
  189 | test("multi-selection drags as one group and persists the same canvas delta", async ({
  190 |   page,
  191 | }) => {
  192 |   test.setTimeout(45_000);
  193 |   await page.setViewportSize({ width: 1600, height: 1000 });
  194 |   await authenticate(page);
  195 |   await page.goto("/studio/screens");
  196 |   await page.getByRole("button", { name: /新建大屏/ }).first().click();
  197 |   await page.getByLabel("大屏名称").fill("E2E 多选拖拽");
  198 |   await page.getByRole("button", { name: "创建并编辑" }).click();
  199 |
  200 |   const library = page.getByLabel("组件库");
  201 |   await library.getByRole("button", { name: "文本", exact: true }).click();
  202 |   await library.getByRole("button", { name: /^指标\s+数据$/ }).click();
  203 |   const components = page.locator("[data-canvas-component]");
  204 |   await expect(components).toHaveCount(2);
  205 |   await components.nth(0).click();
  206 |   await components.nth(1).click({ modifiers: ["Meta"] });
  207 |   await expect(page.locator(".editor-canvas-component.is-selected")).toHaveCount(2);
  208 |
  209 |   const before = await components.evaluateAll((items) =>
  210 |     items.map((item) => ({
  211 |       x: Number.parseFloat((item as HTMLElement).style.left),
  212 |       y: Number.parseFloat((item as HTMLElement).style.top),
  213 |     })),
  214 |   );
  215 |   const firstBox = await components.nth(0).boundingBox();
  216 |   expect(firstBox).not.toBeNull();
  217 |   await page.mouse.move(
  218 |     firstBox!.x + firstBox!.width / 2,
  219 |     firstBox!.y + firstBox!.height / 2,
  220 |   );
  221 |   await page.mouse.down();
  222 |   await page.mouse.move(
  223 |     firstBox!.x + firstBox!.width / 2 + 50,
  224 |     firstBox!.y + firstBox!.height / 2 + 30,
  225 |     { steps: 6 },
  226 |   );
  227 |   await page.mouse.up();
  228 |
  229 |   const after = await components.evaluateAll((items) =>
  230 |     items.map((item) => ({
  231 |       x: Number.parseFloat((item as HTMLElement).style.left),
  232 |       y: Number.parseFloat((item as HTMLElement).style.top),
  233 |     })),
  234 |   );
```