# DataPulse 维护执行记录（2026-11-11）

时区：Asia/Shanghai。执行仓库：`/Users/dundundebaba/sync/code/open/DataPulse`。

## 基线与范围

- **有证据**：开工执行 `git status --short --branch`、`git log -1 --oneline` 和 `git log --oneline origin/main..main`；基线为 `main@7464c4e`，工作区干净，本地领先 `origin/main` 1 个提交。
- **有证据**：本次没有修改应用代码、组件、Plugin SDK、Embed SDK 或协议；只补充维护验证证据和交接记录。
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

- 成本上限：本轮真实请求成本固定为 **$0.00 USD**，因为凭据缺失而没有发出供应商请求；运行器对 `gpt-6-astra` 的计价为输入 $10/M、输出 $50/M。**真实 M1/M2 的批准预算上限尚未配置，不能以 fixture 成本代替。**
- 评测日期：`2026-11-11`。

## 命令与结果

| 命令 | 退出码 | 结果 | 证据 |
| --- | ---: | --- | --- |
| `pnpm verify` | 0 | 通过：contracts；SDK 20 tests；Web 53 files/331 tests；后端 1016 passed、15 deselected；类型检查；Vite build | `verify-current-rerun.log` |
| `pnpm quality:baseline -- --provider fixture --model gpt-6-astra --date 2026-11-11 ...` | 0 | fixture 演练 8/8 成功，字段绑定 1.0，语义 1.0，平均耗时 13.75 ms，计算成本 $0.03596 | `quality-fixture-20261111.json`、`quality-fixture.log` |
| `pnpm quality:baseline -- --provider openai --model gpt-6-astra --date 2026-11-11 ...` | 2 | **BLOCKED**：缺少 `DATAPULSE_AI_BASE_URL` 和 `DATAPULSE_AI_API_KEY`；没有跳过或伪造真实结果 | `quality-real-blocked.log` |

fixture 报告只证明 harness 能运行；它不证明真实模型的 M1/M2 成功率、字段绑定、语义匹配、耗时或成本。

## 未完成项与解除条件

1. **M1/M2 真实模型门禁：阻塞。** 解除条件：提供批准的 OpenAI-compatible `DATAPULSE_AI_BASE_URL`、专用 `DATAPULSE_AI_API_KEY`、可核对的模型版本和明确 USD 成本上限；随后使用同一 golden 哈希运行 real baseline，并按 M1/M2 阈值归档报告。
2. **P4 八项目标环境：阻塞。** 解除条件见 `docs/PHASE_FOUR_TARGET_ENVIRONMENT.md`：真实密码管理器、生产代理链、物理 4K、连续 8 小时播放、真实 TTS/媒体/运维证据。
3. **插件、连接器、模板扩展：建议，待确认，当前不实施。** 本轮未新增目录、运行时加载或协议。

## 结论标注

- **有证据**：以上命令、退出码和日志均在本目录；当前 HEAD 可由 `git log -1 --oneline` 复核。
- **文档声明**：仓库交接和 P4 文档声明真实模型及目标环境不能由 fixture、本地预检或短时运行关闭。
- **推断**：在解除条件满足前，DataPulse 只能标记“验证工具可用、真实门禁阻塞”，不能把历史 fixture 结果当作交付门禁通过。
