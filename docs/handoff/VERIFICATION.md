# 交接验证记录

## 2026-11-11 维护复验（main 基线）

- 开工核对：`main@63d74c7`，工作区干净，`origin/main..main` 为空。
- `pnpm verify:no-ai`：退出码 0；AI 未加载、路由隐藏、健康/认证/数据集/大屏路由通过。
- `pnpm verify:upgrade-rollback`：退出码 0；9 项通过。
- `pnpm demo:verify`：退出码 0；数据集画像、静态语音降级、发布/播放/Embed 和权限拒绝通过。
- `pnpm test:integration`：退出码 0；1 项通过，12 项因未配置 `DATAPULSE_TEST_MYSQL_URL`/`DATAPULSE_TEST_POSTGRES_URL` 跳过，12 项 deselected。
- `pnpm test:e2e`：退出码 0；Chromium 28 项通过。文件数据集 E2E 的保存按钮改为精确定位；组件注册表扩展后的 Darwin 视觉基线已复核并更新。
- 提交前 `pnpm verify`：退出码 0；后端 1016 passed、15 deselected，类型检查和 Web 构建通过。
- 证据：`test-evidence/maintenance-20261111/`（命令日志、环境、跳过原因和 E2E 输出）。真实模型 M1/M2、真实数据库连接和八项目标环境门禁未执行。

## 2026-11-10 复跑（main 合并后）

- 代码：`main` / `dbfaf42`（2026-10-31 提交，2026-11-10 快进合并 `codex/batches-10-16` 后复跑）。
- 命令：仓库根 `pnpm verify`（contracts → test → typecheck → build）。
- 结果：**退出码 0**。SDK 20 passed；Web 53 文件 / 331 passed；后端 `1016 passed, 15 deselected in 251.12s`；前端 build 8.22s 通过（仅 chunk 体积告警）。
- 证据：`test-evidence/verify-20261110/env.txt`（提交、环境版本与命令）与 `verify.log`（完整输出与退出码）。
- 未覆盖：`test:integration`（15 项按配置 deselect）、浏览器 E2E、无 AI 部署、真实模型质量门禁、四阶段目标环境门禁。
- 结论：批次 10–16 的 verify 声明由此获得归档证据，`test-evidence/` 不再停留在 2026-09-23；M1/M2 真实模型门禁与 P4 环境门禁仍未完成。

## 2026-10-31 复查

交接记录的 4 个失败已修复，`pnpm verify` 退出码 0：SDK 20、Web 331、后端 1016 通过，15 个 integration 用例按配置 deselect。

- 文件查询路径补齐 `field_expressions`、固定指标和聚合表达式，与 SQL 路径共用语义层。
- 质量升级门禁拒绝非 1 的 `schema_version` 和缺失的 `fixture` 元数据。
- 文档编译快照补入组件 `contract_version`。

以下 2026-09-29 记录保留为历史证据。

执行日期：2026-09-29，Asia/Shanghai。代码快照：`a70f8d5` 加当前 `codex/batches-10-16` 工作树。
本次为交接核实运行现有定向回归；未修改产品代码，也未运行全量 `pnpm verify`、Docker、数据库集成或浏览器 E2E。

## 2026-09-29 当前工作区定向复现（历史）

仓库根目录执行：

```bash
uv run --package datapulse-server pytest \
  apps/server/tests/filedata/test_duckdb_executor.py::test_query_service_compiles_parameterized_query \
  apps/server/tests/filedata/test_duckdb_executor.py::test_file_query_executes_calculated_fields_and_fixed_metrics \
  apps/server/tests/filedata/test_duckdb_executor.py::test_file_compiler_supports_the_same_time_grain_contract \
  apps/server/tests/quality/test_quality_harness.py::test_upgrade_gate_blocks_unsupported_schema_and_missing_fixture \
  -q
```

实际结果：**退出码 1，4 failed in 3.35s**。这四项是确认的当前失败，不是从旧会话推断。

| 回归 | 实际错误 | 负责模块 |
| --- | --- | --- |
| `test_query_service_compiles_parameterized_query` | `_FilterCompiler.__init__()` 缺少必需 `field_expressions` | `apps/server/src/datapulse/filedata/query.py:70` |
| `test_file_query_executes_calculated_fields_and_fixed_metrics` | 固定指标 `total_profit` 被当作未知字段，抛 `CHART_FIELD_UNKNOWN` | `apps/server/src/datapulse/filedata/query.py:64` |
| `test_file_compiler_supports_the_same_time_grain_contract` | `_FilterCompiler.__init__()` 缺少必需 `field_expressions` | `apps/server/src/datapulse/filedata/query.py:70` |
| `test_upgrade_gate_blocks_unsupported_schema_and_missing_fixture` | 预期 `allowed=False`，实际 `True` | `tools/quality_harness.py`，断言在 `apps/server/tests/quality/test_quality_harness.py:178` |

测试使用临时目录中的 fixture，不读写现有 `data/` 实例。

## 根因范围与接手检查

文件查询的共享 helper 已随语义层升级，但 `FileQueryCompiler` 尚未完成适配：

- `screen/chart_query.py` 的 `_FilterCompiler`、`_dimension_expressions` 都要求 `field_expressions`，文件路径两个调用都未传。
- `_aggregate` 已要求 `(aggregation, expression)`，文件路径选择和排序仍传单个 `measure`；先修构造参数后还需覆盖这两个调用。
- 文件路径的已知字段仅含物理字段，未纳入 `calculated_fields` / `metrics`。需要保证字段校验、表达式、聚合、筛选、排序、时间粒度和下钻在文件路径一起成立。

质量门禁的 `_comparability_issues` 只比较双方值是否相等，未验证各自报告是否为受支持版本：

- 双方都 `schema_version=2` 且均缺少 `run.fixture` 时，`2 == 2`、`None == None`，报告仍被放行。
- 已有回归要求拒绝并提供四条不支持原因。修复需要验证基线和候选各自的版本及 fixture 元数据，不能只验证相互相等。

以上是下一位 agent 的已确认修复起点。本次交接没有将其修复，也不能据此断言剩余用例全部通过。

## 历史结果的适用范围

- 2026-09-21 第四阶段本地交付曾通过后端 848、Web 281、SDK 20；三浏览器完整 E2E 各 26。详见 `../PHASE_FOUR_CLOSEOUT.md`，它记录当时环境与源码。
- 2026-09-23 最新主会话曾有完整 `pnpm verify` 退出 0，包含 SDK 20、Web 329、后端 1007。随后审查新增回归，19:21 的定向结果为文件查询 3 failed / 5 passed、质量工具 1 failed / 9 passed；没有审查后的完整通过结果。
- 同一天更早存在被中断的 `pnpm verify`（`exit=-1`），随后又有完整通过轮。不能把中断轮或审查前通过轮当作最终收尾结论。
- `test-evidence/quality-baseline/*fixture*` 与 2026-09-22 baseline 是确定性演练，不能证明真实模型质量、真实延迟/成本或 M1/M2/M3 指标通过。
- 真实生产的八项目标门禁仍阻塞，见 `../PHASE_FOUR_TARGET_ENVIRONMENT.md`。

## 文档检查

交付前检查交接文件的本地链接、文件清单计数、会话索引覆盖和新增文件的差异格式。
最终检查结果记录在交接总览的“本次整理结果”中。该文档检查不等同产品测试通过。
