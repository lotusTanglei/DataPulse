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

  16472 pixels (ratio 0.01 of all image pixels) are different.

  Snapshot: editor-shell.png

Call log:
  - Expect "toHaveScreenshot(editor-shell.png)" with timeout 8000ms
    - verifying given screenshot expectation
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - 47986 pixels (ratio 0.03 of all image pixels) are different.
  - waiting 100ms before taking screenshot
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - 22003 pixels (ratio 0.02 of all image pixels) are different.
  - waiting 250ms before taking screenshot
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - 10101 pixels (ratio 0.01 of all image pixels) are different.
  - waiting 500ms before taking screenshot
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - 88 pixels (ratio 0.01 of all image pixels) are different.
  - waiting 1000ms before taking screenshot
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - captured a stable screenshot
  - 16472 pixels (ratio 0.01 of all image pixels) are different.

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
    - region "最近访问" [ref=f2e33]:
      - paragraph [ref=f2e34]: 最近访问
      - paragraph [ref=f2e35]: 暂无最近项目
    - link "系统设置" [ref=f2e37] [cursor=pointer]:
      - /url: /studio/settings
    - generic [ref=f2e42]:
      - generic [ref=f2e43]: A
      - generic [ref=f2e44]: admin
      - button "退出管理员账号" [ref=f2e45] [cursor=pointer]
  - main [ref=f2e50]:
    - generic [ref=f2e51]:
      - navigation "面包屑" [ref=f2e52]:
        - generic [ref=f2e53]: DataPulse
        - generic [ref=f2e54]: /
        - strong [ref=f2e55]: 大屏编辑器
      - generic [ref=f2e56]: 本地工作区
    - region "大屏编辑器" [ref=f2e58]:
      - generic "编辑器工具栏" [ref=f2e59]:
        - link "返回大屏列表" [ref=f2e60] [cursor=pointer]:
          - /url: /studio/screens
        - generic [ref=f2e64]:
          - strong [ref=f2e65]: E2E 运营大屏
          - generic [ref=f2e66]: 已保存
        - button "左对齐" [disabled] [ref=f2e67]
        - button "水平居中" [disabled] [ref=f2e72]
        - button "右对齐" [disabled] [ref=f2e77]
        - button "组合" [disabled] [ref=f2e82]
        - button "取消组合" [disabled] [ref=f2e83]
        - button "顶部对齐" [disabled] [ref=f2e84]
        - button "垂直居中" [disabled] [ref=f2e91]
        - button "底部对齐" [disabled] [ref=f2e98]
        - button "水平等间距" [disabled] [ref=f2e105]
        - button "垂直等间距" [disabled] [ref=f2e108]
        - button "网格" [ref=f2e111] [cursor=pointer]
        - button "吸附" [ref=f2e118] [cursor=pointer]
        - button "缩小" [ref=f2e123] [cursor=pointer]
        - generic [ref=f2e128]: 50%
        - button "放大" [ref=f2e129] [cursor=pointer]
        - button "撤销" [disabled] [ref=f2e135]
        - button "重做" [disabled] [ref=f2e139]
        - button "刷新数据" [ref=f2e143] [cursor=pointer]
        - link "预览" [ref=f2e149] [cursor=pointer]:
          - /url: /studio/screens/eb968609-5e2f-4908-95a3-fb68844dc981/preview
        - button "保存" [ref=f2e153]
        - button "发布" [ref=f2e158] [cursor=pointer]
      - generic [ref=f2e162]:
        - complementary "组件与图层" [ref=f2e163]:
          - region "组件库" [ref=f2e164]:
            - heading "组件" [level=2] [ref=f2e165]
            - generic [ref=f2e166]:
              - heading "基础与装饰" [level=3] [ref=f2e167]
              - generic [ref=f2e168]:
                - button "文本" [ref=f2e169] [cursor=pointer]
                - button "图片" [ref=f2e182] [cursor=pointer]
                - button "面板" [ref=f2e190] [cursor=pointer]
                - button "分割线" [ref=f2e197] [cursor=pointer]
                - button "数字翻牌 数据" [ref=f2e208] [cursor=pointer]:
                  - generic [ref=f2e216]: 数字翻牌
                  - generic [ref=f2e217]: 数据
            - generic [ref=f2e218]:
              - heading "指标与状态" [level=3] [ref=f2e219]
              - generic [ref=f2e220]:
                - button "指标 数据" [ref=f2e221] [cursor=pointer]:
                  - generic [ref=f2e226]: 指标
                  - generic [ref=f2e227]: 数据
                - button "进度 数据" [ref=f2e228] [cursor=pointer]:
                  - generic [ref=f2e240]: 进度
                  - generic [ref=f2e241]: 数据
                - button "仪表盘 数据" [ref=f2e242] [cursor=pointer]:
                  - generic [ref=f2e248]: 仪表盘
                  - generic [ref=f2e249]: 数据
                - button "状态矩阵 数据" [ref=f2e250] [cursor=pointer]:
                  - generic [ref=f2e257]: 状态矩阵
                  - generic [ref=f2e258]: 数据
            - generic [ref=f2e259]:
              - heading "列表与分析" [level=3] [ref=f2e260]
              - generic [ref=f2e261]:
                - button "表格 数据" [ref=f2e262] [cursor=pointer]:
                  - generic [ref=f2e267]: 表格
                  - generic [ref=f2e268]: 数据
                - button "排行榜 数据" [ref=f2e269] [cursor=pointer]:
                  - generic [ref=f2e283]: 排行榜
                  - generic [ref=f2e284]: 数据
                - button "告警列表 数据" [ref=f2e285] [cursor=pointer]:
                  - generic [ref=f2e293]: 告警列表
                  - generic [ref=f2e294]: 数据
                - button "时间线 数据" [ref=f2e295] [cursor=pointer]:
                  - generic [ref=f2e301]: 时间线
                  - generic [ref=f2e302]: 数据
            - generic [ref=f2e303]:
              - heading "图表" [level=3] [ref=f2e304]
              - generic [ref=f2e305]:
                - button "折线图 数据" [ref=f2e306] [cursor=pointer]:
                  - generic [ref=f2e317]: 折线图
                  - generic [ref=f2e318]: 数据
                - button "柱状图 数据" [ref=f2e319] [cursor=pointer]:
                  - generic [ref=f2e331]: 柱状图
                  - generic [ref=f2e332]: 数据
                - button "饼图 数据" [ref=f2e333] [cursor=pointer]:
                  - generic [ref=f2e339]: 饼图
                  - generic [ref=f2e340]: 数据
                - button "雷达图 数据" [ref=f2e341] [cursor=pointer]:
                  - generic [ref=f2e358]: 雷达图
                  - generic [ref=f2e359]: 数据
                - button "热力图 数据" [ref=f2e360] [cursor=pointer]:
                  - generic [ref=f2e372]: 热力图
                  - generic [ref=f2e373]: 数据
                - button "散点图 数据" [ref=f2e374] [cursor=pointer]:
                  - generic [ref=f2e385]: 散点图
                  - generic [ref=f2e386]: 数据
                - button "漏斗图 数据" [ref=f2e387] [cursor=pointer]:
                  - generic [ref=f2e397]: 漏斗图
                  - generic [ref=f2e398]: 数据
            - generic [ref=f2e399]:
              - heading "地图" [level=3] [ref=f2e400]
              - button "地图 数据" [ref=f2e402] [cursor=pointer]:
                - generic [ref=f2e409]: 地图
                - generic [ref=f2e410]: 数据
          - region "图层" [ref=f2e411]:
            - heading "图层" [level=2] [ref=f2e412]
            - button "地图 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e413] [cursor=pointer]:
              - generic [ref=f2e414]: 地图
              - button "移到最底层" [ref=f2e415]: ↓
              - button "移到最顶层" [ref=f2e416]: ↑
              - button "隐藏图层" [ref=f2e417]
              - button "锁定图层" [ref=f2e421]
            - button "饼图 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e425] [cursor=pointer]:
              - generic [ref=f2e426]: 饼图
              - button "移到最底层" [ref=f2e427]: ↓
              - button "移到最顶层" [ref=f2e428]: ↑
              - button "隐藏图层" [ref=f2e429]
              - button "锁定图层" [ref=f2e433]
            - button "柱状图 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e437] [cursor=pointer]:
              - generic [ref=f2e438]: 柱状图
              - button "移到最底层" [ref=f2e439]: ↓
              - button "移到最顶层" [ref=f2e440]: ↑
              - button "隐藏图层" [ref=f2e441]
              - button "锁定图层" [ref=f2e445]
            - button "折线图 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e449] [cursor=pointer]:
              - generic [ref=f2e450]: 折线图
              - button "移到最底层" [ref=f2e451]: ↓
              - button "移到最顶层" [ref=f2e452]: ↑
              - button "隐藏图层" [ref=f2e453]
              - button "锁定图层" [ref=f2e457]
            - button "进度 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e461] [cursor=pointer]:
              - generic [ref=f2e462]: 进度
              - button "移到最底层" [ref=f2e463]: ↓
              - button "移到最顶层" [ref=f2e464]: ↑
              - button "隐藏图层" [ref=f2e465]
              - button "锁定图层" [ref=f2e469]
            - button "表格 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e473] [cursor=pointer]:
              - generic [ref=f2e474]: 表格
              - button "移到最底层" [ref=f2e475]: ↓
              - button "移到最顶层" [ref=f2e476]: ↑
              - button "隐藏图层" [ref=f2e477]
              - button "锁定图层" [ref=f2e481]
            - button "指标 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e485] [cursor=pointer]:
              - generic [ref=f2e486]: 指标
              - button "移到最底层" [ref=f2e487]: ↓
              - button "移到最顶层" [ref=f2e488]: ↑
              - button "隐藏图层" [ref=f2e489]
              - button "锁定图层" [ref=f2e493]
            - button "图片 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e497] [cursor=pointer]:
              - generic [ref=f2e498]: 图片
              - button "移到最底层" [ref=f2e499]: ↓
              - button "移到最顶层" [ref=f2e500]: ↑
              - button "隐藏图层" [ref=f2e501]
              - button "锁定图层" [ref=f2e505]
            - button "文本 移到最底层 移到最顶层 隐藏图层 锁定图层" [ref=f2e509] [cursor=pointer]:
              - generic [ref=f2e510]: 文本
              - button "移到最底层" [ref=f2e511]: ↓
              - button "移到最顶层" [ref=f2e512]: ↑
              - button "隐藏图层" [ref=f2e513]
              - button "锁定图层" [ref=f2e517]
        - main "大屏画布" [ref=f2e521]:
          - generic [ref=f2e522]:
            - generic [ref=f2e524]:
              - button "DataPulse 运营态势总览" [ref=f2e525]
              - button [ref=f2e528]:
                - img "品牌图像" [ref=f2e531]
              - button [ref=f2e532]:
                - generic [ref=f2e534]:
                  - paragraph [ref=f2e535]: 销售总额
                  - strong [ref=f2e536]: "561"
              - button [ref=f2e537]:
                - table [ref=f2e541]:
                  - rowgroup [ref=f2e542]:
                    - row [ref=f2e543]:
                      - columnheader "month" [ref=f2e544]
                      - columnheader "region" [ref=f2e545]
                      - columnheader "amount" [ref=f2e546]
                  - rowgroup [ref=f2e547]:
                    - row [ref=f2e548]:
                      - cell "2026-01" [ref=f2e549]
                      - cell "华东" [ref=f2e550]
                      - cell "120.5" [ref=f2e551]
                    - row [ref=f2e552]:
                      - cell "2026-02" [ref=f2e553]
                      - cell "华南" [ref=f2e554]
                      - cell "80" [ref=f2e555]
                    - row [ref=f2e556]:
                      - cell "2026-03" [ref=f2e557]
                      - cell "华东" [ref=f2e558]
                      - cell "200" [ref=f2e559]
                    - row [ref=f2e560]:
                      - cell "2026-04" [ref=f2e561]
                      - cell "华北" [ref=f2e562]
                      - cell "160" [ref=f2e563]
              - button "目标值 100% 100" [ref=f2e564]:
                - generic [ref=f2e566]:
                  - generic [ref=f2e567]:
                    - generic [ref=f2e568]: 目标值
                    - strong [ref=f2e569]: 100%
                  - progressbar "目标值" [ref=f2e570]
              - button [ref=f2e572]
              - button [ref=f2e578]
              - button [ref=f2e584]
              - button [ref=f2e590]
            - generic:
              - generic: 1920 × 1080
              - generic: 50%
              - generic: 网格 10px
              - generic: 吸附开启
        - complementary "属性面板" [ref=f2e596]:
          - region "属性面板" [ref=f2e597]:
            - heading "属性" [level=2] [ref=f2e598]
            - paragraph [ref=f2e599]: 选择一个组件后编辑属性。
          - region "AI 使用说明" [ref=f2e600]:
            - heading "AI 分析" [level=2] [ref=f2e601]
            - paragraph [ref=f2e602]: 选中一个可绑定数据的组件后，就可以生成图表建议并直接应用。
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