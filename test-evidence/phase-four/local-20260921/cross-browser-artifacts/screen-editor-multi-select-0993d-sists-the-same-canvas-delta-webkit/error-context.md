# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: screen-editor.spec.ts >> multi-selection drags as one group and persists the same canvas delta
- Location: e2e/screen-editor.spec.ts:211:1

# Error details

```
Test timeout of 45000ms exceeded.
```

```
Error: locator.click: Test timeout of 45000ms exceeded.
Call log:
  - waiting for getByLabel('组件库').getByRole('button', { name: '文本', exact: true })

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - complementary [ref=e4]:
    - generic "工作区导航" [ref=e5]:
      - generic [ref=e6]: D
      - generic [ref=e7]: DataPulse
      - generic [ref=e8]: ⌄
    - navigation "主导航" [ref=e9]:
      - link "概览" [ref=e10]:
        - /url: /studio/overview
      - link "数据源" [ref=e17]:
        - /url: /studio/datasources
      - link "数据集" [ref=e23]:
        - /url: /studio/datasets
      - link "大屏" [ref=e28]:
        - /url: /studio/screens
    - link "资源共享" [ref=e33]:
      - /url: /studio/sharing
    - link "模板与插件" [ref=e38]:
      - /url: /studio/ecosystem
    - link "用户管理" [ref=e43]:
      - /url: /studio/users
    - region "最近访问" [ref=e48]:
      - paragraph [ref=e49]: 最近访问
      - paragraph [ref=e50]: 暂无最近项目
    - link "系统设置" [ref=e52]:
      - /url: /studio/settings
    - generic [ref=e57]:
      - generic [ref=e58]: A
      - generic [ref=e59]: admin
      - button "退出管理员账号" [ref=e60] [cursor=pointer]
  - main [ref=e64]:
    - generic [ref=e65]:
      - navigation "面包屑" [ref=e66]:
        - generic [ref=e67]: DataPulse
        - generic [ref=e68]: /
        - strong [ref=e69]: 大屏
      - generic [ref=e70]: 本地工作区
    - region [ref=e72]:
      - generic [ref=e73]:
        - generic [ref=e74]:
          - paragraph [ref=e75]: 可视化工作区
          - heading "大屏" [level=1] [ref=e76]
          - paragraph [ref=e77]: 创建、调试并发布可独立播放或安全嵌入业务系统的数据大屏。
        - generic [ref=e78]:
          - button "从模板创建" [ref=e79]
          - button "AI 生成大屏" [ref=e84]
          - button "新建大屏" [ref=e85] [cursor=pointer]
      - generic "大屏列表" [ref=e87]:
        - article [ref=e88]:
          - link "E2E AI 图表应用 草稿 暂无描述 最后更新 2026/09/21 11:36" [ref=e89]:
            - /url: /studio/screens/71e8a6e6-e035-4541-bd49-919a2069bc07/edit
            - generic [ref=e96]:
              - generic [ref=e97]:
                - strong [ref=e98]: E2E AI 图表应用
                - generic [ref=e99]: 草稿
              - generic [ref=e100]: 暂无描述
            - generic [ref=e101]: 最后更新 2026/09/21 11:36
          - generic [ref=e102]:
            - button "复制大屏 E2E AI 图表应用" [ref=e103] [cursor=pointer]: 复制
            - button "删除大屏 E2E AI 图表应用" [ref=e107] [cursor=pointer]: 删除
        - article [ref=e111]:
          - link "E2E AI 原子草稿 草稿 暂无描述 最后更新 2026/09/21 11:37" [ref=e112]:
            - /url: /studio/screens/dbaf7fd0-51a5-47d0-a90e-4c2985c67980/edit
            - generic [ref=e119]:
              - generic [ref=e120]:
                - strong [ref=e121]: E2E AI 原子草稿
                - generic [ref=e122]: 草稿
              - generic [ref=e123]: 暂无描述
            - generic [ref=e124]: 最后更新 2026/09/21 11:37
          - generic [ref=e125]:
            - button "复制大屏 E2E AI 原子草稿" [ref=e126] [cursor=pointer]: 复制
            - button "删除大屏 E2E AI 原子草稿" [ref=e130] [cursor=pointer]: 删除
        - article [ref=e134]:
          - link "数字人发布 1789961873359 已发布 暂无描述 最后更新 2026/09/21 11:37" [ref=e135]:
            - /url: /studio/screens/c51e911b-f676-423e-99d2-277599133db8/edit
            - generic [ref=e142]:
              - generic [ref=e143]:
                - strong [ref=e144]: 数字人发布 1789961873359
                - generic [ref=e145]: 已发布
              - generic [ref=e146]: 暂无描述
            - generic [ref=e147]: 最后更新 2026/09/21 11:37
          - generic [ref=e148]:
            - button "复制大屏 数字人发布 1789961873359" [ref=e149] [cursor=pointer]: 复制
            - button "删除大屏 数字人发布 1789961873359" [ref=e153] [cursor=pointer]: 删除
        - article [ref=e157]:
          - link "结构化话术持久化 1789961877288 已发布 暂无描述 最后更新 2026/09/21 11:37" [ref=e158]:
            - /url: /studio/screens/ea13b953-91d0-4bce-ae15-1b80b29a5172/edit
            - generic [ref=e165]:
              - generic [ref=e166]:
                - strong [ref=e167]: 结构化话术持久化 1789961877288
                - generic [ref=e168]: 已发布
              - generic [ref=e169]: 暂无描述
            - generic [ref=e170]: 最后更新 2026/09/21 11:37
          - generic [ref=e171]:
            - button "复制大屏 结构化话术持久化 1789961877288" [ref=e172] [cursor=pointer]: 复制
            - button "删除大屏 结构化话术持久化 1789961877288" [ref=e176] [cursor=pointer]: 删除
        - article [ref=e180]:
          - link "数字人 TTS 闭环 1789961879427 已发布 暂无描述 最后更新 2026/09/21 11:38" [ref=e181]:
            - /url: /studio/screens/bbda80ba-093b-4d34-ad19-f2f9d63a9292/edit
            - generic [ref=e188]:
              - generic [ref=e189]:
                - strong [ref=e190]: 数字人 TTS 闭环 1789961879427
                - generic [ref=e191]: 已发布
              - generic [ref=e192]: 暂无描述
            - generic [ref=e193]: 最后更新 2026/09/21 11:38
          - generic [ref=e194]:
            - button "复制大屏 数字人 TTS 闭环 1789961879427" [ref=e195] [cursor=pointer]: 复制
            - button "删除大屏 数字人 TTS 闭环 1789961879427" [ref=e199] [cursor=pointer]: 删除
        - article [ref=e203]:
          - link "数字人嵌入 1789961890481 已发布 暂无描述 最后更新 2026/09/21 11:38" [ref=e204]:
            - /url: /studio/screens/603050a7-ba0c-4d78-89c2-c9eaddc41fa6/edit
            - generic [ref=e211]:
              - generic [ref=e212]:
                - strong [ref=e213]: 数字人嵌入 1789961890481
                - generic [ref=e214]: 已发布
              - generic [ref=e215]: 暂无描述
            - generic [ref=e216]: 最后更新 2026/09/21 11:38
          - generic [ref=e217]:
            - button "复制大屏 数字人嵌入 1789961890481" [ref=e218] [cursor=pointer]: 复制
            - button "删除大屏 数字人嵌入 1789961890481" [ref=e222] [cursor=pointer]: 删除
        - article [ref=e226]:
          - link "数字人跨源嵌入 1789961891849 已发布 暂无描述 最后更新 2026/09/21 11:38" [ref=e227]:
            - /url: /studio/screens/3c1c255c-974d-4488-b1c2-619847b5170f/edit
            - generic [ref=e234]:
              - generic [ref=e235]:
                - strong [ref=e236]: 数字人跨源嵌入 1789961891849
                - generic [ref=e237]: 已发布
              - generic [ref=e238]: 暂无描述
            - generic [ref=e239]: 最后更新 2026/09/21 11:38
          - generic [ref=e240]:
            - button "复制大屏 数字人跨源嵌入 1789961891849" [ref=e241] [cursor=pointer]: 复制
            - button "删除大屏 数字人跨源嵌入 1789961891849" [ref=e245] [cursor=pointer]: 删除
        - article [ref=e249]:
          - link "数字人访问撤销 1789961893417 已发布 暂无描述 最后更新 2026/09/21 11:38" [ref=e250]:
            - /url: /studio/screens/040fa544-65b3-4698-b704-475164038553/edit
            - generic [ref=e257]:
              - generic [ref=e258]:
                - strong [ref=e259]: 数字人访问撤销 1789961893417
                - generic [ref=e260]: 已发布
              - generic [ref=e261]: 暂无描述
            - generic [ref=e262]: 最后更新 2026/09/21 11:38
          - generic [ref=e263]:
            - button "复制大屏 数字人访问撤销 1789961893417" [ref=e264] [cursor=pointer]: 复制
            - button "删除大屏 数字人访问撤销 1789961893417" [ref=e268] [cursor=pointer]: 删除
        - article [ref=e272]:
          - link "真实视频播报 1789961897121 已发布 暂无描述 最后更新 2026/09/21 11:38" [ref=e273]:
            - /url: /studio/screens/d321370a-2462-4a14-990a-ea9e1724de55/edit
            - generic [ref=e280]:
              - generic [ref=e281]:
                - strong [ref=e282]: 真实视频播报 1789961897121
                - generic [ref=e283]: 已发布
              - generic [ref=e284]: 暂无描述
            - generic [ref=e285]: 最后更新 2026/09/21 11:38
          - generic [ref=e286]:
            - button "复制大屏 真实视频播报 1789961897121" [ref=e287] [cursor=pointer]: 复制
            - button "删除大屏 真实视频播报 1789961897121" [ref=e291] [cursor=pointer]: 删除
        - article [ref=e295]:
          - link "资源版本测试 1789961905880 已发布 暂无描述 最后更新 2026/09/21 11:38" [ref=e296]:
            - /url: /studio/screens/e2955248-077a-4bbb-bd9d-1aa117618adc/edit
            - generic [ref=e303]:
              - generic [ref=e304]:
                - strong [ref=e305]: 资源版本测试 1789961905880
                - generic [ref=e306]: 已发布
              - generic [ref=e307]: 暂无描述
            - generic [ref=e308]: 最后更新 2026/09/21 11:38
          - generic [ref=e309]:
            - button "复制大屏 资源版本测试 1789961905880" [ref=e310] [cursor=pointer]: 复制
            - button "删除大屏 资源版本测试 1789961905880" [ref=e314] [cursor=pointer]: 删除
        - article [ref=e318]:
          - link "Plugin firefox 1789961928884 已发布 暂无描述 最后更新 2026/09/21 11:38" [ref=e319]:
            - /url: /studio/screens/041a3e06-fd2a-4e7e-b2b7-078cd5faceaf/edit
            - generic [ref=e326]:
              - generic [ref=e327]:
                - strong [ref=e328]: Plugin firefox 1789961928884
                - generic [ref=e329]: 已发布
              - generic [ref=e330]: 暂无描述
            - generic [ref=e331]: 最后更新 2026/09/21 11:38
          - generic [ref=e332]:
            - button "复制大屏 Plugin firefox 1789961928884" [ref=e333] [cursor=pointer]: 复制
            - button "删除大屏 Plugin firefox 1789961928884" [ref=e337] [cursor=pointer]: 删除
        - article [ref=e341]:
          - link "E2E 第一阶段模板入口 草稿 标题、核心指标、趋势、排行和明细表的通用起始布局。 最后更新 2026/09/21 11:39" [ref=e342]:
            - /url: /studio/screens/7c6441b0-4817-4570-b09c-ad314fc6f198/edit
            - generic [ref=e349]:
              - generic [ref=e350]:
                - strong [ref=e351]: E2E 第一阶段模板入口
                - generic [ref=e352]: 草稿
              - generic [ref=e353]: 标题、核心指标、趋势、排行和明细表的通用起始布局。
            - generic [ref=e354]: 最后更新 2026/09/21 11:39
          - generic [ref=e355]:
            - button "复制大屏 E2E 第一阶段模板入口" [ref=e356] [cursor=pointer]: 复制
            - button "删除大屏 E2E 第一阶段模板入口" [ref=e360] [cursor=pointer]: 删除
        - article [ref=e364]:
          - link "E2E 第一阶段交替创作 已发布 暂无描述 最后更新 2026/09/21 11:39" [ref=e365]:
            - /url: /studio/screens/e4ff2538-9f25-40e7-8ac7-3fbb20a05b59/edit
            - generic [ref=e372]:
              - generic [ref=e373]:
                - strong [ref=e374]: E2E 第一阶段交替创作
                - generic [ref=e375]: 已发布
              - generic [ref=e376]: 暂无描述
            - generic [ref=e377]: 最后更新 2026/09/21 11:39
          - generic [ref=e378]:
            - button "复制大屏 E2E 第一阶段交替创作" [ref=e379] [cursor=pointer]: 复制
            - button "删除大屏 E2E 第一阶段交替创作" [ref=e383] [cursor=pointer]: 删除
        - article [ref=e387]:
          - link "E2E 第一阶段访问限制 已发布 暂无描述 最后更新 2026/09/21 11:39" [ref=e388]:
            - /url: /studio/screens/801bd7b8-8309-4a39-8f69-649927d7efd5/edit
            - generic [ref=e395]:
              - generic [ref=e396]:
                - strong [ref=e397]: E2E 第一阶段访问限制
                - generic [ref=e398]: 已发布
              - generic [ref=e399]: 暂无描述
            - generic [ref=e400]: 最后更新 2026/09/21 11:39
          - generic [ref=e401]:
            - button "复制大屏 E2E 第一阶段访问限制" [ref=e402] [cursor=pointer]: 复制
            - button "删除大屏 E2E 第一阶段访问限制" [ref=e406] [cursor=pointer]: 删除
        - article [ref=e410]:
          - link "E2E 窄视口编辑器 草稿 暂无描述 最后更新 2026/09/21 11:39" [ref=e411]:
            - /url: /studio/screens/30fc260a-5f7e-4ff2-a807-6c0699c6dd06/edit
            - generic [ref=e418]:
              - generic [ref=e419]:
                - strong [ref=e420]: E2E 窄视口编辑器
                - generic [ref=e421]: 草稿
              - generic [ref=e422]: 暂无描述
            - generic [ref=e423]: 最后更新 2026/09/21 11:39
          - generic [ref=e424]:
            - button "复制大屏 E2E 窄视口编辑器" [ref=e425] [cursor=pointer]: 复制
            - button "删除大屏 E2E 窄视口编辑器" [ref=e429] [cursor=pointer]: 删除
        - article [ref=e433]:
          - link "协作权限 firefox-1789961964312 草稿 暂无描述 最后更新 2026/09/21 11:39" [ref=e434]:
            - /url: /studio/screens/c0e8ba41-26b0-4dc2-a9a4-c3a1f51add9b/edit
            - generic [ref=e441]:
              - generic [ref=e442]:
                - strong [ref=e443]: 协作权限 firefox-1789961964312
                - generic [ref=e444]: 草稿
              - generic [ref=e445]: 暂无描述
            - generic [ref=e446]: 最后更新 2026/09/21 11:39
          - generic [ref=e447]:
            - button "复制大屏 协作权限 firefox-1789961964312" [ref=e448] [cursor=pointer]: 复制
            - button "删除大屏 协作权限 firefox-1789961964312" [ref=e452] [cursor=pointer]: 删除
        - article [ref=e456]:
          - link "E2E 运营大屏 草稿 暂无描述 最后更新 2026/09/21 11:39" [ref=e457]:
            - /url: /studio/screens/097312f2-a80a-4ae5-bee9-df702a502876/edit
            - generic [ref=e464]:
              - generic [ref=e465]:
                - strong [ref=e466]: E2E 运营大屏
                - generic [ref=e467]: 草稿
              - generic [ref=e468]: 暂无描述
            - generic [ref=e469]: 最后更新 2026/09/21 11:39
          - generic [ref=e470]:
            - button "复制大屏 E2E 运营大屏" [ref=e471] [cursor=pointer]: 复制
            - button "删除大屏 E2E 运营大屏" [ref=e475] [cursor=pointer]: 删除
        - article [ref=e479]:
          - link "E2E 多选拖拽 草稿 暂无描述 最后更新 2026/09/21 11:39" [ref=e480]:
            - /url: /studio/screens/f7fb2bdc-b5df-4270-b8e9-af04fa8c6926/edit
            - generic [ref=e487]:
              - generic [ref=e488]:
                - strong [ref=e489]: E2E 多选拖拽
                - generic [ref=e490]: 草稿
              - generic [ref=e491]: 暂无描述
            - generic [ref=e492]: 最后更新 2026/09/21 11:39
          - generic [ref=e493]:
            - button "复制大屏 E2E 多选拖拽" [ref=e494] [cursor=pointer]: 复制
            - button "删除大屏 E2E 多选拖拽" [ref=e498] [cursor=pointer]: 删除
        - article [ref=e502]:
          - link "E2E 深色播放 已发布 暂无描述 最后更新 2026/09/21 11:39" [ref=e503]:
            - /url: /studio/screens/ccc31183-baac-4e54-a788-1f361a360931/edit
            - generic [ref=e510]:
              - generic [ref=e511]:
                - strong [ref=e512]: E2E 深色播放
                - generic [ref=e513]: 已发布
              - generic [ref=e514]: 暂无描述
            - generic [ref=e515]: 最后更新 2026/09/21 11:39
          - generic [ref=e516]:
            - button "复制大屏 E2E 深色播放" [ref=e517] [cursor=pointer]: 复制
            - button "删除大屏 E2E 深色播放" [ref=e521] [cursor=pointer]: 删除
        - article [ref=e525]:
          - link "E2E 浅色播放 已发布 暂无描述 最后更新 2026/09/21 11:39" [ref=e526]:
            - /url: /studio/screens/d09d55a2-387d-40e1-a744-95e2165bc9d8/edit
            - generic [ref=e533]:
              - generic [ref=e534]:
                - strong [ref=e535]: E2E 浅色播放
                - generic [ref=e536]: 已发布
              - generic [ref=e537]: 暂无描述
            - generic [ref=e538]: 最后更新 2026/09/21 11:39
          - generic [ref=e539]:
            - button "复制大屏 E2E 浅色播放" [ref=e540] [cursor=pointer]: 复制
            - button "删除大屏 E2E 浅色播放" [ref=e544] [cursor=pointer]: 删除
        - article [ref=e548]:
          - link "E2E 组件错误隔离 已发布 暂无描述 最后更新 2026/09/21 11:39" [ref=e549]:
            - /url: /studio/screens/d0c1e66d-502a-4a46-a716-80f04381bc0c/edit
            - generic [ref=e556]:
              - generic [ref=e557]:
                - strong [ref=e558]: E2E 组件错误隔离
                - generic [ref=e559]: 已发布
              - generic [ref=e560]: 暂无描述
            - generic [ref=e561]: 最后更新 2026/09/21 11:39
          - generic [ref=e562]:
            - button "复制大屏 E2E 组件错误隔离" [ref=e563] [cursor=pointer]: 复制
            - button "删除大屏 E2E 组件错误隔离" [ref=e567] [cursor=pointer]: 删除
        - article [ref=e571]:
          - link "E2E 直连嵌入 已发布 暂无描述 最后更新 2026/09/21 11:39" [ref=e572]:
            - /url: /studio/screens/3fd3777e-da69-404e-a3ea-25a218792e2b/edit
            - generic [ref=e579]:
              - generic [ref=e580]:
                - strong [ref=e581]: E2E 直连嵌入
                - generic [ref=e582]: 已发布
              - generic [ref=e583]: 暂无描述
            - generic [ref=e584]: 最后更新 2026/09/21 11:39
          - generic [ref=e585]:
            - button "复制大屏 E2E 直连嵌入" [ref=e586] [cursor=pointer]: 复制
            - button "删除大屏 E2E 直连嵌入" [ref=e590] [cursor=pointer]: 删除
        - article [ref=e594]:
          - link "E2E 安全嵌入 已发布 暂无描述 最后更新 2026/09/21 11:39" [ref=e595]:
            - /url: /studio/screens/41131c4a-7de7-4a37-92aa-d5e3e74cb74d/edit
            - generic [ref=e602]:
              - generic [ref=e603]:
                - strong [ref=e604]: E2E 安全嵌入
                - generic [ref=e605]: 已发布
              - generic [ref=e606]: 暂无描述
            - generic [ref=e607]: 最后更新 2026/09/21 11:39
          - generic [ref=e608]:
            - button "复制大屏 E2E 安全嵌入" [ref=e609] [cursor=pointer]: 复制
            - button "删除大屏 E2E 安全嵌入" [ref=e613] [cursor=pointer]: 删除
        - article [ref=e617]:
          - link "数字人发布 1789962032984 已发布 暂无描述 最后更新 2026/09/21 11:40" [ref=e618]:
            - /url: /studio/screens/ccef2eef-6619-4e8a-bfeb-c7482f807d5e/edit
            - generic [ref=e625]:
              - generic [ref=e626]:
                - strong [ref=e627]: 数字人发布 1789962032984
                - generic [ref=e628]: 已发布
              - generic [ref=e629]: 暂无描述
            - generic [ref=e630]: 最后更新 2026/09/21 11:40
          - generic [ref=e631]:
            - button "复制大屏 数字人发布 1789962032984" [ref=e632] [cursor=pointer]: 复制
            - button "删除大屏 数字人发布 1789962032984" [ref=e636] [cursor=pointer]: 删除
        - article [ref=e640]:
          - link "结构化话术持久化 1789962035495 已发布 暂无描述 最后更新 2026/09/21 11:40" [ref=e641]:
            - /url: /studio/screens/c4f1c52b-a063-4e4c-b526-afcaa2643979/edit
            - generic [ref=e648]:
              - generic [ref=e649]:
                - strong [ref=e650]: 结构化话术持久化 1789962035495
                - generic [ref=e651]: 已发布
              - generic [ref=e652]: 暂无描述
            - generic [ref=e653]: 最后更新 2026/09/21 11:40
          - generic [ref=e654]:
            - button "复制大屏 结构化话术持久化 1789962035495" [ref=e655] [cursor=pointer]: 复制
            - button "删除大屏 结构化话术持久化 1789962035495" [ref=e659] [cursor=pointer]: 删除
        - article [ref=e663]:
          - link "数字人 TTS 闭环 1789962037336 已发布 暂无描述 最后更新 2026/09/21 11:40" [ref=e664]:
            - /url: /studio/screens/f3dd4381-fe3b-4030-94c7-f27f3b190422/edit
            - generic [ref=e671]:
              - generic [ref=e672]:
                - strong [ref=e673]: 数字人 TTS 闭环 1789962037336
                - generic [ref=e674]: 已发布
              - generic [ref=e675]: 暂无描述
            - generic [ref=e676]: 最后更新 2026/09/21 11:40
          - generic [ref=e677]:
            - button "复制大屏 数字人 TTS 闭环 1789962037336" [ref=e678] [cursor=pointer]: 复制
            - button "删除大屏 数字人 TTS 闭环 1789962037336" [ref=e682] [cursor=pointer]: 删除
        - article [ref=e686]:
          - link "数字人嵌入 1789962041243 已发布 暂无描述 最后更新 2026/09/21 11:40" [ref=e687]:
            - /url: /studio/screens/fc48d75e-b38e-4bca-ae4e-7770578c16fb/edit
            - generic [ref=e694]:
              - generic [ref=e695]:
                - strong [ref=e696]: 数字人嵌入 1789962041243
                - generic [ref=e697]: 已发布
              - generic [ref=e698]: 暂无描述
            - generic [ref=e699]: 最后更新 2026/09/21 11:40
          - generic [ref=e700]:
            - button "复制大屏 数字人嵌入 1789962041243" [ref=e701] [cursor=pointer]: 复制
            - button "删除大屏 数字人嵌入 1789962041243" [ref=e705] [cursor=pointer]: 删除
        - article [ref=e709]:
          - link "数字人跨源嵌入 1789962042251 已发布 暂无描述 最后更新 2026/09/21 11:40" [ref=e710]:
            - /url: /studio/screens/476c74c5-decb-4c1c-9a8f-18d1637b6df4/edit
            - generic [ref=e717]:
              - generic [ref=e718]:
                - strong [ref=e719]: 数字人跨源嵌入 1789962042251
                - generic [ref=e720]: 已发布
              - generic [ref=e721]: 暂无描述
            - generic [ref=e722]: 最后更新 2026/09/21 11:40
          - generic [ref=e723]:
            - button "复制大屏 数字人跨源嵌入 1789962042251" [ref=e724] [cursor=pointer]: 复制
            - button "删除大屏 数字人跨源嵌入 1789962042251" [ref=e728] [cursor=pointer]: 删除
        - article [ref=e732]:
          - link "数字人访问撤销 1789962043870 已发布 暂无描述 最后更新 2026/09/21 11:40" [ref=e733]:
            - /url: /studio/screens/9f22b79d-58d2-4af0-a159-c565de541180/edit
            - generic [ref=e740]:
              - generic [ref=e741]:
                - strong [ref=e742]: 数字人访问撤销 1789962043870
                - generic [ref=e743]: 已发布
              - generic [ref=e744]: 暂无描述
            - generic [ref=e745]: 最后更新 2026/09/21 11:40
          - generic [ref=e746]:
            - button "复制大屏 数字人访问撤销 1789962043870" [ref=e747] [cursor=pointer]: 复制
            - button "删除大屏 数字人访问撤销 1789962043870" [ref=e751] [cursor=pointer]: 删除
        - article [ref=e755]:
          - link "真实视频播报 1789962045751 已发布 暂无描述 最后更新 2026/09/21 11:40" [ref=e756]:
            - /url: /studio/screens/e5f3a3a3-b644-4bc7-b686-7f7934b95c8e/edit
            - generic [ref=e763]:
              - generic [ref=e764]:
                - strong [ref=e765]: 真实视频播报 1789962045751
                - generic [ref=e766]: 已发布
              - generic [ref=e767]: 暂无描述
            - generic [ref=e768]: 最后更新 2026/09/21 11:40
          - generic [ref=e769]:
            - button "复制大屏 真实视频播报 1789962045751" [ref=e770] [cursor=pointer]: 复制
            - button "删除大屏 真实视频播报 1789962045751" [ref=e774] [cursor=pointer]: 删除
        - article [ref=e778]:
          - link "资源版本测试 1789962053466 已发布 暂无描述 最后更新 2026/09/21 11:40" [ref=e779]:
            - /url: /studio/screens/4f50188f-0219-4339-a863-3de3fd1c9903/edit
            - generic [ref=e786]:
              - generic [ref=e787]:
                - strong [ref=e788]: 资源版本测试 1789962053466
                - generic [ref=e789]: 已发布
              - generic [ref=e790]: 暂无描述
            - generic [ref=e791]: 最后更新 2026/09/21 11:40
          - generic [ref=e792]:
            - button "复制大屏 资源版本测试 1789962053466" [ref=e793] [cursor=pointer]: 复制
            - button "删除大屏 资源版本测试 1789962053466" [ref=e797] [cursor=pointer]: 删除
        - article [ref=e801]:
          - link "Plugin webkit 1789962080153 已发布 暂无描述 最后更新 2026/09/21 11:41" [ref=e802]:
            - /url: /studio/screens/9d484436-6607-4952-989a-75b27f863c0b/edit
            - generic [ref=e809]:
              - generic [ref=e810]:
                - strong [ref=e811]: Plugin webkit 1789962080153
                - generic [ref=e812]: 已发布
              - generic [ref=e813]: 暂无描述
            - generic [ref=e814]: 最后更新 2026/09/21 11:41
          - generic [ref=e815]:
            - button "复制大屏 Plugin webkit 1789962080153" [ref=e816] [cursor=pointer]: 复制
            - button "删除大屏 Plugin webkit 1789962080153" [ref=e820] [cursor=pointer]: 删除
        - article [ref=e824]:
          - link "协作权限 webkit-1789962148721 草稿 暂无描述 最后更新 2026/09/21 11:42" [ref=e825]:
            - /url: /studio/screens/e043dd03-34ab-441b-926d-5d37f37a1fbd/edit
            - generic [ref=e832]:
              - generic [ref=e833]:
                - strong [ref=e834]: 协作权限 webkit-1789962148721
                - generic [ref=e835]: 草稿
              - generic [ref=e836]: 暂无描述
            - generic [ref=e837]: 最后更新 2026/09/21 11:42
          - generic [ref=e838]:
            - button "复制大屏 协作权限 webkit-1789962148721" [ref=e839] [cursor=pointer]: 复制
            - button "删除大屏 协作权限 webkit-1789962148721" [ref=e843] [cursor=pointer]: 删除
      - dialog [ref=e847]:
        - generic [ref=e848]:
          - generic [ref=e849]:
            - heading "新建大屏" [level=2] [ref=e850]
            - paragraph [ref=e851]: 创建后将直接进入编辑器。
          - button "关闭" [ref=e852] [cursor=pointer]
        - generic [ref=e856]:
          - generic [ref=e857]:
            - generic [ref=e858]: 大屏名称
            - textbox "大屏名称 A screen with this name already exists." [ref=e859]:
              - /placeholder: 例如：运营总览
              - text: E2E 多选拖拽
            - generic [ref=e860]: A screen with this name already exists.
          - generic [ref=e861]:
            - button "取消" [ref=e862]
            - button "创建并编辑" [ref=e863] [cursor=pointer]
```

# Test source

```ts
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
  156 |   await expect(page).toHaveScreenshot(editorSnapshot, {
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
> 223 |   await library.getByRole("button", { name: "文本", exact: true }).click();
      |                                                                  ^ Error: locator.click: Test timeout of 45000ms exceeded.
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
  257 |   const deltas = after.map((position, index) => ({
  258 |     x: position.x - before[index]!.x,
  259 |     y: position.y - before[index]!.y,
  260 |   }));
  261 |   expect(deltas[0]!.x).toBeGreaterThan(20);
  262 |   expect(deltas[0]!.y).toBeGreaterThan(10);
  263 |   expect(Math.abs(deltas[0]!.x - deltas[1]!.x)).toBeLessThanOrEqual(1);
  264 |   expect(Math.abs(deltas[0]!.y - deltas[1]!.y)).toBeLessThanOrEqual(1);
  265 | 
  266 |   const beforeSizes = await components.evaluateAll((items) =>
  267 |     items.map((item) => ({
  268 |       width: Number.parseFloat((item as HTMLElement).style.width),
  269 |       height: Number.parseFloat((item as HTMLElement).style.height),
  270 |     })),
  271 |   );
  272 |   const groupResizeHandle = page.locator(".moveable-control-box .moveable-se");
  273 |   await expect(groupResizeHandle).toBeVisible();
  274 |   const resizeBox = await groupResizeHandle.boundingBox();
  275 |   expect(resizeBox).not.toBeNull();
  276 |   await page.mouse.move(
  277 |     resizeBox!.x + resizeBox!.width / 2,
  278 |     resizeBox!.y + resizeBox!.height / 2,
  279 |   );
  280 |   await page.mouse.down();
  281 |   await page.mouse.move(
  282 |     resizeBox!.x + resizeBox!.width / 2 + 40,
  283 |     resizeBox!.y + resizeBox!.height / 2 + 30,
  284 |     { steps: 6 },
  285 |   );
  286 |   await page.mouse.up();
  287 |   const resized = await components.evaluateAll((items) =>
  288 |     items.map((item) => ({
  289 |       x: Number.parseFloat((item as HTMLElement).style.left),
  290 |       y: Number.parseFloat((item as HTMLElement).style.top),
  291 |       width: Number.parseFloat((item as HTMLElement).style.width),
  292 |       height: Number.parseFloat((item as HTMLElement).style.height),
  293 |     })),
  294 |   );
  295 |   expect(resized[0]!.width).toBeGreaterThan(beforeSizes[0]!.width);
  296 |   expect(resized[0]!.height).toBeGreaterThan(beforeSizes[0]!.height);
  297 |   expect(resized[1]!.width).toBeGreaterThan(beforeSizes[1]!.width);
  298 |   expect(resized[1]!.height).toBeGreaterThan(beforeSizes[1]!.height);
  299 | 
  300 |   await expect(
  301 |     page.getByLabel("编辑器工具栏").getByText("未保存"),
  302 |   ).toBeVisible();
  303 |   await expect(
  304 |     page.getByLabel("编辑器工具栏").getByText("已保存"),
  305 |   ).toBeVisible({ timeout: 10_000 });
  306 |   await page.reload();
  307 |   await expect(components).toHaveCount(2);
  308 |   const persisted = await page.locator("[data-canvas-component]").evaluateAll((items) =>
  309 |     items.map((item) => ({
  310 |       x: Number.parseFloat((item as HTMLElement).style.left),
  311 |       y: Number.parseFloat((item as HTMLElement).style.top),
  312 |     })),
  313 |   );
  314 |   expect(persisted).toEqual(
  315 |     resized.map(({ x, y }) => ({ x, y })),
  316 |   );
  317 | });
  318 | 
```