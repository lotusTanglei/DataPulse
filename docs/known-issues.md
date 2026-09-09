# DataPulse 已知问题清单

本文档记录自测期间发现、已确认但暂不立即修复的问题。问题完成统一修复并通过验收后，从“待修复”移动到“已解决”。

## 待修复

### DP-005 产品第二阶段目标环境门禁未关闭

- **发现日期：** 2026-09-08
- **状态：** 阻塞（不是未开发功能）
- **影响范围：** 第二阶段完成判定
- **现象：** 真实密码管理器、将要上线的完整代理链、物理 4K 设备和连续 8 小时播放没有目标环境证据。生产等价 Nginx、真实 Retina、4K 仿真和 10 分钟浸泡只能作为预检。
- **已有证据：** `test-evidence/blackbox-20260909/proxy-equivalent/`、`display-target/`、`soak-preflight-10m-final/`。
- **后续动作：** 严格按 `docs/PHASE_TWO_TARGET_ENVIRONMENT.md` 执行；在四项全部通过前不得标记第二阶段完成。

## 已解决

### DP-007 播放页缺少 favicon 产生控制台 404

- **发现日期：** 2026-09-09
- **状态：** 已解决（60 秒和 10 分钟浸泡复跑完成）
- **影响范围：** Studio、独立播放和嵌入共用的 Web 入口
- **现象：** 首次 10 分钟浸泡的业务查询和页面状态均正常，但浏览器自动请求 `/favicon.ico` 返回 404，严格 console 门禁失败。
- **修复：** Web 入口声明仓库内 `/favicon.svg`；浸泡错误记录只保存去除 query/hash 的 URL，防止凭据进入证据。
- **证据：** `AUTO-026` 保留首次失败；`AUTO-029` 60 秒 49/49、`AUTO-030` 10 分钟 427/427 均通过且 console error 为空。

### DP-006 Retina 视觉证据截取早于 Canvas 动画终态

- **发现日期：** 2026-09-09
- **状态：** 已解决（采证修正并人工复核）
- **影响范围：** 目标显示预检证据，不改变普通播放动画时长
- **现象：** 首张 Retina 截图中折线、柱状和饼图仍在入场动画，虽然自动断言 2/2，通过截图也不能判定视觉通过。
- **修复：** 截图前额外等待 Canvas 动画稳定；旧图另存为 `physical-retina-premature-canvas.png`，最终图不通过更新快照生成。
- **证据：** `AUTO-032-display-target-stable-canvas-final.log`；`test-evidence/blackbox-20260909/display-target/review.md`。

### DP-004 减少动效模式仍播放 ECharts 入场动画

- **发现日期：** 2026-09-09
- **状态：** 已解决（代码、单元测试、4K 仿真和人工视觉复核完成）
- **影响范围：** 折线、柱状、饼、雷达、热力、散点、漏斗和地图组件
- **现象：** 4K 仿真已报告 `prefers-reduced-motion: reduce`，但首张证据中的折线和饼图仍停在入场动画中，不能判定减少动效生效。
- **修复：** 运行时在媒体查询命中时把 ECharts 初始和更新动画禁用；不改变普通模式和组件级 `animation` 配置。
- **证据：** `chart-motion.test.ts` 2/2；修复后 `AUTO-025-display-target-reduced-motion.log` 2/2；`test-evidence/blackbox-20260909/display-target/emulated-4k.png` 已人工核对全部图表首帧完整。未更新视觉快照。

### DP-003 Firefox/WebKit 编辑器视觉门禁未建立独立可评审基线

- **发现日期：** 2026-09-08
- **状态：** 已解决（状态归一化、人工评审和完整复跑完成）
- **影响范围：** Firefox 153、WebKit 26.5 的完整 E2E 编辑器视觉回归
- **根因：** Firefox reload 后保留组件面板滚动位置；两个引擎与 Chromium 存在字体、Canvas 和细线栅格化差异，共用严格编辑器基线会产生稳定误报。
- **修复：** 截图前等待查询结束，将左右面板滚动到顶部并清理焦点；保留 Chromium 基线，评审 actual/diff 后只为 Firefox/WebKit 增加独立 Darwin 编辑器基线。
- **证据：** 评审记录位于 `test-evidence/blackbox-20260909/cross-browser/review.md`；Firefox `AUTO-007`、WebKit `AUTO-009` 和 Chromium `AUTO-010` 均为完整 16/16。未经评审未批量更新其他快照。

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
