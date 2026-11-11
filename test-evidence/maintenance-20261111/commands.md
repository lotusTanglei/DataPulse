# DataPulse 2026-11-11 maintenance evidence

历史开工核对：`main@63d74c7`，工作区干净，`origin/main..main` 为空。当前实际复核：`main@7464c4e`，工作区干净，`origin/main..main` 有 1 个提交。

| 命令 | 结果 | 记录 |
| --- | --- | --- |
| `pnpm verify:no-ai` | 退出码 0 | `no-ai.log`；AI 未加载、路由隐藏、健康/认证/数据集/大屏路由通过 |
| `pnpm verify:upgrade-rollback` | 退出码 0 | `upgrade-rollback.log`；9 passed |
| `pnpm demo:verify` | 退出码 0 | `demo-verify.log`；交付闭环与静态语音降级通过 |
| `pnpm test:integration` | 退出码 0 | `integration.log` / `integration-reasons.log`；1 passed，12 skipped，12 deselected；跳过原因是 MySQL/PostgreSQL URL 未配置 |
| `pnpm test:e2e` | 退出码 0 | `e2e.log`；Chromium 28 passed；日志已移除初始化码 |
| `pnpm verify` | 退出码 0 | `verify.log`；后端 1016 passed、15 deselected，类型检查与 Web 构建通过 |

当前复核补充：

| 命令 | 结果 | 记录 |
| --- | --- | --- |
| `pnpm verify`（当前工作树复跑） | 退出码 0 | `verify-current-rerun.log`；SDK 20、Web 331、后端 1016 通过，15 deselected，类型检查和构建通过 |
| `pnpm quality:baseline -- --provider fixture --model gpt-6-astra --date 2026-11-11` | 退出码 0 | `quality-fixture-20261111.json`；8/8 fixture 成功，仅证明工具可用 |
| `pnpm quality:baseline -- --provider openai --model gpt-6-astra --date 2026-11-11` | 退出码 2 | `quality-real-blocked.log`；缺少 `DATAPULSE_AI_BASE_URL`/`DATAPULSE_AI_API_KEY`，真实 M1/M2 BLOCKED |

E2E 修复：文件数据集保存按钮改为精确名称匹配；组件注册表扩展后复核并更新 Darwin `compiled-template-editor.png` 与 `editor-shell.png` 快照。真实模型 M1/M2、真实数据库和目标环境门禁未执行。

## 预算、Plan 与 CI 维护（最终工作树）

**有证据**：维护开工 `main@ed5ec70`，工作区干净，领先远端 4 个提交。最终源码清单/哈希在 `budget-guard/source-digests.json`；本轮 commit 用 `git log -1` 定位，未推送。

原始 `.log.gz` 用 `gzip -cd <路径>` 阅读；无损校验与解压后 SHA-256 见 `budget-guard/raw-log-archives.json`。

| 命令 | 结果 | 记录 |
| --- | --- | --- |
| `uv run --package datapulse-server pytest apps/server/tests/quality/test_quality_baseline.py apps/server/tests/quality/test_quality_harness.py -q` | 退出码 0；44 passed，无跳过 | `budget-guard/focused-final.log`；红灯 20 failed/9 passed 仍保留 |
| `uv run --package datapulse-server pytest apps/server/tests/screen/test_plan_validator.py apps/server/tests/ai/test_plan_generator.py apps/server/tests/screen/test_document_compiler.py apps/server/tests/screen/test_planning_service.py -q` | 退出码 0；35 passed，无跳过 | `plan-dataset-boundary/focused-green.log`；红灯 4 failed/14 passed 仍保留 |
| `uv run --package datapulse-server ruff check apps/server tools` | 最终退出码 0 | `budget-guard/ruff-check-all-final.log`；首轮及 HEAD 7 项失败仍保留 |
| `uv run --package datapulse-server ruff format --check apps/server tools` | 最终退出码 0；327 文件 | `budget-guard/ruff-format-all-final.log`；首轮及 HEAD 45 格式文件失败仍保留 |
| `pnpm verify` | 退出码 0；SDK 20、Web 331、后端 1045 passed/15 deselected；类型与构建通过 | `verify-budget-plan-final.log.gz` |
| fixture / real CLI，固定 USD 1.00、512 输出 tokens | 退出码 0 / 2；fixture 演练通过，real 缺凭据在请求前拒绝 | `budget-guard/cli-commands.json` 与对应日志 |

**文档声明**：用户要求真实模型配置“先等等吧”，真实模型评测暂缓；P4 缺环境仍 BLOCKED。没有新增 skip 参数，没有执行额外外部数据库/浏览器门禁，没有新增计划外功能；插件、连接器和模板为“建议，待确认，当前不实施”。三项目仅统一证据字段，不共享运行时代码。
