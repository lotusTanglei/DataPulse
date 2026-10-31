# DataPulse Agent 入口

## 先读交接

- 首先阅读 `docs/handoff/README.md`，再按任务查 `docs/handoff/SESSIONS.md` 和 `docs/handoff/INVENTORY.md`。
- 交接是 2026-09-29 的状态快照。开始修改前重新检查 `git status --short --branch` 与相关文件的当前内容，保留已有未提交成果。
- 最近的开发任务是新三阶段计划的批次 10–16，尚未最终验收。已复现的失败和复跑命令见 `docs/handoff/VERIFICATION.md`。

<!-- CODEGRAPH_START -->
## CodeGraph

仓库根存在 `.codegraph/` 时，理解或定位代码先用 CodeGraph：

- 有 MCP 工具时用 `codegraph_explore`；指定文件或符号可取得当前行号源码。
- Shell 可用 `codegraph explore "符号名或问题"`。
- 索引定位不足时再核对磁盘文件和调用方。没有 `.codegraph/` 时跳过；不要自行建立索引。
<!-- CODEGRAPH_END -->

## 执行来源

- 代码仓库：`/Users/dundundebaba/sync/code/open/DataPulse`。
- 仓库是唯一执行来源；Obsidian 根是 `/Users/dundundebaba/sync/Tanglei`，不要把笔记路径当代码路径。
- 近期开发依据为 `docs/superpowers/plans/三阶段计划.md`、`docs/superpowers/plans/开发顺序.md`、`docs/prompts/2026-09-22-ai-model-and-development-prompts.md`。
- 必读文档缺失时报告具体路径，不能用旧阶段计划猜测任务。按用户指定批次执行。
- 产品四阶段、近期三阶段改造、工程 E1/E2/E3 是不同编号体系；含义与历史变更见交接总览。

## 维护边界

- 后端在 `apps/server/src/datapulse/`，前端在 `apps/web/`；优先复用现有模块和辅助函数。
- 跨仓库涉及 Sunbox 后端时，默认在项目专属服务库（如 `backend/sunbox-store`、`backend/sunbox-storecloud`）实现；未经用户明确要求，不向 `backend/sunbox` 添加新代码。
- 一个组件只绑定一个数据集。跨源合并由上游视图或接口提供；不实现单图跨数据集 join、临时 ETL 或任意代码执行。
- AI 仅产生 Plan、预览或草稿；发布必须由有发布权限的用户明确确认。核心模块不得依赖 AI，关闭 AI 后规则推荐、编辑与交付继续可用。
- Python `contracts/` 是合同源；修改后运行 `pnpm generate:contracts`，连同 JSON Schema 和 TypeScript 生成物一起维护。
- 文档、组件、模板和编辑命令的版本变更必须声明兼容与迁移策略，拒绝未来版本。
- 维护认证、CSRF、资源授权依赖、只读查询、显示密钥撤销、Embed 精确 Origin/CSP 和凭据脱敏约束。
- 新组件遵循 `docs/operations/component-contributions.md`；更新视觉基线前人工核对 actual/diff。
- 不提交 `.env*` 实际配置、密钥、运行数据、原始含凭据 trace、依赖缓存或 IDE 配置。

## 验证口径

- 行为变更按现有贡献流程增加回归检查，批次结束运行 `pnpm verify`；涉及数据库、浏览器、恢复或部署时运行相应额外门禁。
- `pnpm verify` 不包含真实数据库 integration 与 E2E；命令全集见交接总览。
- 第四阶段八项目标门禁仍阻塞；fixture、短时预检、仿真和本地通过不能关闭真实环境验收。
- 历史通过、最新失败、中断、skip/deselect 与未执行必须分别报告。交接文档里的测试计数不是当前工作树通过证明。
