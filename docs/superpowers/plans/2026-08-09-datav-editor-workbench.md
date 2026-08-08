# DataV 风格大屏编辑器工作台实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification checkpoints.

**目标：** 将 DataPulse 大屏编辑器升级为以 DataV 工作台逻辑为主、具备清晰画布交互和固定 1920×1080 坐标体系的可用编辑器。

**架构：** 保留现有 DashboardDocument 和 Pinia 编辑器 Store 作为唯一状态源；将几何计算、画布交互、属性面板和工具栏分别收敛到独立模块。编辑器只操作草稿，预览和播放继续复用运行时组件，发布仍是明确的版本快照操作。

**技术栈：** Vue 3、TypeScript、Pinia、Moveable、Selecto、Vitest、CSS。

## 全局约束

- 画布坐标固定为 1920 × 1080，持久化位置不得使用视口像素。
- 播放和嵌入保持 16:9 等比缩放，使用 contain，不拉伸、不裁切。
- 允许组件覆盖，必须提供选区、重叠区域和层级反馈。
- 默认 10px 网格和吸附；`Alt` 临时关闭吸附。
- 单管理员、单页草稿、明确发布；不引入多用户、模板市场或复杂权限。
- 数据绑定修改立即进入草稿，查询预览单独触发。
- 不泄露数据库密码、显示密钥、签名密钥或会话令牌。

---

### 任务 1：几何吸附和对齐计算

**文件：**

- 修改：`apps/web/src/features/screens/editor/geometry.ts`
- 测试：`apps/web/src/features/screens/editor/geometry.test.ts`（新建）
- 修改：`apps/web/src/features/screens/editor/canvas.test.ts`

**接口：**

- 产生 `snapFrame(frame, context, options)`，返回吸附后的位置和可视化 guide 数据。
- 产生 `selectionBounds(frames)`、`alignFrames(frames, alignment)` 和 `distributeFrames(frames, axis)`。
- 保留 `snapToGrid`、`translateFrame` 的兼容行为。

- [ ] 写失败测试：画布边缘、网格、兄弟组件边缘/中心线、间距和边界限制。
- [ ] 运行 `pnpm --filter @datapulse/web test -- geometry`，确认新测试失败。
- [ ] 实现纯函数几何计算，阈值按设计坐标传入，禁止读取 DOM。
- [ ] 增加水平/垂直对齐和等间距分布计算。
- [ ] 运行几何测试和现有画布测试，确认通过。

### 任务 2：画布选区、悬停、重叠和吸附反馈

**文件：**

- 修改：`apps/web/src/features/screens/editor/ScreenCanvas.vue`
- 修改：`apps/web/src/features/screens/editor/geometry.ts`
- 修改：`apps/web/src/features/screens/editor/canvas.test.ts`
- 修改：`apps/web/src/styles/base.css`

**接口：**

- `ScreenCanvas` 暴露 `setZoom`、`fitToViewport`、`alignSelection`、`distributeSelection`、`toggleGrid`、`toggleSnap`。
- 画布内部维护悬停组件 ID、网格状态、吸附状态和当前 guides，不写入 DashboardDocument。

- [ ] 写失败测试：多选整体边界、悬停标识、重叠组件标识、网格/吸附切换和 `Alt` 临时禁用。
- [ ] 调整 Moveable 和 Selecto 的缩放换算，确保 1920×1080 坐标不受 zoom 影响。
- [ ] 在拖动过程中计算 sibling/edge/center snap，并渲染 guide、间距和重叠提示。
- [ ] 允许通过 `Alt` 或工具栏关闭吸附；锁定组件不得进入可编辑目标。
- [ ] 对重叠组件采用顶层优先，提供 Alt 循环选择和图层树选择通道。
- [ ] 运行画布测试，验证拖拽、缩放、锁定、隐藏和多选没有回归。

### 任务 3：工具栏、图层和基础组合操作

**文件：**

- 修改：`apps/web/src/features/screens/editor/EditorToolbar.vue`
- 修改：`apps/web/src/features/screens/editor/LayersPanel.vue`
- 修改：`apps/web/src/features/screens/editor/ScreenCanvas.vue`
- 修改：`apps/web/src/features/screens/editor/commands.ts`
- 修改：`apps/web/src/features/screens/editor/commands.test.ts`
- 修改：`apps/web/src/features/screens/editor/canvas.test.ts`

**接口：**

- 新增 `group_components`、`ungroup_components` 或等价的编辑命令，保持成员属性和数据绑定不变。
- 工具栏通过事件调用画布的对齐、分布、网格和吸附操作。

- [ ] 写失败测试：置顶/置底、上移/下移、锁定/隐藏、多选组合和解散组合的一步撤销。
- [ ] 实现命令并确保历史记录能整体撤销。
- [ ] 扩展图层树显示组合节点、悬停状态、锁定/隐藏状态和层级操作。
- [ ] 扩展工具栏为选择、网格、吸附、对齐、分布、组合、层级、缩放、预览、保存和发布入口。
- [ ] 增加标准键盘快捷键并排除输入框内的误触发。
- [ ] 运行命令、画布和图层测试。

### 任务 4：属性面板 DataV 式分 Tab 和配置回填

**文件：**

- 修改：`apps/web/src/features/screens/editor/InspectorPanel.vue`
- 修改：`apps/web/src/features/screens/editor/inspector.test.ts`
- 修改：`apps/web/src/features/screens/ScreenEditorView.vue`
- 修改：`apps/web/src/styles/base.css`

**接口：**

- 属性面板分为“基础、数据、样式、交互、高级”五个 Tab。
- 组件切换时从 `ComponentInstance.frame/props/style/data_binding/interactions` 回填所有表单。
- 现有 `bindChart`、`setClickInteraction`、`updateTheme` 对外接口保持兼容。

- [ ] 写失败测试：切换组件后位置、数据绑定、聚合、主题、点击参数和高级状态正确回填。
- [ ] 实现 Tab 状态、空状态和组件能力过滤。
- [ ] 将配置变更立即派发到编辑器 Store，保留草稿自动保存。
- [ ] 将数据预览错误显示在数据 Tab 内，不覆盖整个工作台。
- [ ] 运行属性面板测试、类型检查和现有编辑器测试。

### 任务 5：工作区视觉和固定画布布局

**文件：**

- 修改：`apps/web/src/styles/base.css`
- 修改：`apps/web/src/features/screens/ScreenEditorView.vue`
- 修改：`apps/web/src/features/screens/editor/ComponentLibrary.vue`
- 修改：`apps/web/src/features/screens/editor/LayersPanel.vue`
- 修改：`apps/web/src/features/screens/editor/EditorToolbar.vue`

**接口：**

- 保持现有页面路由和组件 API，不改变播放页样式。

- [ ] 将编辑器调整为浅色工作区、独立画布、清晰面板边界和低装饰视觉。
- [ ] 为画布增加网格背景、画布外工作区、选区句柄、悬停轮廓、锁定和隐藏图标样式。
- [ ] 统一按钮、Tab、图层行、空状态和错误状态视觉。
- [ ] 确保窄窗口下左右面板不会覆盖画布核心区域，保持横向滚动或合理最小宽度。
- [ ] 运行 Web 构建并检查无 CSS 溢出、无新增无障碍错误。

### 任务 6：播放比例和组件级错误体验

**文件：**

- 检查/修改：`apps/web/src/features/runtime/ScreenRuntime.vue`
- 检查/修改：`apps/web/src/features/player/PlayerView.vue`
- 测试：`apps/web/src/features/player/standalone-player.test.ts`
- 测试：`apps/web/src/features/runtime/runtime.test.ts`
- 修改：`apps/web/src/styles/base.css`

**接口：**

- 保持 `/play/:screenId`、`/embed/:screenId` 和现有播放 API 不变。

- [ ] 写失败测试：非 16:9 容器 contain、无拉伸、播放错误中性提示。
- [ ] 确认播放视口和编辑器画布均以 1920×1080 作为逻辑尺寸。
- [ ] 将组件查询失败限制在单个组件，其他组件继续渲染。
- [ ] 运行播放器和运行时测试。

### 任务 7：集成回归和文档

**文件：**

- 修改：`docs/superpowers/specs/2026-08-09-datav-editor-workbench-design.md`（仅在实现偏离设计时更新）
- 修改：`README.md`（补充编辑器和本地签名密钥启动说明，如有必要）
- 测试：`apps/web/src/features/screens/editor/*.test.ts`

- [ ] 运行前端全量测试：`pnpm --filter @datapulse/web test`。
- [ ] 运行类型检查：`pnpm --filter @datapulse/web typecheck`。
- [ ] 运行构建：`pnpm --filter @datapulse/web build`。
- [ ] 运行后端全量测试：`uv run --package datapulse-server pytest apps/server/tests -q`。
- [ ] 运行 `git diff --check` 并确认 `.env`、数据库和构建产物未进入提交。
- [ ] 在本地浏览器验证：组件拖拽、吸附、覆盖选择、属性回填、预览、发布和播放链接。

