# 项目文件与文档清单

快照日期：2026-09-29，生成于交接文档新增之前。仓库：`/Users/dundundebaba/sync/code/open/DataPulse`。
`HEAD`：`a70f8d506d015dff85b353142658036cb9aacb21`；分支：`codex/batches-10-16`。

## 文件范围

[FILES.tsv](FILES.tsv) 完整列出快照时 Git 跟踪或未忽略的 **1,432 个文件**，包含路径、Git 状态和磁盘字节数。
其中已有跟踪文件修改 **78 个**、未跟踪文件 **65 个**；暂存修改 **0 个**。
`M` 为相对 HEAD 的修改，`??` 为未跟踪，`tracked-clean` 为 Git 跟踪且无修改。
本次新增的交接文件不在这份先于新增操作生成的快照中。
这是一份可追溯目录，文件内容仍保存在原路径。

| 类别 | 文件数 | 维护用途 |
| --- | ---: | --- |
| `apps/` | 545 | 后端、前端、数据库迁移、单元测试与浏览器测试 |
| `packages/` | 99 | Schema 生成物、Embed SDK、Plugin SDK |
| `docs/` | 51 | 需求、设计、计划、运维与案例 |
| `test-evidence/` | 674 | 历史日志、截图、诊断与验收证据 |
| `tools/` | 16 | 合同生成、测试运行器、质量评测和交付验证 |
| `fixtures/` | 8 | Golden 数据、失败样本、案例清单和部署样例 |
| `examples/` | 6 | 可构建的可信插件示例 |
| `deploy/` | 3 | Nginx 与 Prometheus 配置 |
| `.github/` | 2 | CI 和 PR 模板 |
| 根目录配置/文档及本地元数据 | 28 | README、测试计划、锁文件、Compose、CodeGraph 和 IDE 元数据 |

## 未纳入逐文件清单的本地内容

以下目录/文件受 Git 忽略，仍留在原机器。维护迁移时需要按用途处理：

| 位置 | 本次观察 | 处理方式 |
| --- | --- | --- |
| `data/` | 144 KiB 的本地运行数据 | 按备份恢复手册保护数据，不能靠 Git 搬迁运行实例 |
| `.secrets/` | 当前目录为空 | 密钥独立保管；文档不导出凭据 |
| `.env`、`.env.demo`（存在时） | 本次未读取 | 不能提交或复制到交接文档；凭据从授权渠道配置 |
| `.e2e/` | 4 KiB 的本地测试目录 | 临时测试环境，按运行器重新生成 |
| `.codegraph/codegraph.db` | 索引目录共约 14 MiB | 本机索引；优先查询，索引未覆盖时核对磁盘代码 |
| `.idea/workspace.xml`、`.DS_Store` | IDE/系统文件 | 本地元数据，无产品功能含义 |
| `.venv/`、各级 `node_modules/` | 本地依赖 | 使用锁文件重新安装 |
| `apps/web/dist/`、`examples/metric-plugin/dist/` | 构建产物 | 从源码重新构建 |
| `apps/web/test-results/` | 测试产物 | 原始 trace 可能包含临时凭据，外发前脱敏 |
| `__pycache__/`、`.pytest_cache/`、`.ruff_cache/` | 缓存 | 不作为工程输入 |
| `s/` | 当前为空 | 无需作为维护输入 |
| `.git/` | 本地历史、分支、配置 | 使用 Git 迁移；不要把整个内部目录放入会话上下文 |

## 全部 Markdown 文档

快照共 **91 份 Markdown 文档**。下面按原文件列出，不改动历史文件状态。
标题是当时正文的一级标题；维护决策的优先顺序见 [交接总览](README.md)。

| 文档 | 原标题 |
| --- | --- |
| [.github/pull_request_template.md](../../.github/pull_request_template.md) | (无一级标题) |
| [2026-08-29-第01次测试计划.md](../../2026-08-29-第01次测试计划.md) | DataPulse 第 01 次测试计划：核心闭环与容器构建回归 |
| [2026-08-31-第02次测试计划.md](../../2026-08-31-第02次测试计划.md) | DataPulse 大屏组件系统与演示数据第 02 次测试计划 |
| [2026-09-07-第03次测试计划.md](../../2026-09-07-第03次测试计划.md) | DataPulse 第 03 次测试计划：交互折线图修复与发布播放回归 |
| [CONTRIBUTING.md](../../CONTRIBUTING.md) | 贡献指南 |
| [docs/known-issues.md](../../docs/known-issues.md) | DataPulse 已知问题清单 |
| [docs/operations/backup-restore.md](../../docs/operations/backup-restore.md) | Backup and restore |
| [docs/operations/component-contributions.md](../../docs/operations/component-contributions.md) | 组件贡献规范 |
| [docs/operations/delivery-demo.md](../../docs/operations/delivery-demo.md) | 交付演示 |
| [docs/operations/ecosystem-plugins.md](../../docs/operations/ecosystem-plugins.md) | 离线模板目录与组件插件 |
| [docs/operations/identity-permissions.md](../../docs/operations/identity-permissions.md) | 用户与资源权限 |
| [docs/operations/local-validation.md](../../docs/operations/local-validation.md) | 本地容器与容量预检 |
| [docs/operations/resource-sharing.md](../../docs/operations/resource-sharing.md) | 用户与资源共享 |
| [docs/operations/restore-rehearsal-local.md](../../docs/operations/restore-rehearsal-local.md) | 本地完整恢复演练记录 |
| [docs/operations/security-capacity.md](../../docs/operations/security-capacity.md) | Processing isolation and capacity |
| [docs/operations/speech-workers.md](../../docs/operations/speech-workers.md) | Speech worker consistency |
| [docs/operations/version-migrations.md](../../docs/operations/version-migrations.md) | 版本迁移与回滚 |
| [docs/PHASE_FOUR_CLOSEOUT.md](../../docs/PHASE_FOUR_CLOSEOUT.md) | 第四阶段开发与本地验证交付记录 |
| [docs/PHASE_FOUR_PROGRESS.md](../../docs/PHASE_FOUR_PROGRESS.md) | 第四阶段实现与验收进度 |
| [docs/PHASE_FOUR_TARGET_ENVIRONMENT.md](../../docs/PHASE_FOUR_TARGET_ENVIRONMENT.md) | 产品第四阶段目标环境与生产成熟度门禁 |
| [docs/PHASE_THREE_PROGRESS.md](../../docs/PHASE_THREE_PROGRESS.md) | 第三阶段数字人实现与验收进度 |
| [docs/PHASE_TWO_CLOSEOUT.md](../../docs/PHASE_TWO_CLOSEOUT.md) | DataPulse 产品第二阶段收尾结论 |
| [docs/prompts/2026-09-21-phase-four-development-prompt.md](../../docs/prompts/2026-09-21-phase-four-development-prompt.md) | DataPulse 最后一阶段开发提示词 |
| [docs/prompts/2026-09-22-ai-model-and-development-prompts.md](../../docs/prompts/2026-09-22-ai-model-and-development-prompts.md) | DataPulse AI 模型选型与开发提示词 |
| [docs/prompts/2026-09-22-doc-index.md](../../docs/prompts/2026-09-22-doc-index.md) | 三阶段文档索引与约定 |
| [docs/scenarios/business.md](../../docs/scenarios/business.md) | 经营分析 |
| [docs/scenarios/equipment.md](../../docs/scenarios/equipment.md) | 设备监控 |
| [docs/scenarios/operations.md](../../docs/scenarios/operations.md) | 运营监控 |
| [docs/scenarios/README.md](../../docs/scenarios/README.md) | 场景案例库 |
| [docs/scenarios/sales.md](../../docs/scenarios/sales.md) | 销售分析 |
| [docs/superpowers/plans/2026-07-29-datasource-studio.md](../../docs/superpowers/plans/2026-07-29-datasource-studio.md) | DataPulse Datasource Studio Implementation Plan |
| [docs/superpowers/plans/2026-07-29-foundation-and-contracts.md](../../docs/superpowers/plans/2026-07-29-foundation-and-contracts.md) | DataPulse Foundation and Contracts Implementation Plan |
| [docs/superpowers/plans/2026-07-30-screen-editor-player-embedding.md](../../docs/superpowers/plans/2026-07-30-screen-editor-player-embedding.md) | DataPulse Screen Editor, Player, and Embedding Implementation Plan |
| [docs/superpowers/plans/2026-08-01-phase-three-file-data-ai.md](../../docs/superpowers/plans/2026-08-01-phase-three-file-data-ai.md) | `E3` 文件数据与 AI 分析实施计划 |
| [docs/superpowers/plans/2026-08-01-phase-three-remediation.md](../../docs/superpowers/plans/2026-08-01-phase-three-remediation.md) | DataPulse `E3` Remediation Implementation Plan |
| [docs/superpowers/plans/2026-08-08-editor-datasource-api-remediation.md](../../docs/superpowers/plans/2026-08-08-editor-datasource-api-remediation.md) | Editor, Datasource, and API Data Sources Implementation Plan |
| [docs/superpowers/plans/2026-08-09-datav-editor-workbench.md](../../docs/superpowers/plans/2026-08-09-datav-editor-workbench.md) | DataV 风格大屏编辑器工作台实施计划 |
| [docs/superpowers/plans/2026-09-21-phase-four-ecosystem.md](../../docs/superpowers/plans/2026-09-21-phase-four-ecosystem.md) | Phase Four Ecosystem Implementation Plan |
| [docs/superpowers/plans/2026-09-21-phase-four-identity.md](../../docs/superpowers/plans/2026-09-21-phase-four-identity.md) | Phase Four Identity Implementation Plan |
| [docs/superpowers/plans/2026-09-21-phase-four-operations.md](../../docs/superpowers/plans/2026-09-21-phase-four-operations.md) | Phase Four Operations Implementation Plan |
| [docs/superpowers/plans/三阶段计划.md](../../docs/superpowers/plans/三阶段计划.md) | DataPulse 三阶段开发计划 |
| [docs/superpowers/plans/开发顺序.md](../../docs/superpowers/plans/开发顺序.md) | DataPulse 开发顺序 |
| [docs/superpowers/specs/2026-07-29-datapulse-product-technical-route-design.md](../../docs/superpowers/specs/2026-07-29-datapulse-product-technical-route-design.md) | DataPulse 产品愿景与技术路线设计 |
| [docs/superpowers/specs/2026-07-29-datasource-studio-design.md](../../docs/superpowers/specs/2026-07-29-datasource-studio-design.md) | DataPulse 数据源工作台设计 |
| [docs/superpowers/specs/2026-07-30-screen-editor-player-embedding-design.md](../../docs/superpowers/specs/2026-07-30-screen-editor-player-embedding-design.md) | DataPulse 第二阶段：大屏编辑、播放与安全嵌入设计 |
| [docs/superpowers/specs/2026-08-01-phase-three-file-data-ai-design.md](../../docs/superpowers/specs/2026-08-01-phase-three-file-data-ai-design.md) | DataPulse `E3`：文件数据集与 AI 分析设计 |
| [docs/superpowers/specs/2026-08-01-phase-three-remediation-design.md](../../docs/superpowers/specs/2026-08-01-phase-three-remediation-design.md) | DataPulse `E3` 文件数据与 AI 问题修复设计 |
| [docs/superpowers/specs/2026-08-08-editor-datasource-api-remediation-design.md](../../docs/superpowers/specs/2026-08-08-editor-datasource-api-remediation-design.md) | 编辑器与数据源体验修复设计 |
| [docs/superpowers/specs/2026-08-09-datav-editor-workbench-design.md](../../docs/superpowers/specs/2026-08-09-datav-editor-workbench-design.md) | DataV 风格大屏编辑器工作台设计 |
| [docs/superpowers/specs/2026-08-31-screen-component-system-and-demo-data-design.md](../../docs/superpowers/specs/2026-08-31-screen-component-system-and-demo-data-design.md) | DataPulse 大屏设计器组件体系、视觉系统与演示数据设计 |
| [docs/superpowers/specs/2026-09-09-phase-three-digital-human-broadcast-design.md](../../docs/superpowers/specs/2026-09-09-phase-three-digital-human-broadcast-design.md) | DataPulse 产品第三阶段：数字人播报功能列表 |
| [docs/superpowers/specs/2026-09-12-phase-four-conversational-digital-human-design.md](../../docs/superpowers/specs/2026-09-12-phase-four-conversational-digital-human-design.md) | 独立产品候选：受控对话数字人 v1 设计 |
| [docs/superpowers/specs/2026-09-21-phase-four-ecosystem-design.md](../../docs/superpowers/specs/2026-09-21-phase-four-ecosystem-design.md) | 第四阶段：受控市场与组件插件 |
| [docs/superpowers/specs/2026-09-21-phase-four-identity-design.md](../../docs/superpowers/specs/2026-09-21-phase-four-identity-design.md) | 第四阶段：多用户与资源协作 |
| [docs/superpowers/specs/2026-09-21-phase-four-operations-design.md](../../docs/superpowers/specs/2026-09-21-phase-four-operations-design.md) | 第四阶段：备份恢复与运维 |
| [docs/TESTING_SESSION.md](../../docs/TESTING_SESSION.md) | 测试会话记录 |
| [examples/metric-plugin/README.md](../../examples/metric-plugin/README.md) | 示例指标插件 |
| [packages/embed-sdk/README.md](../../packages/embed-sdk/README.md) | DataPulse Embed SDK |
| [packages/plugin-sdk/README.md](../../packages/plugin-sdk/README.md) | DataPulse plugin SDK |
| [README.md](../../README.md) | DataPulse |
| [test-evidence/automation-20260829/ISSUES.md](../../test-evidence/automation-20260829/ISSUES.md) | 自动化测试问题记录 |
| [test-evidence/automation-20260908/README.md](../../test-evidence/automation-20260908/README.md) | 2026-09-08 自动化证据索引 |
| [test-evidence/automation-20260909/README.md](../../test-evidence/automation-20260909/README.md) | 2026-09-09 第二阶段自动化证据索引 |
| [test-evidence/automation-20260909/resource-audit.md](../../test-evidence/automation-20260909/resource-audit.md) | 第二阶段临时资源清理审计 |
| [test-evidence/blackbox-20260908/BB-002/light-theme-review/review.md](../../test-evidence/blackbox-20260908/BB-002/light-theme-review/review.md) | 浅色主题视觉差异评审 |
| [test-evidence/blackbox-20260908/cross-browser/firefox/error-context.md](../../test-evidence/blackbox-20260908/cross-browser/firefox/error-context.md) | Instructions |
| [test-evidence/blackbox-20260908/cross-browser/webkit/error-context.md](../../test-evidence/blackbox-20260908/cross-browser/webkit/error-context.md) | Instructions |
| [test-evidence/blackbox-20260908/README.md](../../test-evidence/blackbox-20260908/README.md) | 2026-09-08 黑盒证据索引 |
| [test-evidence/blackbox-20260909/cross-browser/review.md](../../test-evidence/blackbox-20260909/cross-browser/review.md) | Firefox/WebKit 编辑器视觉基线评审 |
| [test-evidence/blackbox-20260909/display-target/review.md](../../test-evidence/blackbox-20260909/display-target/review.md) | Retina/4K 显示证据人工评审 |
| [test-evidence/blackbox-20260909/README.md](../../test-evidence/blackbox-20260909/README.md) | 2026-09-09 第二阶段黑盒证据索引 |
| [test-evidence/phase-four/local-20260921/chromium-artifacts/file-dataset-administrator-17f54-moves-a-Chinese-CSV-dataset-chromium/error-context.md](../../test-evidence/phase-four/local-20260921/chromium-artifacts/file-dataset-administrator-17f54-moves-a-Chinese-CSV-dataset-chromium/error-context.md) | Instructions |
| [test-evidence/phase-four/local-20260921/chromium-artifacts/screen-editor-administrato-b7823-and-plays-a-complete-screen-chromium/error-context.md](../../test-evidence/phase-four/local-20260921/chromium-artifacts/screen-editor-administrato-b7823-and-plays-a-complete-screen-chromium/error-context.md) | Instructions |
| [test-evidence/phase-four/local-20260921/cross-browser-artifacts/ai-analysis-AI-analysis-us-3d460-art-and-preserves-the-draft-firefox/error-context.md](../../test-evidence/phase-four/local-20260921/cross-browser-artifacts/ai-analysis-AI-analysis-us-3d460-art-and-preserves-the-draft-firefox/error-context.md) | Instructions |
| [test-evidence/phase-four/local-20260921/cross-browser-artifacts/ai-analysis-AI-analysis-us-3d460-art-and-preserves-the-draft-webkit/error-context.md](../../test-evidence/phase-four/local-20260921/cross-browser-artifacts/ai-analysis-AI-analysis-us-3d460-art-and-preserves-the-draft-webkit/error-context.md) | Instructions |
| [test-evidence/phase-four/local-20260921/cross-browser-artifacts/ai-screen-generation-AI-sc-ba43f-irms-with-one-atomic-create-webkit/error-context.md](../../test-evidence/phase-four/local-20260921/cross-browser-artifacts/ai-screen-generation-AI-sc-ba43f-irms-with-one-atomic-create-webkit/error-context.md) | Instructions |
| [test-evidence/phase-four/local-20260921/cross-browser-artifacts/datasource-studio-administ-9a11d-analyze-a-SQLite-datasource-webkit/error-context.md](../../test-evidence/phase-four/local-20260921/cross-browser-artifacts/datasource-studio-administ-9a11d-analyze-a-SQLite-datasource-webkit/error-context.md) | Instructions |
| [test-evidence/phase-four/local-20260921/cross-browser-artifacts/first-stage-creation-blank-f8379-tion-undo-redo-and-playback-webkit/error-context.md](../../test-evidence/phase-four/local-20260921/cross-browser-artifacts/first-stage-creation-blank-f8379-tion-undo-redo-and-playback-webkit/error-context.md) | Instructions |
| [test-evidence/phase-four/local-20260921/cross-browser-artifacts/first-stage-creation-edito-b83e8-h-dialog-closes-with-Escape-webkit/error-context.md](../../test-evidence/phase-four/local-20260921/cross-browser-artifacts/first-stage-creation-edito-b83e8-h-dialog-closes-with-Escape-webkit/error-context.md) | Instructions |
| [test-evidence/phase-four/local-20260921/cross-browser-artifacts/first-stage-creation-scree-51e0d-ect-and-embed-authorization-webkit/error-context.md](../../test-evidence/phase-four/local-20260921/cross-browser-artifacts/first-stage-creation-scree-51e0d-ect-and-embed-authorization-webkit/error-context.md) | Instructions |
| [test-evidence/phase-four/local-20260921/cross-browser-artifacts/first-stage-creation-templ-637fe-rs-the-shared-screen-editor-webkit/error-context.md](../../test-evidence/phase-four/local-20260921/cross-browser-artifacts/first-stage-creation-templ-637fe-rs-the-shared-screen-editor-webkit/error-context.md) | Instructions |
| [test-evidence/phase-four/local-20260921/cross-browser-artifacts/screen-editor-administrato-b7823-and-plays-a-complete-screen-firefox/error-context.md](../../test-evidence/phase-four/local-20260921/cross-browser-artifacts/screen-editor-administrato-b7823-and-plays-a-complete-screen-firefox/error-context.md) | Instructions |
| [test-evidence/phase-four/local-20260921/cross-browser-artifacts/screen-editor-administrato-b7823-and-plays-a-complete-screen-webkit/error-context.md](../../test-evidence/phase-four/local-20260921/cross-browser-artifacts/screen-editor-administrato-b7823-and-plays-a-complete-screen-webkit/error-context.md) | Instructions |
| [test-evidence/phase-four/local-20260921/cross-browser-artifacts/screen-editor-multi-select-0993d-sists-the-same-canvas-delta-webkit/error-context.md](../../test-evidence/phase-four/local-20260921/cross-browser-artifacts/screen-editor-multi-select-0993d-sists-the-same-canvas-delta-webkit/error-context.md) | Instructions |
| [test-evidence/phase-four/local-20260921/cross-browser-artifacts/screen-playback-direct-ifr-3dd53-instance-id-query-parameter-webkit/error-context.md](../../test-evidence/phase-four/local-20260921/cross-browser-artifacts/screen-playback-direct-ifr-3dd53-instance-id-query-parameter-webkit/error-context.md) | Instructions |
| [test-evidence/phase-four/local-20260921/cross-browser-artifacts/screen-playback-host-SDK-c-7b323-n-and-rejects-unsafe-access-webkit/error-context.md](../../test-evidence/phase-four/local-20260921/cross-browser-artifacts/screen-playback-host-SDK-c-7b323-n-and-rejects-unsafe-access-webkit/error-context.md) | Instructions |
| [test-evidence/phase-four/local-20260921/cross-browser-artifacts/screen-playback-published--4d130-error-and-letterbox-visuals-webkit/error-context.md](../../test-evidence/phase-four/local-20260921/cross-browser-artifacts/screen-playback-published--4d130-error-and-letterbox-visuals-webkit/error-context.md) | Instructions |
| [test-evidence/phase-four/local-20260921/identity-retry-artifacts/identity-two-accounts-shar-7517c-ale-edits-and-revoke-access-chromium/error-context.md](../../test-evidence/phase-four/local-20260921/identity-retry-artifacts/identity-two-accounts-shar-7517c-ale-edits-and-revoke-access-chromium/error-context.md) | Instructions |
| [test-evidence/phase-four/local-20260921/review.md](../../test-evidence/phase-four/local-20260921/review.md) | 独立审查记录 |
| [test-evidence/phase-four/local-20260921/webkit-visual-artifacts/screen-editor-administrato-b7823-and-plays-a-complete-screen-webkit/error-context.md](../../test-evidence/phase-four/local-20260921/webkit-visual-artifacts/screen-editor-administrato-b7823-and-plays-a-complete-screen-webkit/error-context.md) | Instructions |
| [test-evidence/quality-baseline/README.md](../../test-evidence/quality-baseline/README.md) | Quality Baseline |

## 外部 Obsidian 项目笔记

笔记库根目录是 `/Users/dundundebaba/sync/Tanglei`，与代码仓库不同。
已定位的全部项目 Markdown 笔记如下：

| 原位置（相对笔记库） | 维护判断 |
| --- | --- |
| `开源/datapulse/愿景.md` | 长期定位参考；其中多用户/市场排除项已被后续产品设计更新 |
| `开源/datapulse/当前进度.md` | 最后核对 2026-08-29，分支、提交和待办已过时 |
| `开源/datapulse/完成情况.md` | 最后核对 2026-08-29，勾选状态不能作为当前验收 |
| `开源/datapulse/三阶段计划.md` | 仓库执行副本为 `docs/superpowers/plans/三阶段计划.md` |
| `开源/datapulse/开发顺序.md` | 仓库执行副本为 `docs/superpowers/plans/开发顺序.md` |
| `开源/datapulse/AI模型选型与开发提示词.md` | 仓库执行副本为 `docs/prompts/2026-09-22-ai-model-and-development-prompts.md` |
| `开源/datapulse/三阶段文档索引.md` | 仓库执行副本为 `docs/prompts/2026-09-22-doc-index.md` |

四组仓库/笔记副本本次字节比较均不完全相同；其中可能含双链格式差异。
按现有约定，**仓库是唯一执行来源**，修改先落仓库再同步笔记。
本次只整理与引用，没有更新外部笔记或替换原始需求文档。

## 其他仓库外项目资产

本次确认以下文件仍在原机器，均不在 `FILES.tsv` 或 Git 内：

| 位置 | 用途 |
| --- | --- |
| `/Users/dundundebaba/WorkBuddy/2026-07-29-15-56-14/12个大屏可视化开源项目报告.html` | 最初产品/技术路线会话使用的参考报告，当前 34,198 字节 |
| `/Users/dundundebaba/Documents/Codex/2026-08-31/mysql-orbstack/outputs/README.md` | 外部 ERP MySQL 测试资产说明 |
| `/Users/dundundebaba/Documents/Codex/2026-08-31/mysql-orbstack/outputs/docker-compose.yml` | 当时测试 MySQL 的 OrbStack/Docker 配置，可能含专用凭据 |
| 同目录 `sql/001_schema.sql` | 初始 ERP 表结构 |
| 同目录 `sql/002_seed.sql` | 初始样例数据 |
| 同目录 `sql/003_schema_extensions.sql` | 扩展表/视图 |
| 同目录 `sql/004_bulk_seed.sql` | 大批量样例数据脚本 |

外部 ERP 历史地址为 `127.0.0.1:3307`、库 `erp_ops`；当前容器状态未验证。
本次只核对上述路径存在，未复制配置、SQL 内容或凭据；接手使用前按专用测试资产重新核实。
其上下文与中文编码待确认问题见 [会话 M08](SESSIONS.md#m08)。
