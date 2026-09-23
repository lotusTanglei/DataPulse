# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: first-stage-creation.spec.ts >> template creation enters the shared screen editor
- Location: e2e/first-stage-creation.spec.ts:14:1

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
      - code: d131ea0a-b4ea-4fdc-84e3-b5edafadfe27
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
    - dialog "从模板创建":
      - heading "从模板创建" [level=2]
      - paragraph: 选择后仍会进入同一个编辑器，可继续绑定数据和调整布局。
      - button "关闭模板选择"
      - text: 大屏名称
      - textbox "大屏名称":
        - /placeholder: 例如：华东区域经营分析
        - text: E2E 第一阶段模板入口
      - button "总览网格 总览布局" [pressed]:
        - strong: 总览网格
        - text: 总览布局
      - button "趋势聚焦 趋势分析":
        - strong: 趋势聚焦
        - text: 趋势分析
      - button "对比分析 对比分析":
        - strong: 对比分析
        - text: 对比分析
      - button "状态墙 状态布局":
        - strong: 状态墙
        - text: 状态布局
      - button "分析工作台 分析布局":
        - strong: 分析工作台
        - text: 分析布局
      - text: 数据总览 用统一的视觉层级组织核心指标与明细信息 演示数据
      - paragraph: 核心指标
      - strong: "64"
      - text: 演示数据
      - paragraph: 完成数量
      - strong: "77"
      - text: 演示数据
      - paragraph: 平均效率
      - strong: "62"
      - text: 演示数据
      - paragraph: 异常数量
      - strong: "75"
      - text: 演示数据 演示数据
      - strong: 分类排行
      - text: 6 项
      - list:
        - listitem:
          - text: 01 区域-01
          - emphasis
          - strong: "998"
        - listitem:
          - text: 02 区域-02
          - emphasis
          - strong: "905"
        - listitem:
          - text: 03 区域-03
          - emphasis
          - strong: "775"
        - listitem:
          - text: 04 区域-04
          - emphasis
          - strong: "701"
        - listitem:
          - text: 05 区域-05
          - emphasis
          - strong: "606"
        - listitem:
          - text: 06 区域-06
          - emphasis
          - strong: "535"
      - text: 演示数据
      - table:
        - rowgroup:
          - row "编号 对象 状态 完成率 更新时间":
            - columnheader "编号"
            - columnheader "对象"
            - columnheader "状态"
            - columnheader "完成率"
            - columnheader "更新时间"
        - rowgroup:
          - row "ID-260831 对象-01 进行中 71 08/20 08:30":
            - cell "ID-260831"
            - cell "对象-01"
            - cell "进行中"
            - cell "71"
            - cell "08/20 08:30"
          - row "ID-260832 对象-02 待确认 65 08/21 09:30":
            - cell "ID-260832"
            - cell "对象-02"
            - cell "待确认"
            - cell "65"
            - cell "08/21 09:30"
          - row "ID-260833 对象-03 已完成 62 08/22 10:30":
            - cell "ID-260833"
            - cell "对象-03"
            - cell "已完成"
            - cell "62"
            - cell "08/22 10:30"
          - row "ID-260834 对象-04 异常 59 08/23 11:30":
            - cell "ID-260834"
            - cell "对象-04"
            - cell "异常"
            - cell "59"
            - cell "08/23 11:30"
          - row "ID-260835 对象-01 进行中 73 08/24 12:30":
            - cell "ID-260835"
            - cell "对象-01"
            - cell "进行中"
            - cell "73"
            - cell "08/24 12:30"
          - row "ID-260836 对象-02 待确认 51 08/25 13:30":
            - cell "ID-260836"
            - cell "对象-02"
            - cell "待确认"
            - cell "51"
            - cell "08/25 13:30"
          - row "ID-260837 对象-03 已完成 60 08/26 14:30":
            - cell "ID-260837"
            - cell "对象-03"
            - cell "已完成"
            - cell "60"
            - cell "08/26 14:30"
          - row "ID-260838 对象-04 异常 68 08/27 15:30":
            - cell "ID-260838"
            - cell "对象-04"
            - cell "异常"
            - cell "68"
            - cell "08/27 15:30"
      - paragraph: 总览布局
      - heading "总览网格" [level=3]
      - paragraph: 标题、核心指标、趋势、排行和明细表的通用起始布局。
      - text: 1920 × 1080 · 含演示数据
      - button "取消"
      - button "使用此模板"
```

# Test source

```ts
  1   | import { expect, test } from "@playwright/test";
  2   | 
  3   | import {
  4   |   apiGet,
  5   |   apiPatch,
  6   |   apiPost,
  7   |   appOrigin,
  8   |   authenticate,
  9   |   generateDisplayKey,
  10  |   type ScreenRecord,
  11  | } from "./helpers.js";
  12  | import { loadRuntimeConfig } from "./runtime-config.js";
  13  | 
  14  | test("template creation enters the shared screen editor", async ({ page }) => {
  15  |   await authenticate(page);
  16  |   await page.goto("/studio/screens");
  17  |   await page.getByRole("button", { name: "从模板创建" }).first().click();
  18  | 
  19  |   const dialog = page.getByRole("dialog", { name: "从模板创建" });
  20  |   await expect(dialog.getByLabel("大屏模板").getByRole("button")).toHaveCount(5);
  21  |   await dialog.getByLabel("大屏名称").fill("E2E 第一阶段模板入口");
  22  |   await dialog.getByRole("button", { name: "使用此模板" }).click();
  23  | 
> 24  |   await expect(page.getByLabel("大屏编辑器")).toBeVisible();
      |                                          ^ Error: expect(locator).toBeVisible() failed
  25  |   const layersPanel = page.locator('section.layers-panel[aria-label="图层"]');
  26  |   await expect(layersPanel.locator("[data-layer-id]")).toHaveCount(9);
  27  |   await expect(page.getByText("数据总览")).toBeVisible();
  28  | });
  29  | 
  30  | test("blank creation supports hand editing, AI preview, confirmation, undo, redo, and playback", async ({
  31  |   page,
  32  | }) => {
  33  |   test.setTimeout(75_000);
  34  |   await authenticate(page);
  35  |   const publishRequests: string[] = [];
  36  |   page.on("request", (request) => {
  37  |     if (request.method() === "POST" && request.url().includes("/publish")) {
  38  |       publishRequests.push(request.url());
  39  |     }
  40  |   });
  41  | 
  42  |   await page.goto("/studio/screens");
  43  |   await page.getByRole("button", { name: /新建大屏/ }).first().click();
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
```