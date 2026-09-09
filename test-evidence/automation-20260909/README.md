# 2026-09-09 第二阶段自动化证据索引

最终代码基线为本地提交 `08adadb`，未推送。最终门禁在 detached 临时 worktree 中运行，未包含工作区并发出现的第三阶段数字人改动。

2026-09-09 阶段范围调整：经用户确认，真实密码管理器、目标生产代理链、物理 4K 和连续 8 小时播放验收转入第四阶段。第二阶段 8 组功能和下列最终门禁已通过，现标记为完成；四项仍按第四阶段阻塞统计，没有新增目标环境通过结果。关闭步骤见 `docs/PHASE_FOUR_TARGET_ENVIRONMENT.md`，结论见 `docs/PHASE_TWO_CLOSEOUT.md`。

## 最终门禁

| 日志 | 结果 |
| --- | --- |
| `AUTO-035-final-check-contracts.log` | `pnpm check:contracts` 通过 |
| `AUTO-036-final-test.log` | Embed SDK 5/5、Web 142/142、Server 448/448；13 个 integration 项 deselect，不计通过 |
| `AUTO-037-final-typecheck.log` | Web、schema、Embed SDK 类型检查通过 |
| `AUTO-038-final-build.log` | 构建通过；保留大 chunk 警告 |
| `AUTO-039-final-chromium-e2e.log` | Chromium 16/16 |
| `AUTO-040-final-firefox-e2e.log` | Firefox 16/16 |
| `AUTO-041-final-webkit-e2e.log` | WebKit 16/16 |
| `AUTO-042`～`AUTO-044` | PostgreSQL/MariaDB 13/13；12 个非 integration 项 deselect；专用容器、网络已清理 |
| `AUTO-045`～`AUTO-047` | 记录最终 HEAD、隔离 worktree 洁净状态并恢复主工作区 Python editable 环境 |

## 目标预检与发现

- `AUTO-019-proxy-equivalent-isolated.log` 是最终生产等价代理预检；`AUTO-011`～`AUTO-018` 保留发现可信代理和隔离构建问题的失败/诊断过程，不计通过。
- `AUTO-026-playback-soak-10m.log` 因 favicon 404 失败；修复后的 `AUTO-029` 60 秒和 `AUTO-030` 10 分钟均通过。
- `AUTO-031` 的自动断言虽为 2/2，但前置归档路径错误且人工查看发现 Canvas 未到终态，不计通过；`AUTO-032` 是最终 2/2 和人工评审采用的显示日志。
- `AUTO-033-final-check-contracts.log` 因 `git archive` 隔离目录没有 Git 元数据而失败，未执行到契约比较；`AUTO-035` 在 detached worktree 中才是有效最终结果。
- `AUTO-028-accidental-worktree-aborted.log` 在测试主体刚开始时中止，计未执行，不计通过。

历史失败和诊断日志均保留。最终通过不能抹去先前失败；skip、deselect、环境阻塞和未完成的人工步骤没有计入通过。

阶段范围调整的文档检查记录见 `AUTO-048-phase-scope-docs.log`：空白、手册引用、四项阻塞状态及暂存范围检查通过；本次仅修改文档，未重跑应用测试。

临时资源最终核对见 `resource-audit.md`。
