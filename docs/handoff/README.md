# DataPulse 维护交接

整理日期：2026-09-29；最近维护复验：2026-11-11，时区 Asia/Shanghai。面向接替维护的 agent。
依据为当前工作树、Git 历史、仓库文档、本机可访问的项目会话和本次定向回归。

## 先看当前状态

**历史交接基线为 `main@63d74c7`；2026-11-11 当前复核实际为 `main@7464c4e`，工作区干净且领先 `origin/main` 1 个提交。本次维护补充了当前 `pnpm verify` 和 M1/M2 真实模型阻塞证据；真实模型与目标环境门禁仍未通过。**

| 项目 | 交接时事实 |
| --- | --- |
| 仓库 | `/Users/dundundebaba/sync/code/open/DataPulse` |
| Remote | `https://github.com/lotusTanglei/DataPulse.git` |
| 当前分支 | `main` |
| HEAD | 当前复核 `7464c4e`（2026-11-11 证据化收尾） |
| 本地 main / origin/main | `origin/main..main` 有 1 个本地提交 |
| 工作树 | 当前复核干净；本次维护仅补充 `test-evidence/maintenance-20261111/` 和交接记录 |
| 文件清单 | 1,432 个跟踪或未忽略文件；包括 91 份 Markdown 文档 |
| 本次运行 | `pnpm test:e2e`：28 passed，退出码 0；集成数据库项 1 passed、12 skipped（缺少测试 URL） |
| 最近开发进度答复 | 2026-09-23 主会话估计整体约 85%；这是当时人工估计，不是验收比例 |
| 产品第四阶段 | 本地开发与历史回归已交付，八项目标环境验收仍阻塞，0 项通过 |
| 本地服务 | 2026-09-29 检查时 8000、8001、5173 没有监听服务；本次未启动应用 |

当前工作树必须作为一个整体保留。仅切到 main、只下载 GitHub 或只传 `git diff`，都会遗漏未跟踪的新模块、测试、合同和交付工具。
跨机器接手还需要单独保护运行数据与密钥；本次文档不是运行实例备份。

### 2026-11-11 维护复验记录

以下结果均来自当前 `main` 开工基线及本次维护工作树，原始日志位于 [`test-evidence/maintenance-20261111/`](../../test-evidence/maintenance-20261111/)：

- `pnpm verify:no-ai`：退出码 0；AI 未加载、AI 路由隐藏、健康/认证/数据集/大屏路由检查通过。
- `pnpm verify:upgrade-rollback`：退出码 0；9 项通过。
- `pnpm demo:verify`：退出码 0；数据集画像、静态语音降级、发布/播放/Embed 和权限拒绝通过。
- `pnpm test:integration`：退出码 0；1 项通过，12 项因未配置 `DATAPULSE_TEST_MYSQL_URL`/`DATAPULSE_TEST_POSTGRES_URL` 跳过，不能视为真实数据库全通过。
- `pnpm test:e2e`：退出码 0；Chromium 28 项通过。期间修复文件数据集保存按钮的非精确定位，并更新组件注册表扩展后的 Darwin 视觉基线；更新理由与 diff 复核见 `e2e.log` 和提交差异。
- 未执行真实模型质量门禁（M1/M2）及八项目标环境门禁；这些仍是待验收项。

### 2026-11-11 当前工作树复核

- **有证据**：`git status --short --branch`、`git log -1 --oneline`、`git log --oneline origin/main..main` 显示 `main@7464c4e`，工作区干净，领先远端 1 个提交。
- **有证据**：`pnpm verify` 退出码 0；完整输出与计数见 `test-evidence/maintenance-20261111/verify-current-rerun.log`。
- **有证据**：固定 `gpt-6-astra` / `golden-v1` fixture 评测退出码 0，但真实 OpenAI-compatible 评测因缺少 `DATAPULSE_AI_BASE_URL`、`DATAPULSE_AI_API_KEY` 退出码 2，记录为 BLOCKED；不得把 fixture 报告当作 M1/M2 真实证据。详见 `test-evidence/maintenance-20261111/README.md`。
- **文档声明**：P4 八项目标环境仍按 `docs/PHASE_FOUR_TARGET_ENVIRONMENT.md` 阻塞，不执行伪验收。

## 交接材料

| 文件 | 用途 |
| --- | --- |
| [根目录 AGENTS.md](../../AGENTS.md) | 新 agent 自动读取的入口、执行来源与长期维护约束 |
| [本文件](README.md) | 当前状态、完整模块地图、开发/验证方法和下一步 |
| [SESSIONS.md](SESSIONS.md) | 所有已定位项目会话的目录、决策时间线与未完事项 |
| [INVENTORY.md](INVENTORY.md) | 全部 Markdown 文档、外部笔记、目录用途与忽略内容说明 |
| [FILES.tsv](FILES.tsv) | 交接新增前逐文件路径、Git 状态和字节数快照 |
| [VERIFICATION.md](VERIFICATION.md) | 本次四个失败的实际命令、错误、适配缺口与历史验证边界 |

建议阅读顺序：本文件的当前状态和接手顺序 -> 验证记录 -> 相关会话 -> 当前批次计划 -> 任务涉及模块。
完整源码与历史证据仍保留在原目录；这里提炼维护上下文并给出可追溯索引。

## 项目定位与范围

DataPulse 是面向私有部署、系统嵌入和 AI 辅助分析的数据分析与大屏创作软件。
专业用户可手工制作，普通用户可借助 AI；空白、模板、AI 创建进入同一编辑器，共用文档、组件、命令、预览和发布链路。

当前磁盘代码包含：

- 本地多用户账号、管理员/编辑者/只读角色、逐资源共享和 revision 冲突检测。
- SQLite、PostgreSQL、MySQL/MariaDB、HTTP API，以及 CSV/Excel/JSON/Parquet 数据接入。
- 数据集画像、字段修正、规则推荐；新语义层包含计算字段、固定指标与层级定义，文件查询适配尚有失败。
- 可视化画布、数据绑定、全局参数、联动、5 个模板、当前注册的 40 类内置组件。
- AI 分析、图表建议、整屏 Plan 规划和确定性编译、生成自检、局部修改预览。
- 数字人播报、字幕、媒体、静态/无音频降级、TTS 与持久化 speech worker。
- 草稿预览、人工确认发布、显示密钥播放、安全 Embed Ticket 和宿主 SDK。
- 可信离线模板/插件安装、精确版本依赖、备份恢复、质量评测、示例交付与迁移工具。

这些是模块实现范围，不能替代逐项验收结论。旧 README 的“21 类组件”描述的是早期基线；当前注册表为原有 22 类（含数字人）加新扩展 18 类，共 40 类。

长期边界：一个组件只绑定一个数据集；跨源合并在上游视图或接口完成。
不做单图跨数据集 join、临时 ETL、数据仓库、跨库事务、任意用户代码执行或自动发布。
当前多用户权限不等于独立租户隔离；元数据中没有 tenant/org 模型。
实时共同编辑、组织树、行列级权限、外部身份联邦、公共交易市场和对话数字人不在当前交付范围。

## 文档优先级与阶段编号

**仓库是唯一执行来源。** 代码根与 Obsidian 根不同，不能在代码根查 `开源/datapulse/...`。
四份近期执行文档为：

- [三阶段计划](../superpowers/plans/三阶段计划.md)，2026-09-22 v3。
- [开发顺序](../superpowers/plans/开发顺序.md)，批次依赖和 M0/M1/M2/M3 门禁。
- [模型选型与开发提示词](../prompts/2026-09-22-ai-model-and-development-prompts.md)，已确认约束与按批次提示词。
- [文档索引](../prompts/2026-09-22-doc-index.md)，两根目录与同步规则。

必读文件缺失时报告原路径，不能用旧计划替代推测。模型推荐、价格和账号可用性是 2026-09-22 的历史记录，切换模型时须重新核实供应商支持并完成真实质量门禁。

存在三套编号，互不一一对应：

| 编号体系 | 含义与状态 |
| --- | --- |
| 早期工程 E1/E2/E3/E4 | 数据基础、编辑交付、文件与 AI 等工程顺序；不是产品版本号 |
| 产品四阶段 | 1 基础闭环；2 数据理解与融合创作，`08adadb` 历史验收已完成；3 数字人播报功能及本地回归已完成；4 产品成熟度与生态，本地实现已交付、真实环境未完成 |
| 2026-09-22 新三阶段 | “多源大屏 -> 可信生成 -> 交付”的改造主线：批次 1–3、4–8、10–16；数字人和真实环境验收保留并行轨道 |

旧设计中的“不做多用户/市场”已被后续第四阶段设计更新。
Obsidian 的“当前进度/完成情况”最后核对 2026-08-29，不能覆盖仓库当前事实。
旧阶段交付记录中的“没有提交/推送”是当次执行状态；之后已有 2026-09-23 提交与合并，当前未提交部分主要是批次 10–16 后续工作。

## 目录与技术栈

| 目录 | 内容 |
| --- | --- |
| `apps/server/` | Python FastAPI、Pydantic 合同、SQLAlchemy async、Alembic、后端测试 |
| `apps/web/` | Vue 3、TypeScript、Vite、Pinia、Vue Router、ECharts、CodeMirror、Moveable/Selecto、Vitest/Playwright |
| `packages/schema/` | 从 Python 合同导出的 JSON Schema、TypeScript 声明和公共导出 |
| `packages/embed-sdk/` | 宿主系统嵌入、参数、刷新、全屏及消息协议 |
| `packages/plugin-sdk/` | 固定版本可信组件插件接口；没有 `packages/cli` |
| `examples/metric-plugin/` | 可构建的指标插件和离线打包示例 |
| `fixtures/` | Golden 四行业数据、失败样本、场景清单和交付样例 |
| `tools/` | 合同生成/检查、E2E 运行器、质量评测、演示和部署验证 |
| `deploy/` | 安全 Nginx 参考与 Prometheus 抓取/告警规则 |
| `docs/` | 需求设计、历史计划、当前批次计划、运维手册与案例 |
| `test-evidence/` | 已归档的命令日志、截图、环境、诊断和验收结果 |
| `data/` | Git 忽略的本地实例数据；不是测试 fixture，也不是源码 |

环境要求：Python `>=3.13,<3.15`，Node.js 22，pnpm 10，uv；Docker 用于容器与数据库集成。
本次实测 Node `22.23.1`、pnpm `10.33.0`、uv `0.11.6`。锁文件为 `uv.lock` 和 `pnpm-lock.yaml`。
音视频处理另需 FFmpeg/ffprobe；数据库、AI、TTS、扫描器和指标抓取按实际配置启用，基础单体无需消息队列。

## 后端模块地图

基准路径为 `apps/server/src/datapulse/`。

| 模块 | 维护入口与职责 |
| --- | --- |
| 应用装配 | [app.py](../../apps/server/src/datapulse/app.py)、[lifespan.py](../../apps/server/src/datapulse/lifespan.py)：路由注册、迁移检查、服务图、`app.state`、关闭回收 |
| 配置/错误 | [settings.py](../../apps/server/src/datapulse/settings.py)、[errors.py](../../apps/server/src/datapulse/errors.py)：`DATAPULSE_` 配置、稳定错误码和 request ID |
| 元数据 | [metadata/models.py](../../apps/server/src/datapulse/metadata/models.py)、[metadata/database.py](../../apps/server/src/datapulse/metadata/database.py)：账号、资源、草稿、发布、任务、授权、审计；默认 `data/datapulse.db` |
| 认证 | [auth/api.py](../../apps/server/src/datapulse/auth/api.py)、[auth/dependencies.py](../../apps/server/src/datapulse/auth/dependencies.py)：一次性 setup、Argon2、Cookie Session、登录限流、CSRF |
| 身份与共享 | [identity/service.py](../../apps/server/src/datapulse/identity/service.py)、[identity/policy.py](../../apps/server/src/datapulse/identity/policy.py)：admin/editor/viewer、owner、read/write/publish、传递资源校验与撤销 |
| 数据源 | [datasource/service.py](../../apps/server/src/datapulse/datasource/service.py)、`sqlite.py/postgresql.py/mysql.py/http_api.py`：连接配置、加密凭据、Schema 与四类连接器 |
| 查询 | [query/execution.py](../../apps/server/src/datapulse/query/execution.py)、`safety.py/parameters.py/limits.py`：SQL AST 只读校验、绑定、并发、超时、行数、结果标准化和执行记录 |
| 数据集 | [dataset/service.py](../../apps/server/src/datapulse/dataset/service.py)、[dataset/profile.py](../../apps/server/src/datapulse/dataset/profile.py)、[dataset/semantics.py](../../apps/server/src/datapulse/dataset/semantics.py)、[dataset/recommendations.py](../../apps/server/src/datapulse/dataset/recommendations.py)：持久化、预览、画像、规则推荐与语义 |
| 文件 | [filedata/parsers.py](../../apps/server/src/datapulse/filedata/parsers.py)、[filedata/query.py](../../apps/server/src/datapulse/filedata/query.py)、[filedata/duckdb_executor.py](../../apps/server/src/datapulse/filedata/duckdb_executor.py)：受限解析、规范化 Parquet、缓存和 DuckDB；查询编译当前存在回归 |
| 规划编译 | [screen/planning.py](../../apps/server/src/datapulse/screen/planning.py)、[screen/compiler.py](../../apps/server/src/datapulse/screen/compiler.py)、[screen/planning_service.py](../../apps/server/src/datapulse/screen/planning_service.py)：Plan 校验、确定性网格布局、分区重编译、查询预执行和自检 |
| 图表运行 | [screen/chart_query.py](../../apps/server/src/datapulse/screen/chart_query.py)、[screen/runtime.py](../../apps/server/src/datapulse/screen/runtime.py)：语义表达式、维度/聚合/筛选/排序、时间分桶、下钻；按数据源执行组件查询 |
| 发布 | [screen/publishing.py](../../apps/server/src/datapulse/screen/publishing.py)、[screen/api.py](../../apps/server/src/datapulse/screen/api.py)：revision、素材/数据集/插件引用、覆盖式发布与草稿预览 |
| AI 可选模块 | [ai/bootstrap.py](../../apps/server/src/datapulse/ai/bootstrap.py)、[ai/gateway.py](../../apps/server/src/datapulse/ai/gateway.py)、[ai/context.py](../../apps/server/src/datapulse/ai/context.py)、[ai/plan_generator.py](../../apps/server/src/datapulse/ai/plan_generator.py)：条件装配、兼容接口、画像上下文、Plan 生成与修复 |
| 素材/媒体 | [screen/assets.py](../../apps/server/src/datapulse/screen/assets.py)、[screen/media.py](../../apps/server/src/datapulse/screen/media.py)：MIME、大小、时长/像素、扫描、引用保护、受限子进程与孤儿处理 |
| 数字人/语音 | [speech/service.py](../../apps/server/src/datapulse/speech/service.py)、[speech/providers.py](../../apps/server/src/datapulse/speech/providers.py)、[worker.py](../../apps/server/src/datapulse/worker.py)：话术、字幕、TTS、缓存、配额/治理、持久任务、租约/心跳与回收 |
| 播放授权 | [display/service.py](../../apps/server/src/datapulse/display/service.py)：可撤销 display key 与仅供 player 的短期会话 |
| 嵌入授权 | [embedding/service.py](../../apps/server/src/datapulse/embedding/service.py)：宿主 API Key、限定屏幕/Origin/参数的短票据、策略复查 |
| 模板/插件 | [ecosystem/service.py](../../apps/server/src/datapulse/ecosystem/service.py)：可信 ZIP 安装、兼容性、JSON Schema、固定 ID/version 和引用保护 |
| 运维/交付 | [operations/cli.py](../../apps/server/src/datapulse/operations/cli.py)、[operations/backup.py](../../apps/server/src/datapulse/operations/backup.py)、[operations/maintenance.py](../../apps/server/src/datapulse/operations/maintenance.py)、[operations/delivery.py](../../apps/server/src/datapulse/operations/delivery.py)：离线备份、验证、恢复、维护锁与示例导入 |
| 公共合同 | [contracts/registry.py](../../apps/server/src/datapulse/contracts/registry.py)、[contracts/migrations.py](../../apps/server/src/datapulse/contracts/migrations.py)：模型注册、导出与 JSON 数据版本迁移 |

Alembic 位于 `apps/server/migrations/versions/`，链从 `0001` 至 `0021_speech_leases`；`0020_identity` 添加用户/资源权限，`0021` 添加 speech 租约。
JSON 文档/组件/命令迁移与数据库迁移是两个机制，不能混用。

## 前端与共享包地图

| 位置 | 职责与维护注意 |
| --- | --- |
| [router/index.ts](../../apps/web/src/router/index.ts) | Studio 数据源、数据集、大屏、市场、用户、共享、设置；preview/play/embed 路由；初始化/会话/角色守卫 |
| [stores/auth.ts](../../apps/web/src/stores/auth.ts)、[lib/api.ts](../../apps/web/src/lib/api.ts) | 合并认证解析、读取 `ai_enabled`、Cookie/CSRF、401 失效事件和稳定错误 |
| `features/{datasources,query,files,datasets}` | 数据接入、Schema、SQL、上传、数据集、画像字段修正与推荐；画像编辑在 [DatasetDetailView.vue](../../apps/web/src/features/datasets/DatasetDetailView.vue) |
| [ScreenEditorView.vue](../../apps/web/src/features/screens/ScreenEditorView.vue) | 组件库、画布、图层、属性、AI、发布和访问策略编排；先保存再确认发布 |
| [editor/store.ts](../../apps/web/src/features/screens/editor/store.ts) | 800 ms 自动保存，`expected_revision` 冲突停止重试，保存期间编辑在后续轮保存 |
| [editor/commands.ts](../../apps/web/src/features/screens/editor/commands.ts)、[history.ts](../../apps/web/src/features/screens/editor/history.ts) | 手工/AI/插件迁移共用命令与 batch；100 份快照撤销历史；版本化命令入口 |
| [ScreenCanvas.vue](../../apps/web/src/features/screens/editor/ScreenCanvas.vue)、[InspectorPanel.vue](../../apps/web/src/features/screens/editor/InspectorPanel.vue) | Moveable/Selecto 多选拖缩、吸附对齐、成组；按注册属性定义 `propertyGroups` 生成控件，配置单源数据绑定 |
| [ScreenRuntime.vue](../../apps/web/src/features/runtime/ScreenRuntime.vue)、[dataRuntime.ts](../../apps/web/src/features/runtime/dataRuntime.ts) | preview/standalone/embed 共用参数、刷新与适配；同轮请求合并、旧 generation 取消与过期结果屏蔽 |
| [ComponentHost.vue](../../apps/web/src/features/runtime/ComponentHost.vue) | 单组件错误隔离、受控资产、主题、QueryResult 和交互；数字人消费统一运行结果 |
| [registry.ts](../../apps/web/src/features/runtime/registry.ts)、[advancedComponents.ts](../../apps/web/src/features/runtime/builtins/advancedComponents.ts) | 40 类内置注册；新高级组件按地图、关系、计划、指标组、媒体、词云/水球、富表格和轮播分组 |
| [templates.ts](../../apps/web/src/features/screens/templates.ts)、[migrations.ts](../../apps/web/src/features/screens/migrations.ts) | 5 种模板布局、Plan 生成、文档/组件迁移；行业案例为经营/运营/销售/设备 |
| `features/ai` | 分析、图表、整屏/局部编辑；预览后一次可撤销 batch；关闭 AI 时入口隐藏并异步加载实现 |
| [PlayerView.vue](../../apps/web/src/features/player/PlayerView.vue)、[embedBridge.ts](../../apps/web/src/features/player/embedBridge.ts) | 草稿、display Session 与 ticket 三种访问；精确 Origin/来源窗口/实例 ID/请求关联 |
| `features/{ecosystem,identity,settings}` | 插件版本、账号与逐资源授权、系统/数字人供应商配置；共享页面 `SharingView` 位于 `identity` |
| [Embed SDK](../../packages/embed-sdk/README.md)、[Plugin SDK](../../packages/plugin-sdk/README.md) | 宿主消息与可信插件公共接口；固定版本，发布快照不随安装升级自动改变 |

新增组件需同时维护公共合同、前端注册、默认尺寸/样式/mock、后端发布类型和测试。
高级组件 gallery 的浏览器回归使用 mock；其中 video/iframe/carousel 为空来源，不能据此声称真实媒体与轮播路径已完整验收。

## 关键主流程与不变量

### 数据与生成

```text
数据库/文件/HTTP API -> DatasetDefinition -> 字段画像与语义
                                      -> AI 或手工 DashboardPlan
                                      -> PlanValidator -> DocumentCompiler
                                      -> 查询预执行/自检 -> 可编辑 DashboardDocument 草稿
```

SQL 保存/更新会真实执行只读查询并推断字段。文件数据集无 `data_source_id`，引用托管文件资产。
外部数据库走原生异步连接器；DuckDB 负责本地文件，不能当外部数据库代理。
同一 Plan 应得到同一布局，Plan 不含自由像素坐标；画布编辑与 AI 修改使用同一命令路径。
AI 接口为 OpenAI-compatible `/chat/completions`；优先 strict JSON Schema，不支持时回退 JSON Object，最终仍由服务端验证。
生成初次输出后最多两轮修复，组件可降级并给 warning；429 不应被重试。
当前上下文优先画像与摘要，默认不发送明细样本；实际发送内容以 `ai/context.py` 为准。
数据分类、脱敏和第三方留存仍须由部署方确认，凭据和文件绝对路径不能进入模型上下文。

### 编辑与交付

```text
编辑命令/batch -> revision 草稿保存 -> 人工确认发布
                                  -> 已发布文档快照
                                  -> 独立播放或宿主 Embed
                                  -> 同一 ScreenRuntime/ComponentHost
```

修改草稿不改变线上发布文档。发布为覆盖式，历史版本需要先复制大屏。
所有发布都校验数据集、素材和固定插件依赖；无写权限进入预览，publish 独立授权。
独立播放 key 换仅 `/api/player` 使用的 HttpOnly Session，再从 URL 移除 key；轮换撤销旧 key 和旧播放会话。
Embed Key 由宿主后端持有，ticket 最长 8 小时，限定一个大屏、精确 HTTPS Origin 与可改参数。
票据移入内存并以 Bearer 请求，不写入浏览器持久存储；宿主负责观看者身份与业务权限。

### 数字人与运维

话术/字幕消费同一运行结果；无 AI、TTS 或音频时保留可用降级。
语音任务先持久化，再原子领取、租约续期、配额预留、合成/缓存、素材保存与终态结算；失租约需取消执行。
API 内 worker 可关闭并另起独立 worker，必须共享数据库、数据路径与密钥。
可信插件由管理员安装，组件错误隔离不是恶意 JS 沙箱。
自动备份当前仅覆盖离线 SQLite 拓扑，API/worker 停止后用排他维护锁创建归档；恢复需匹配应用版本、Alembic head 和原 master key。
回滚不能把新版本写过的数据目录直接交给旧版本。

## 当前未提交批次 10–16

| 批次 | 当前工作树内容 | 接手状态 |
| --- | --- | --- |
| 10 评测 harness | `quality_harness.py`、模型 gate、趋势 dashboard、失败库、fixture 报告 | 有已复现报告支持性检查失败；真实模型证据仍需单独补充 |
| 11 数据语义 | 字段显示名/格式/别名、计算字段、固定指标、同源关系/层级、质量提示 | SQL 已扩展；文件编译器适配不完整，新接口非管理员权限待复核 |
| 12 场景扩展 | 时间粒度、下钻、多参数交互、4 类场景 fixture/案例 | 随文件语义修复后核对多源场景及各来源边界 |
| 13 AI 可选部署 | `structured_output.py`、AI bootstrap、条件路由、前端隐藏/异步加载、规则推荐、无 AI 预检 | 有证据：`verify:no-ai` 退出码 0；真实模型质量门禁仍暂缓 |
| 14 组件第二/三批 | 18 类扩展、版本化 ComponentContract、词云/水球依赖、发布校验、gallery E2E/快照 | 有证据：Chromium E2E 28 项通过并刷新 Darwin 快照；真实媒体、空态和交互覆盖不能仅靠 mock gallery |
| 15 交付闭环 | `operations/delivery.py`、`demo:verify`、`demo:deploy`、经营样例和演示手册 | 有证据：`demo:verify` 退出码 0；目标环境交付仍未验收 |
| 16 演进与生态 | 文档/组件/命令版本迁移、升级回滚命令、案例库、贡献指南/PR 模板 | 有证据：`verify:upgrade-rollback` 9 项通过；合同检查随最终 `pnpm verify` 复核 |

未跟踪的 `.idea/` 和 CodeGraph 元数据需与产品源码分别判断是否纳入提交。
逐文件状态均在 `FILES.tsv`；`git diff --stat` 不包含未跟踪模块，不能用其估算完整工作量。

## 已确认失败与待复核边界

| 优先级 | 事项 | 下一步与依据 |
| --- | --- | --- |
| 立即 | 文件图表基本查询、计算指标、时间粒度三项失败 | 统一适配 `FileQueryCompiler` 的字段表达式和聚合 helper；见 [实际失败](VERIFICATION.md) |
| 立即 | 模型 gate 放行双方均为不支持版本且缺 fixture 的报告 | 各自检查支持版本和元数据，再检查可比较性；保留已有拒绝回归 |
| 收尾复核 | 推荐/语义新路由未加入身份策略白名单 | `get_dataset_recommendations/get_dataset_semantics/update_dataset_semantics` 对非 admin 默认拒绝；按 editor/read/write 需求补齐验证 |
| 能力边界 | REST runtime 直接执行 JSON 请求映射 | 没有走 SQL/file 的 ChartSpec 聚合/时间粒度/下钻编译；不能宣称所有来源语义能力一致 |
| 能力边界 | `DatasetDefinition.cache/refresh` | 后端未找到通用查询结果缓存或 cron 调度实现；前端轮询、文件解析缓存和 speech 缓存是不同能力 |
| 能力边界 | DuckDB timeout | `asyncio.timeout + to_thread` 不保证底层线程立刻停止；容量治理要在真实负载下核实 |
| 数据侧 | ISS-016 ERP 中文字段疑似双重编码 | 等数据源所有者确认，不能擅自改外部数据或生产凭据 |

这些待复核事项不额外算入本次“四项已复现失败”数量，也不把潜在扩展写成已承诺新功能。

## 开发与配置

仓库根安装依赖并迁移：

```bash
uv sync --all-packages --group dev --frozen
pnpm install --frozen-lockfile
uv run --package datapulse-server alembic -c apps/server/alembic.ini upgrade head
```

分别启动后端和前端：

```bash
uv run --package datapulse-server uvicorn datapulse.app:app --reload
pnpm dev:web
```

Studio：`http://127.0.0.1:5173/studio`；API 健康：`http://127.0.0.1:8000/api/health`。
前端默认代理 8000，`VITE_API_PROXY_TARGET` 可覆盖。端口占用时使用空闲端口并同步代理配置。
启动日志的一次性初始化码只在首次初始化使用；不要写入交接、提交或截图证据。

| 配置 | 维护要点 |
| --- | --- |
| `DATAPULSE_DATA_DIR` / `DATAPULSE_DATABASE_URL` | 本地默认 `data/` 与 SQLite `datapulse.db`；容器为 `/data`，元数据 URL 可配置 |
| `DATAPULSE_MASTER_KEY` / `DATAPULSE_SIGNING_KEY` | 各自独立随机 32 字节 URL-safe Base64；不能复用；恢复要保留原 master key |
| `DATAPULSE_AI_ENABLED` | 默认 false；开启再配置 base URL、API key 和 model；本次不读取实际凭据 |
| AI 上下文/超时 | 普通超时默认 30 秒，整屏默认 120 秒；字段/行/字符预算以 `settings.py` 和当前 context 为准 |
| 文件/DuckDB | 默认 100 MiB 上传、5,000 行、2 线程、512 MB 内存、30 秒超时；生产按容量实测配置 |
| `DATAPULSE_SPEECH_WORKER_ENABLED` | API 内 worker 开关；独立进程命令 `uv run --package datapulse-server datapulse-speech-worker` |
| `DATAPULSE_FORWARDED_ALLOW_IPS` | 只信任实际代理，禁止 `*`；代理覆写不可信转发头，并保护 Secure Cookie/CSP |
| 扫描器/媒体 | 受限子进程、并发、取消回收；fixture 扫描不能替代实际扫描器验收 |
| `DATAPULSE_METRICS_TOKEN` | 独立内部抓取 bearer token，默认关闭，不复用管理员或签名凭据 |

Docker 单镜像自动执行 Alembic 后启动；完整部署步骤以 [README](../../README.md) 和 [本地运维验证](../operations/local-validation.md) 为准。
`pnpm demo:deploy` 会构建/启动容器并创建 `.env.demo`，不是只读检查；本次未运行。

## 验证命令与证据口径

| 命令 | 实际覆盖 |
| --- | --- |
| `pnpm generate:contracts` | Python 合同 -> JSON Schema -> TypeScript 声明/导出，修改生成物 |
| `pnpm check:contracts` | 临时重新生成并比较，不修改工作树 |
| `pnpm verify` | 合同 + SDK/Web/后端非 integration 测试 + 类型 + Web 构建 |
| `pnpm verify:full` | verify + 真实数据库 integration + Chromium E2E |
| `pnpm test:integration` | PostgreSQL/MariaDB 连接器，需测试数据库或 `compose.test.yaml` 服务 |
| `pnpm test:e2e` | 隔离临时数据和随机空闲端口，默认 Chromium，不复用现有实例 |
| `pnpm test:e2e:cross-browser` | Firefox/WebKit 顺序执行、独立数据库与证据目录 |
| `pnpm verify:no-ai` | 无 AI 启动、基础 API、`auth_status.ai_enabled`、AI 路由 404 与无 AI 模块加载；不包含浏览器 UI 隐藏验收 |
| `pnpm demo:verify` | 干净临时实例中的接入、画像、静态播报、发布、播放、Embed 和权限拒绝 |
| `pnpm verify:upgrade-rollback` | Alembic、合同迁移、备份恢复/重启/交付演练 |
| `pnpm quality:baseline` / `quality:harness` / `quality:gate` | Golden 质量采集、多报告比较、趋势/失败归档和升级阻断 |
| `pnpm test:e2e:display` / `test:e2e:soak` | 独立显示/长播目标配置；物理设备与 28,800 秒门禁不能由仿真替代 |
| `uv run --package datapulse-server ruff check apps/server tools` | CI Python 检查；另有 `ruff format --check apps/server tools` |

CI 还检查 Linux Docker 构建和 Python 3.14 后端/合同兼容。
质量 Golden 为 4 类行业、各 2 case，共 8 case；`fixture` 的成功率和固定耗时不是供应商真实实测。
2026-09-23 旧 Sol fixture 成本为 0，而当前工具对未知模型无定价配置会拒绝；旧报告不能当当前真实模型成本依据。
更新视觉快照必须先检查 actual/diff 并记录理由，不能通过批量刷新消除失败。
测试证据不得含 Session、Ticket、API Key、display key、初始化码或数据库密码；不要外发未脱敏 trace。

主要历史证据入口：

- [第二阶段交付](../PHASE_TWO_CLOSEOUT.md) 与 `test-evidence/automation-20260908/`、`automation-20260909/`、`blackbox-20260908/`、`blackbox-20260909/`。
- [数字人进度](../PHASE_THREE_PROGRESS.md)。
- [第四阶段交付](../PHASE_FOUR_CLOSEOUT.md) 与 [证据索引](../../test-evidence/phase-four/local-20260921/index.json)。
- [质量 baseline 说明](../../test-evidence/quality-baseline/README.md)。
- 三份根目录测试计划、[测试会话台账](../TESTING_SESSION.md) 与 [已知问题](../known-issues.md)。

## 尚未关闭的目标验收

用户在 2026-09-21 明确目标环境“尚未准备，先完成开发和本地验证”。
以下八项仍全部阻塞；本次没有新增目标环境通过结果：

| 门禁 | 缺少的实际条件 |
| --- | --- |
| P4-ENV-001 | 组织真实浏览器/密码管理器组合与专用配置 |
| P4-ENV-002 | 将上线的完整 LB/WAF/CDN/代理链、TLS 与日志策略 |
| P4-ENV-003 | 物理 4K/高 DPI 设备和现场核对 |
| P4-ENV-004 | 目标浏览器/代理/kiosk 连续 28,800 秒窗口和资源趋势 |
| P4-DH-001 | 真实 TTS 专用账号、供应商故障/语言矩阵 |
| P4-DH-002 | 真实跨域媒体、屏幕阅读器、手势和播放矩阵 |
| P4-DH-003 | 目标首帧/字幕/音频基线、数字人 8 小时长播和跨主机调度 |
| P4-DH-004 | 生产告警接收、真实扫描器/签名库、隔离与重启/容量证据 |

按 [目标环境手册](../PHASE_FOUR_TARGET_ENVIRONMENT.md) 逐项执行并保存脱敏证据；DP-005、ISS-022 保持打开。
本地 10 分钟浸泡、Retina 抽样、4K 仿真、fake TTS、告警规则语法通过都不能关闭上述门禁。
新三阶段 M1/M2/M3 的真实生成质量、一日交付和模型零回归也不能只凭 fixture/代码存在声明通过。

## 建议接手顺序

1. 核对当前分支、HEAD、未提交文件和本交接快照，先保留全部已有成果。
2. 阅读本节的 2026-11-11 复验记录、[最新开发主会话](SESSIONS.md) 与新三阶段计划，确认批次 13–16 的证据已归档。
3. 在测试数据库凭据可用时补跑 MySQL/PostgreSQL 集成项；同时按 [VERIFICATION.md](VERIFICATION.md) 继续核对文件语义适配和模型 gate 支持性校验。
4. 变更后执行当前工作树的 `pnpm verify`；按变更范围补 E2E、无 AI、交付、迁移/恢复与真实数据库门禁。
5. 记录当前源码、环境、命令退出码与失败/跳过，更新进度；真实模型和目标环境缺条件时继续明确保留待验收。
6. 功能/测试/合同/工具/文档一起形成可审查的提交范围，排除 IDE、缓存、凭据和本地实例数据。

## 新 Agent 启动提示词

```text
接手 DataPulse 维护，工作目录 /Users/dundundebaba/sync/code/open/DataPulse。
先读 AGENTS.md 和 docs/handoff/README.md，再读 VERIFICATION.md、SESSIONS.md。
当前分支 main，开工基线 HEAD 63d74c7；2026-11-11 维护复验日志位于 `test-evidence/maintenance-20261111/`。
最新工作是三阶段改造的批次 13–16 证据化收尾；Chromium E2E 28 项已通过，真实数据库、模型和目标环境门禁仍按记录保留。
按仓库当前计划和用户的新任务推进；不要用旧阶段或Obsidian旧进度替代。
单组件单数据集、AI可选、人工确认发布、版本兼容、安全和授权边界必须保持。
报告实际验证结果，历史通过和fixture不能证明当前验收；八项目标环境门禁仍阻塞。
```

## 2026-09-29 历史整理结果

2026-09-29 本次只新增 agent 入口与交接材料，未修改既有产品代码、计划、测试、外部笔记或原始会话。
文件清单、文档索引和会话范围均为本机可访问记录的快照；被删除、其他机器或不可访问平台的会话不能由本次核实覆盖。
本次已实际复跑并记录四项失败；全量产品验证未执行。
交接文档独立核对：225 个本地链接均存在；快照 1,432 个文件的路径/字节数一致，91 份 Markdown 文档计数一致；21 主会话加 18 子任务为 39 唯一会话，42 个原始记录路径均存在。
既有跟踪文件仍为原来的 78 个修改，`git diff --check` 与新增交接文件差异格式检查无空白错误。以上历史文档核对不能据此声明产品全部通过；当前状态以本文件 2026-11-11 复验记录和仓库 `git log` 为准。
