# 2026-09-08 自动化证据索引

本目录记录产品第二阶段收尾命令的原始输出。最终结果以 `docs/PHASE_TWO_CLOSEOUT.md` 为准。

- `AUTO-001`～`AUTO-005`：契约、全量单元、类型、构建、完整 Chromium 16/16。
- `AUTO-007`～`AUTO-009`：PostgreSQL/MariaDB Compose 启动、13/13 集成测试和资源清理。
- `AUTO-010`～`AUTO-016`、`AUTO-021`：BB-001～BB-006 等价验证及修正后的复测；初始脚本假设错误保留，不计为产品失败。
- `AUTO-018`、`AUTO-019`：Firefox/WebKit 各 15/16，编辑器视觉断言失败。
- `AUTO-022`～`AUTO-024`：deterministic fake AI 的 Web 8/8、Server 26/26、Chromium E2E 5/5。
- `AUTO-025`：浅色主题新增断言首次选中透明标题组件，属于测试定位错误。
- `AUTO-026`：修正定位后产生真实浅色 actual/diff，确认旧 fixture 主题令牌失效。
- `AUTO-027`：人工评审后仅更新 `light-player.png`。
- `AUTO-028`、`AUTO-029`：普通模式视觉复跑及 1280×800 浅色证据重采集通过。
- `AUTO-030`、`AUTO-031`：修改后的最终类型检查和完整 Chromium 16/16。
- `AUTO-032`、`AUTO-033`：修改后完整 Firefox/WebKit 最终复跑，仍各为 15/16；浅色播放通过，编辑器视觉断言失败。

日志中的 `deselect`、初始脚本失败、环境阻塞和未完成人工步骤均不计入通过。日志只包含本地 fixture、随机端口和测试标识；不得加入真实凭据、ticket、客户数据或生产连接信息。
