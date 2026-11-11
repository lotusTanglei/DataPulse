# DataPulse 维护执行记录（2026-11-11）

时区：Asia/Shanghai。执行仓库：`/Users/dundundebaba/sync/code/open/DataPulse`。

## 基线与范围

- **有证据**：开工执行 `git status --short --branch`、`git log -1 --oneline` 和 `git log --oneline origin/main..main`；基线为 `main@7464c4e`，工作区干净，本地领先 `origin/main` 1 个提交。
- **有证据**：本次没有修改应用代码、组件、Plugin SDK、Embed SDK 或协议；只补充维护验证证据和交接记录。
- **有证据**：维护提交 `19c7708` 归档当前验证与模型阻塞，`b31ec0c` 区分预算、实际支出和完整产品门禁边界；变更仅在 `docs/handoff/` 与本目录。后续文档补记的提交用 `git log --oneline -- docs/handoff test-evidence/maintenance-20261111` 定位。
- **文档声明**：`docs/PHASE_FOUR_TARGET_ENVIRONMENT.md` 把八个 P4 目标环境门禁列为阻塞条件。
- **推断**：在真实模型账号和目标环境缺失时，本轮可以完成可复跑验证与阻塞记录，但不能宣称 M1/M2 或 P4 通过。

## M1/M2 评测固定输入

- 模型：`gpt-6-astra`。仓库只配置了模型名与价格表，没有可核对的供应商版本号；版本字段因此记录为“供应商未提供”。
- 数据集：`fixtures/golden/manifest.json`，版本 `golden-v1`，8 个 case（经营、运营、销售、设备各 2 个）。
- 数据集哈希（SHA-256）：

  ```text
  3eba6664e837da35ac51a289cc650655cd435cd1a332f75d5397b2d27053d543  fixtures/golden/manifest.json
  db0d0ba9190f2d07002ea324a2802ff5d3d1a2ebd7f53b4044f06b28e7e022e8  fixtures/golden/business/data.csv
  d1d52ba8ce61ab544ceb053c40e77091d014a97d8c821c71011ef9656f3ac3f3  fixtures/golden/operations/data.csv
  4251ff6997fb21955e4184e9e34f42d579d576882da7f984569291e89c0d11bc  fixtures/golden/sales/data.csv
  5c95c09349063c2961ea0677e080324e337c27a453028a7eccb7e92ec3c45303  fixtures/golden/equipment/data.csv
  ```

- 准备计划的成本上限：**每次完整八 case 真实评测不超过 USD 1.00**；本轮只记录计划，不发出请求。实际支出为 USD 0.00，因为凭据缺失；实际支出与预算上限是两个字段。
- **有证据**：当前运行器没有成本硬限额参数，请求也没有 `max_tokens`（`tools/quality_baseline.py:207`）；仓库价格表按输入 $10/M、输出 $50/M 计算成本（`tools/quality_baseline.py:16`），不能代替供应商账单或硬限额。解除 BLOCKED 前，必须在专用供应商账号设置并核对 **不高于 USD 1.00 的硬限额**，确认可核对的模型版本；供应商不支持该硬限额时继续阻塞。本轮不新增协议或运行时实现。
- 评测日期：`2026-11-11`。

## 命令与结果

| 命令 | 退出码 | 结果 | 证据 |
| --- | ---: | --- | --- |
| `pnpm verify` | 0 | 通过：contracts；SDK 20 tests；Web 53 files/331 tests；后端 1016 passed、15 deselected；类型检查；Vite build | `verify-current-rerun.log` |
| `pnpm quality:baseline -- --provider fixture --model gpt-6-astra --date 2026-11-11 ...` | 0 | fixture 演练 8/8 成功，字段绑定 1.0，语义 1.0，平均耗时 13.75 ms，计算成本 $0.03596 | `quality-fixture-20261111.json`、`quality-fixture.log` |
| `pnpm quality:baseline -- --provider openai --model gpt-6-astra --date 2026-11-11 ...` | 2 | **BLOCKED**：缺少 `DATAPULSE_AI_BASE_URL` 和 `DATAPULSE_AI_API_KEY`；没有跳过或伪造真实结果 | `quality-real-blocked.log` |

fixture 报告只证明 harness 能运行；它不证明真实模型的 M1/M2 成功率、字段绑定、语义匹配、耗时或成本。

**文档声明（执行代理报告）**：首次验证的外层 zsh 包装命令将退出码写入只读变量 `status`，包装命令退出 1；原 `verify-current.log` 未写入最终退出码且已删除，未保留原始证据。因此不把首轮记为可核验的 PASS，也不据此推断产品失败。随后改用 `rc` 变量完整重跑；本记录唯一可核验的当前门禁是 `verify-current-rerun.log` 中的 `pnpm verify` 退出 0。保留这一证据缺口，不能把包装错误隐去或冒充项目门禁失败已修复。

## M1/M2 阈值与评测器边界

- **文档声明**：M1 阈值为首次成功率 ≥90%、失败时 100% 仍产出可编辑草稿、CSV 数值/日期识别 ≥95%、字段绑定准确率 ≥85%、可生成 ≥25 组件大屏、一键复跑可用（`docs/superpowers/plans/开发顺序.md:110`）。
- **文档声明**：M2 阈值为空图表/重叠/越界均为 0、首次可用率 ≥95%、平均修改 ≤2、语义匹配 ≥95%、同 Plan 编译可复现、3 个多源大屏场景跑通、组件第一批完成并进入模板（`docs/superpowers/plans/开发顺序.md:169`）。
- **有证据**：`OpenAICompatibleProvider` 只向模型发送字段和最多 5 行样例，并要求返回 `success`、`bindings`、`chart_type`、`warning_count`、`error_code`、`draft_produced` 的结构化绑定摘要（`tools/quality_baseline.py:207`）。它没有调用产品完整的 Plan 生成、编译、草稿持久化、查询或浏览器渲染链路；其中 `success` 和 `draft_produced` 是模型返回字段。
- **推断**：即使 real baseline 有结果，也只能作为该摘要任务的真实模型成功率、字段绑定、语义代理指标、耗时和计价证据。它不能单独证明 M1 可编辑失败草稿、CSV 识别、≥25 组件，以及 M2 空图/重叠/越界、首次产品可用率、人工修改次数、Plan 确定编译、真实数据库 + Excel + HTTP API 的 3 个多源场景或组件进入模板；这些仍需各自现有产品流程和验收证据。完整 M1/M2 当前均未通过。

## 未完成项与解除条件

1. **M1/M2 真实模型门禁：阻塞。** 解除条件：提供批准的 OpenAI-compatible `DATAPULSE_AI_BASE_URL`、专用 `DATAPULSE_AI_API_KEY`、可核对的模型版本，并核验专用供应商账号已配置不高于 USD 1.00 的硬限额；随后使用同一 golden 哈希运行 real baseline，并补齐上述摘要运行器未覆盖的现有产品流程验收证据。不能仅凭 real baseline 关闭完整 M1/M2。
2. **P4 八项目标环境：阻塞。** 解除条件见 `docs/PHASE_FOUR_TARGET_ENVIRONMENT.md`：真实密码管理器、生产代理链、物理 4K、连续 8 小时播放、真实 TTS/媒体/运维证据。
3. **插件、连接器、模板扩展：建议，待确认，当前不实施。** 本轮未新增目录、运行时加载或协议。

## 结论标注

- **有证据**：以上命令、退出码和日志均在本目录；当前 HEAD 可由 `git log -1 --oneline` 复核。
- **有证据**：本次补充仅修改文档，复用同目录 `verify-current-rerun.log` 中 `pnpm verify` 退出码 0 的门禁结果；应用代码未变。
- **文档声明**：仓库交接和 P4 文档声明真实模型及目标环境不能由 fixture、本地预检或短时运行关闭。
- **推断**：在解除条件满足前，DataPulse 只能标记“验证工具可用、真实门禁阻塞”，不能把历史 fixture 结果当作交付门禁通过。
