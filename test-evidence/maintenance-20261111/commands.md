# DataPulse 2026-11-11 maintenance evidence

开工核对：`main@63d74c7`，工作区干净，`origin/main..main` 为空。

| 命令 | 结果 | 记录 |
| --- | --- | --- |
| `pnpm verify:no-ai` | 退出码 0 | `no-ai.log`；AI 未加载、路由隐藏、健康/认证/数据集/大屏路由通过 |
| `pnpm verify:upgrade-rollback` | 退出码 0 | `upgrade-rollback.log`；9 passed |
| `pnpm demo:verify` | 退出码 0 | `demo-verify.log`；交付闭环与静态语音降级通过 |
| `pnpm test:integration` | 退出码 0 | `integration.log` / `integration-reasons.log`；1 passed，12 skipped，12 deselected；跳过原因是 MySQL/PostgreSQL URL 未配置 |
| `pnpm test:e2e` | 退出码 0 | `e2e.log`；Chromium 28 passed；日志已移除初始化码 |
| `pnpm verify` | 退出码 0 | `verify.log`；后端 1016 passed、15 deselected，类型检查与 Web 构建通过 |

E2E 修复：文件数据集保存按钮改为精确名称匹配；组件注册表扩展后复核并更新 Darwin `compiled-template-editor.png` 与 `editor-shell.png` 快照。真实模型 M1/M2、真实数据库和目标环境门禁未执行。
