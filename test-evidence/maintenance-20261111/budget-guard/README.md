# 评测成本保护维护记录（2026-11-11）

## 范围与输入

- **有证据**：维护开工基线 `main@ed5ec70`，工作区干净，领先 `origin/main` 4 个提交。最终维护提交用 `git log -1` 与上级执行记录定位；未推送。
- **文档声明**：用户要求真实模型配置“先等等吧”；本轮仅补齐既有评测器保护、Plan 授权回归与现有 CI 静态门禁，没有发起真实供应商请求。
- **有证据**：项目环境标记均未配置，实际 `.env` 不存在；仅记录配置元数据，未保存密钥或配置值，见 `config-metadata.json`。
- **文档声明**：准备输入固定 `gpt-6-astra`、`golden-v1` 八 case、2026-11-11、USD 1.00、每次输出上限 512 tokens。供应商版本尚未提供，价格表为仓库配置（输入 $10/M、输出 $50/M），未声称已核实实时供应商价格。golden 文件哈希见上级 `README.md`。

## 修改与边界

- **有证据**：`tools/quality_baseline.py:192` 的现有 provider 在建立客户端前校验有限正数预算（最多 USD 1.00）、已配置价格和输出 token 范围（1–4096）。`tools/run_quality_baseline.py:29` 暴露预算与输出上限参数。
- **有证据**：请求包含 `max_tokens`；使用同一份 UTF-8 JSON 字节计算输入保留量并发送（`tools/quality_baseline.py:237`、`:326`）。每次请求前按“请求字节数 + 1,024 framing tokens”和输出上限保留最坏计价；剩余不足不发请求。最多八次，不重试。
- **有证据**：合法的非负整数 usage 替换保留量；timeout、HTTP 错误、缺失/非法 usage 保留本次预算并停止后续请求。报告 usage 超出输入/输出边界时保留实际计价并停止；这些停止后的 case 明确为 `AI_BUDGET_HALTED`。模型输出 JSON 无效但 usage 合法时仍计入已报告用量，并可在余额内继续后续 case（`:315`）。
- **有证据**：真实报告增加整体 `budget` 和逐 case `cost_audit`。`metrics.token_cost.usd` 是已报告成本加未知用量的保留量，`reported_cost_usd` 在用量不完整时为 null；未知账单不会伪记为零。预算/用量停止后写报告并退出 1；配置拒绝退出 2。fixture 报告格式与确定性结果保持不变（`:269`、`:591`；`tools/run_quality_baseline.py:61`）。
- **推断**：该成本保护的成立前提是 byte-based tokenizer、供应商额外 framing ≤1,024 tokens、遵守 `max_tokens`，且配置价格覆盖所有计费用量。任意兼容供应商的隐藏费用、未报告 token 或不遵守限制不能由本地代码保证硬限额；越界已计费部分只能记录并阻止后续请求。供应商账号货币限额可作为额外控制，不是执行本地工具的强制前提。
- **有证据**：同时修复 `PlanValidator` 未核对未被组件使用的顶层数据集声明；详情及授权边界见 `../plan-dataset-boundary/README.md`。

## 验证与原始失败

所有日志保留命令与退出码；没有使用 skip 参数掩盖失败。

三份含原始终端尾随空格的日志以 `.log.gz` 无损归档，用 `gzip -cd <路径>` 阅读。解压字节 SHA-256、压缩包 SHA-256、原命令退出码及往返一致性见 `raw-log-archives.json`；不修剪失败内容。归档前 `git diff --cached --check` 的退出 2 仅对应这些空格，原输出保留于 `diff-check-before-archive.json`；无损归档后退出 0，见 `diff-check-final.json`。归档包装首轮对 `EXIT_CODE` 大小写处理失败（退出 1），已修正并记录在归档清单；日志字节未改变。

| 验证 | 退出码 | 结果与证据 |
| --- | ---: | --- |
| 预算新增回归，修复前 | 1 | 20 failed、9 passed；`focused-red.log.gz` |
| 预算及 harness，首轮修复后 | 0 | 39 passed；`focused-green.log` |
| 预算及 harness，最终回归 | 0 | 44 passed，无跳过；`focused-final.log` |
| fixture CLI（USD 1.00 / 512 tokens） | 0 | 8/8、字段绑定 1.0、语义 1.0、平均 13.75 ms、fixture 计价 $0.03596；`fixture-cli.log`、`fixture.json` |
| real CLI 配置拒绝 | 2 | 缺 `base_url` / `api_key`，请求前拒绝，未创建 real 报告；`real-blocked.log` |
| 本轮三文件 Ruff 首轮 check / format | 1 / 1 | 原错误与逐步修复见 `ruff-check-initial.log`、`ruff-format-initial.log`、`ruff-check-focused.log` |
| 本轮三文件 Ruff 最终 check / format | 0 / 0 | `ruff-check-focused-final.log`、`ruff-format-focused-final.log` |
| 全仓 Ruff 首轮 check / format | 1 / 1 | 7 lint 项 / 45 格式文件；`ruff-check-all.log`、`ruff-format-all.log` |
| HEAD 原始归档 Ruff check / format | 1 / 1 | 证明全仓问题在本轮代码前已存在；`ruff-check-head.log`、`ruff-format-head.log` |
| Ruff 安全 fix | 1 | 6 项已修复，剩余长行交由格式化修复；`ruff-safe-fix.log` |
| Ruff 全仓格式化 | 0 | 仅导入/格式维护；`ruff-format-all-apply.log` |
| 全仓 Ruff 最终 check / format | 0 / 0 | `ruff-check-all-final.log`、`ruff-format-all-final.log`；327 文件格式通过 |
| `pnpm verify`（最终联合维护工作树） | 0 | SDK 20、Web 331、后端 1045 passed/15 deselected；类型、Vite build 通过；`../verify-budget-plan-final.log.gz` |

- **有证据**：安全 fix/格式化共改变 46 文件；除顶层 import 排序及删除未使用的 `Mapping` 外，全部文件 AST 不变，见 `ruff-ast-comparison.json`。未放宽 Ruff 配置。
- **有证据**：完整 `pnpm verify` 统一绑定在 `../verify-budget-plan-final.log.gz` 和上级执行记录；其源码哈希与文件列表见 `source-digests.json`。15 integration 项由项目既有命令 `-m "not integration"` 排除，没有新增 skip。定向回归及 CLI 只使用本地 fixture 或 MockTransport。

## 未完成与后续

- **文档声明**：真实模型评测按用户指令暂缓。恢复后先提供批准的专用凭据、可核对模型版本、价格与 token 限制，再使用固定 golden 哈希评测；不重复尝试账号配置。
- **推断**：本轮真实模型成功率、字段绑定、语义匹配、耗时和成本仍无测量值。此 runner 只是结构化绑定摘要，未覆盖完整 M1/M2 的 Plan、草稿、查询、渲染与多源场景；完整 M1/M2 保持未通过。
- **文档声明**：P4 无目标环境，八项目标门禁继续 BLOCKED，不执行。插件、连接器、模板拓展均为“建议，待确认，当前不实施”。未新增组件、协议、SDK 或跨项目运行时代码。
- **文档声明**：OPEN 索引应记录预算保护/Plan 边界维护及本轮真实门禁暂缓，不能写 M1/M2 或 P4 PASS。三项目只统一证据字段。
