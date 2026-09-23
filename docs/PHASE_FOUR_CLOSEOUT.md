# 第四阶段开发与本地验证交付记录

日期：2026-09-21。当前状态：**开发与本地验证完成，目标验收未完成**。八项目标环境门禁仍全部阻塞，第四阶段尚未完成。

用户已明确“尚未准备，先完成开发和本地验证”。本轮保留 `37a11b0` 上原有全部第三阶段未提交成果，在 `codex/phase-four-maturity` 开发；没有提交、推送或部署到目标环境。源文件清单、工作区差异标识、环境、命令及退出码见[证据索引](../test-evidence/phase-four/local-20260921/index.json)。

## 已交付范围

| 范围 | 实现与验收覆盖 | 使用说明 |
| --- | --- | --- |
| 身份与资源权限 | 追加 `0020_identity`；管理员、编辑者、只读用户；归属、read/write/publish 授权、审计、撤销、会话失效、最后管理员保护；旧账号升级；服务端列表和传递依赖校验 | [权限矩阵](operations/identity-permissions.md)、[资源共享](operations/resource-sharing.md) |
| 多人协作 | 真实双账号共享、revision 冲突与撤销；按有效权限进入预览或编辑，发布单独授权 | 三浏览器双账号用例通过；不提供实时共同编辑 |
| 离线市场 | 目录与详情、ZIP 安装、来源/许可证/哈希、不可变版本、兼容性校验、模板引用重映射、引用中的版本禁止卸载 | [生态操作手册](operations/ecosystem-plugins.md) |
| 组件插件 | 独立 SDK、可构建示例、属性与数据 Schema、编辑器配置、真实数据查询、发布/播放/Embed 精确依赖；草稿显式迁移、原子失败、撤销和降级；旧发布快照不变 | [SDK](../packages/plugin-sdk/README.md)、[示例](../examples/metric-plugin/README.md) |
| 备份恢复 | SQLite 离线维护 CLI：create/inspect/verify/restore；全生命周期维护锁、文件/模板/插件依赖校验、密钥分开保管、空目录分阶段恢复、凭据撤销、升级回滚手册 | [备份手册](operations/backup-restore.md)、[完整 CLI 恢复记录](operations/restore-rehearsal-local.md) |
| worker 与配额 | 追加 `0021_speech_leases`；数据库原子领取、持久租约/心跳、音频配额预留、终态比较更新、过期中断且不自动重播；实际子进程领取与被杀恢复回归 | [worker 手册](operations/speech-workers.md) |
| 运维与处理安全 | 结构化请求日志、脱敏、三条 Prometheus 规则；扫描器命令接入；受限解析/媒体子进程；共享处理槽、取消回收、Linux 内存限制；文件解析有界缓存与同请求合并 | [安全与容量](operations/security-capacity.md)、[本地验证工具](operations/local-validation.md) |

插件使用管理员安装的同源可信代码模型，不提供恶意代码沙箱。协作不包括组织树、行列权限、外部身份联邦；对话数字人、ASR 和多轮问答仍不在本轮范围。

## 验证结果

下列项目彼此有重叠，不将计数相加作为独立用例总数。

| 命令或验证 | 实际结果 | 证据 |
| --- | --- | --- |
| `pnpm verify` | 退出 0；Embed SDK 20、Web 281、后端 844 passed / 15 deselected；合同、类型、构建通过 | `verify-capacity-fixed.log` |
| 最后清理修复后的后端全量 | 退出 0；848 passed / 15 deselected | `server-final.log` |
| `pnpm test:integration` | 退出 0；真实 PostgreSQL/MariaDB 13 passed / 12 deselected | `integration.log` |
| `pnpm test:e2e` | 退出 0；Chromium 26 passed | `e2e-chromium-final.log` |
| `pnpm test:e2e:cross-browser` | 退出 0；Firefox 26、WebKit 26 passed；各浏览器独立数据库 | `e2e-cross-final.log` |
| 缓存修改后的文件数据集浏览器复验 | 退出 0；三浏览器各 2 项，共 6 passed | `e2e-file-capacity-final.log` |
| 最后取消清理回归 | 退出 0；解析、扫描、实际查询等 27 passed | `processing-cancellation-final.log` |
| Linux 解析/扫描/媒体 | 退出 0；86 passed，使用缓存运行镜像挂载当时源码 | `linux-processing-followup-final.log` |
| CLI 完整恢复与两次启动 | 通过；2 账号、2 数据集、3 媒体、1 插件、1 发布大屏；数字人肖像/WAV、SQL/CSV、权限、编辑发布、player/Embed 和撤销均验证 | `restore-rehearsal-digital-human.json` |
| 最终镜像构建 | 退出 0；使用受控替代构建镜像，运行层 Python 3.13 | `docker-build-release-local.log` |
| 最终容器 50 客户端、恢复及重启 | 退出 0；250/250 查询成功、p95 590 ms；真实 CLI 恢复 2.038 秒，重启后验证通过 | `container-final/result.json` |
| 告警规则 | `promtool` 退出 0，3 条规则语法通过；接收器未验收 | `prometheus-rules.log` |

最终镜像 ID 为 `sha256:31a7e97e411e89d35f7cb36d96ca6f7606b1d504e80b1de72a9954f91fb6cd6f`；镜像内 146 个后端源码/迁移文件与工作区逐一匹配。

本地环境为 macOS arm64、Node 22.23.1、pnpm 10.33.0、Python 3.13.13；浏览器版本 Chromium 151.0.7922.34、Firefox 153.0、WebKit 26.5。Docker 运行层为 Linux arm64/Python 3.13.15。Docker 构建使用已缓存的 `mcr.microsoft.com/playwright:v1.62.0-noble`（Node 24.18.0）；默认 `node:22-slim` 下载未完成，不计为默认构建镜像通过。本机 Node 22 的 Web 构建已通过。

完整 CLI 恢复 fixture 为 11 个归档成员、300,683 字节，记录恢复耗时 1.037 秒；这是小规模临时数据的实测值。容器演练固定 2 核、4 GiB、256 PID，50 个独立显示 Session 各做 5 次两行 CSV 查询，预先规定 p95 ≤ 3,000 ms、全部成功且数据正确。最终镜像实测 250/250 成功、p95 590 ms（最大 701.77 ms）；整个恢复/重启演练再次通过，4 成员容器归档恢复耗时 2.038 秒。它衡量本地 HTTP 查询，不代表浏览器首屏、生产规模或 8 小时稳定性。容器测试显式采用 test 模式和 loopback HTTP；生产 TLS、Secure Cookie 和完整代理链保留目标验收。

## 失败与修复记录

- 集成时修复了权限字段/测试 fixture、SQLite 路径提权边界、文件预览删除竞态、扫描取消泄漏、Linux Arrow 分配器虚拟内存过大、插件 CSP 不兼容、安装引用锁及未解析 Schema 引用。
- 首轮 Chromium 为 24 passed / 2 failed；首轮跨浏览器为 38 passed / 14 failed。保留失败日志。新增导航和数字人组件导致的截图差异经人工核对后更新；不同浏览器共享数据库导致的名称冲突由运行器隔离修复。Firefox 首例未在等待窗口内加载，后续串行复跑通过。
- 独立审查的两项备份 P2 已修复并复审：删除媒体后终态语音缓存引用仅在备份快照中清理；模板文档和精确插件依赖纳入校验。
- 容器首次因 HTTP 不发送生产 Secure Cookie 返回 401，明确测试模式后重跑；随后 50 并发重复解析超过处理槽而返回 500，加入有界解析缓存与共享解析，保持原资源与性能阈值后通过。
- 重复取消可能中断子进程回收的问题已通过真实子进程复现并修复；扫描器同类路径亦修复。最后等待者取消会等待启动与回收完成，不遗留子进程。
- 镜像下载中断和依赖超时没有计为成功；构建重试复用缓存，最终构建通过。构建仍输出现有的大 chunk、第三方注释和混合动态导入提示，未将其隐藏。

失败、红灯测试、取消和成功证据均保留。可能包含临时 Session/Ticket 的 18 份原始 Playwright trace 已移除，保留脱敏错误上下文、截图及删除哈希记录，见 `redaction.json`；一次性初始化代码和日志中的凭据已脱敏。

## 八项目标门禁

以下全部是**阻塞，0 项通过**。本地 fixture、截图、容器和 fake TTS 均不关闭这些门禁。

| 编号 | 缺少的执行条件 |
| --- | --- |
| P4-ENV-001 | 组织实际浏览器/密码管理器组合及专用配置 |
| P4-ENV-002 | 实际 LB/WAF/CDN/代理链、TLS、缓存与日志策略 |
| P4-ENV-003 | 物理 4K/高 DPI 设备及现场显示验证 |
| P4-ENV-004 | 目标浏览器/代理/kiosk 的连续 28,800 秒窗口和每分钟资源证据 |
| P4-DH-001 | 专用真实 TTS 账号、供应商网络/故障与语言矩阵 |
| P4-DH-002 | 真实跨域媒体、用户手势、屏幕阅读器和目标播放矩阵 |
| P4-DH-003 | 目标首帧/字幕/音频基线、8 小时数字人长播和跨主机调度 |
| P4-DH-004 | 生产告警接收、实际扫描器及签名库、隔离策略、重启和容量治理证据 |

关闭条件和执行步骤继续沿用[目标环境手册](PHASE_FOUR_TARGET_ENVIRONMENT.md)，DP-005 与 ISS-022 保持打开。自动备份仅支持已说明的离线 SQLite 拓扑；PostgreSQL 原生恢复、实际扫描器、安全容器/网络隔离以及跨主机 worker 均需按部署手册单独验收。只有八项门禁也关闭后，才能声明第四阶段完成。
