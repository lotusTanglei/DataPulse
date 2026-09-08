# DataPulse 已知问题清单

本文档记录自测期间发现、已确认但暂不立即修复的问题。问题完成统一修复并通过验收后，从“待修复”移动到“已解决”。

## 待修复

### DP-003 Firefox/WebKit 编辑器视觉门禁未建立独立可评审基线

- **发现日期：** 2026-09-08
- **状态：** 待处理（第二阶段门禁失败）
- **影响范围：** Firefox 153、WebKit 26.5 的完整 E2E 编辑器视觉回归
- **现象：** 两个浏览器均为 15/16；`screen-editor.spec.ts` 把浏览器实际图与 Chromium Darwin `editor-shell.png` 比较，Firefox 差 16,472 像素（约 1%），WebKit 差 18,400 像素（约 1%）。失败发生在视觉断言处，因此该测试后续点击联动和刷新步骤不能计入跨浏览器通过。
- **人工核对：** 两张 actual 均非空，主要结构和数据可见；Firefox 组件列表滚动位置与 Chromium 基线明显不同，文字和图表也存在引擎渲染差异。尚不能证明全部差异只是抗锯齿，不应直接接受基线。
- **证据：** 首次结果为 `test-evidence/automation-20260908/AUTO-018-firefox-e2e.log`、`AUTO-019-webkit-e2e.log`；修改后最终复跑为 `AUTO-032-firefox-e2e-final.log`、`AUTO-033-webkit-e2e-final.log`；actual/diff/expected 与脱敏错误上下文位于 `test-evidence/blackbox-20260908/cross-browser/`。原始 trace 可能含临时会话值，未保留。
- **后续动作：** 由产品/设计评审 actual/diff，区分真实布局问题和浏览器渲染差异；修复后或建立独立浏览器基线后完整复跑。未经评审不得更新快照。

## 已解决

### DP-002 浅色播放视觉夹具使用过期主题令牌

- **发现日期：** 2026-09-08
- **状态：** 已解决（测试契约修复、人工视觉评审和普通模式复跑完成）
- **影响范围：** Chromium `light-player.png` 视觉回归；产品运行时主题协议未改变
- **现象：** E2E fixture 使用 `component_surface` / `component_border`，当前运行时读取 `panel_background` / `panel_border`。历史浅色快照因此保留深色数据面板，同时把文字切为深色，KPI、坐标、图例和表格低对比度。
- **修复：** fixture 改用当前主题令牌并补全浅色面板、边框、网格和坐标 token；E2E 新增 KPI 背景为白色、文字为深色的计算样式断言。
- **评审证据：** 首先在普通模式生成失败 actual/diff，人工确认修正画面可读且布局/数据未发生非预期变化，评审记录位于 `test-evidence/blackbox-20260908/BB-002/light-theme-review/review.md`。随后只更新 `apps/web/e2e/snapshots/darwin/light-player.png`，定向普通模式复跑 1/1 通过。

### DP-001 数据源连接凭据被误识别为管理员登录凭据

- **发现日期：** 2026-08-08
- **状态：** 已解决（代码修复和自动化回归完成）
- **影响范围：** 新建 PostgreSQL、MySQL / MariaDB 数据源；编辑数据源时也需要回归验证
- **现象：** 用户登录 DataPulse 后进入“新建数据源”，浏览器或密码管理器会把 DataPulse 管理员用户名和密码自动填入数据库用户名、密码字段。
- **风险：** 用户可能在未察觉时使用错误数据库账号发起连接测试；管理员密码会短暂出现在无关的连接表单中，增加误提交风险。

#### 复现步骤

1. 使用浏览器密码管理器保存 DataPulse 管理员登录凭据。
2. 登录 Studio，打开“数据源 → 新建数据源”。
3. 将连接器切换为 PostgreSQL 或 MySQL / MariaDB。
4. 观察数据库用户名和密码字段被自动填入管理员登录凭据。

#### 已确认根因

`DatasourceFormView.vue` 将数据库用户名声明为 `autocomplete="username"`，并在新建数据源时将数据库密码声明为 `autocomplete="current-password"`。浏览器因此把数据库连接配置误判为当前站点的登录表单。

#### 已确认修复方向

- 数据源表单整体不参与登录凭据自动填充。
- 数据库用户名和密码必须由用户手动输入。
- DataPulse 登录、初始化和修改管理员密码页面继续使用正确的标准自动填充语义，不受本修复影响。
- 不使用隐藏用户名/密码输入框欺骗浏览器。

#### 验收标准

1. 新建 PostgreSQL、MySQL / MariaDB 数据源时，数据库用户名和密码初始值为空，浏览器不会填入管理员凭据。
2. 编辑数据源时密码仍保持不回显，用户名只显示已保存的数据库用户名。
3. 手动输入数据库凭据后，连接测试、保存和更新行为不变。
4. 登录页面仍支持密码管理器正常填充管理员账号。
5. 前端测试固定表单的 `autocomplete` 语义，并对新建、编辑两条路径进行回归验证。

#### 本次验证证据

- `DatasourceFormView.vue` 已将数据源表单设置为 `autocomplete="off"`，用户名和密码字段设置为 `autocomplete="new-password"`，编辑密码保持为空。
- `apps/web/src/features/datasources/datasource-form.test.ts` 已覆盖新建和编辑路径；定向执行结果为 5 files/30 tests passed。
- 真实密码管理器是否在特定浏览器策略下仍触发填充，仍建议使用专用测试凭据进行人工抽样，不得使用生产凭据。
