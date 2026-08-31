# 自动化测试问题记录

- 执行日期：2026-08-29
- 分支/提交：`main` / `a0e973e0475f01dd735dcae6448fd56fcc562ae`
- 范围：本次自动化测试命令及其测试环境，以及同一会话中已完成的黑盒问题索引；黑盒详细证据位于 `../blackbox-20260829/`。

## ISS-001：Docker daemon 不可用，阻塞外部数据库和容器测试

- 类型：环境阻塞
- 优先级：P0
- 状态：已解决
- 影响范围：AUTO-INT-006、AUTO-E2E-004、AUTO-E2E-005
- 现象：Docker CLI 无法连接 `unix:///Users/dundundebaba/.orbstack/run/docker.sock`，因此 PostgreSQL/MariaDB Compose 服务无法启动，Docker 镜像无法构建或运行。
- 复现命令：`docker compose -f compose.test.yaml up -d --wait`；`docker build --tag datapulse-test:20260829 .`
- 证据：
  - `AUTO-INT-006-compose-up.log`
  - `AUTO-INT-006.log`
  - `AUTO-E2E-004.log`
  - `AUTO-E2E-005.log`
- 处理结果：已启动 OrbStack；Compose 服务恢复，AUTO-INT-006 重试通过。Docker 构建的后续网络阻塞也已通过镜像源预拉取解决，见 ISS-005。

## ISS-002：AUTO-UNIT-005/006 定向 Vitest 命令未按文件过滤

- 类型：测试命令/配置问题
- 优先级：P1
- 状态：已解决；定向集合已用修正命令复核通过，计划命令已更新
- 影响范围：AUTO-UNIT-005、AUTO-UNIT-006
- 现象：计划中的命令带有 `pnpm ... test -- <file list>`，实际日志显示 Vitest 执行了全部 28 个测试文件、122 个测试，而不是仅执行列出的文件。
- 复现命令：
  - `pnpm --filter @datapulse/web test -- src/features/auth/auth.test.ts src/features/datasources/datasource-form.test.ts src/features/datasources/schema-browser.test.ts src/features/datasets/datasets.test.ts src/features/query/sql-debug.test.ts`
  - `pnpm --filter @datapulse/web test -- src/features/screens/screen-list.test.ts src/features/screens/templates.test.ts src/features/screens/editor/geometry.test.ts src/features/screens/editor/commands.test.ts src/features/screens/editor/canvas.test.ts src/features/screens/editor/store.test.ts src/features/screens/editor/inspector.test.ts src/features/runtime/runtime.test.ts src/features/player/standalone-player.test.ts src/features/player/embed-player.test.ts src/features/player/player.test.ts`
- 原始结果：全量 Web 测试均通过，但原始结果不能证明列出的定向集合单独通过。
- 复核结果：使用不经过 `--` 终止符的 Vitest 直接调用后，AUTO-UNIT-005 定向集合为 5 files/30 tests passed，AUTO-UNIT-006 定向集合为 11 files/59 tests passed，均退出码 `0`。
- 证据：`AUTO-UNIT-005.log`、`AUTO-UNIT-006.log`（原始命令）；`AUTO-UNIT-005-targeted.log`、`AUTO-UNIT-006-targeted.log`（修正命令）。
- 处理结果：计划和模板中的执行命令已改为 `pnpm --filter @datapulse/web exec vitest run <file list>`；定向集合复核通过，避免再次产生范围误判。

## ISS-003：测试计划生成说明与后续执行状态不一致

- 类型：文档追踪问题
- 优先级：P1
- 状态：已解决，计划文件现同时记录执行结果和问题
- 现象：`2026-08-29-第01次测试计划.md` 的“生成说明”写着“没有执行本计划中的测试套件”，该描述在计划生成时成立，但在本轮自动化测试完成后已过时；同时用例状态按原始要求仍保留为“未执行”。
- 影响：读者可能误以为自动化命令完全没有运行，无法仅凭计划文件区分“计划状态”和“执行状态”。
- 处理结果：测试结果和问题已回写 `2026-08-29-第01次测试计划.md` 的“测试执行结果”和“发现的问题”章节；本文件作为问题索引和证据导航。

## 残余风险与未关闭事项

自动化断言和本轮修复回归均未失败。仍未完全关闭的内容只有真实密码管理器行为、跨浏览器人工覆盖，以及外部 ERP 测试数据质量核对；这些不应被描述为 DataPulse 产品缺陷已通过。

- DP-001 的代码修复和自动化验证已完成；真实密码管理器行为仍建议由 BB-004 做抽样确认。
- Firefox/WebKit 以及真实密码管理器 autofill 仍未完成；BB-005/007/011 的部分高成本人工边界仍待补充。
- ISS-016 仍等待 ERP 数据源所有者确认，不修改 DataPulse 业务代码或测试数据。

## ISS-004：DP-001 尚未完成真实密码管理器验证

- 类型：测试覆盖缺口
- 优先级：P1
- 状态：已解决代码问题并完成自动化验证；真实密码管理器行为作为残余抽样风险
- 原因：DP-001 的现象依赖浏览器保存的管理员凭据和真实 autofill 行为；本轮仅执行自动化测试，未启动带专用凭据的人工浏览器会话。
- 已有自动化覆盖：`apps/web/src/features/datasources/datasource-form.test.ts` 检查新建/编辑表单的 `autocomplete` 属性和密码字段为空，但 happy-dom 不会模拟 Chrome/密码管理器的实际填充决策。
- 验证用例：计划中的 BB-004，需在 Chromium 中保存专用测试管理员凭据后检查 PostgreSQL、MySQL/MariaDB 和 HTTP API 表单，并记录 DOM、Network 和截图证据。
- 安全限制：不得使用真实管理员密码、真实数据库凭据或生产站点；验证结束必须清除浏览器凭据和站点数据。

## ISS-005：Docker runtime 基础镜像下载阻塞构建

- 类型：环境阻塞
- 优先级：P0
- 状态：已修复并完成重试
- 影响范围：AUTO-E2E-004、AUTO-E2E-005
- 现象：首次构建时 `python:3.13-slim` 层下载长时间低速，构建进程手动中止并返回退出码 `130`。
- 证据：`AUTO-E2E-004-rerun.log`（首次阻塞）；`AUTO-E2E-004-final.log`、`AUTO-E2E-004-image-inspect.log`、`AUTO-E2E-005-final.log`（修复后）。
- 处理结果：从 `docker.m.daocloud.io/library/python:3.13-slim` 预拉取并复用同 digest 基础镜像后，原始 Dockerfile 构建、容器迁移、健康检查和 `/studio` 烟囱测试均退出码 `0`。

## ISS-006：无 key 或错误 key 的独立播放跳转管理员登录

- 类型：产品行为/安全 UX
- 优先级：P1
- 状态：已修复并完成自动化回归
- 现象：隔离的未登录播放上下文访问 `/play/{screen_id}` 或使用错误 display key 时，播放器 API 返回 401 后页面跳转到 `/studio/login`，没有展示预期的中性“无法播放此大屏”错误。
- 复现：使用 BB-009 已发布文本屏，分别打开无 key、`key=invalid`；观察最终 URL 和页面文案。
- 影响：公开播放链接失效时暴露管理员登录入口，无法向播放端提供中性错误反馈；有效 key 播放不受影响。
- 证据：`../blackbox-20260829/BB-009/BB-009-player-no-key.png`、`BB-009-player-wrong-key.png`。
- 处理结果：`apps/web/src/features/player/api.ts` 对独立播放请求设置 `suppressAuthExpiredEvent`，401 不再触发 Studio 全局登录跳转；播放器仍显示中性错误。
- 验证证据：`AUTO-UNIT-006-targeted.log`（播放器单元集合 59 passed）、`AUTO-E2E-001.log`（播放/E2E 14 passed）。真实无 key/错误 key 浏览器截图保留为修复前基线。

## ISS-007：编辑器窄视口产生水平溢出

- 类型：产品可用性/布局
- 优先级：P2
- 状态：已修复并完成自动化回归
- 现象：390×844 视口打开编辑器时 `scrollWidth=1200`、`clientWidth=390`，组件与图层、画布、属性面板横向排列在屏外。
- 复现：登录后打开 BB-014 编辑器，将 Chromium viewport 设为 390×844，检查滚动宽度和面板位置。
- 影响：窄窗口编辑工作流不可用；同视口播放页无溢出。
- 证据：`../blackbox-20260829/BB-014/BB-014-editor-narrow.png`。
- 处理结果：`StudioShell.vue` 在编辑器路由增加窄视口标记，`base.css` 在 600px 以下隐藏侧栏并将编辑器面板纵向排列，取消固定 1200px 最小宽度。
- 验证证据：`AUTO-E2E-001.log` 中窄视口编辑器测试通过；`AUTO-UNIT-006-targeted.log` 59 passed。Firefox/WebKit 仍未配置。

## ISS-008：发布确认弹窗不响应 Escape

- 类型：产品可用性/键盘交互
- 优先级：P2
- 状态：已修复并完成自动化回归
- 现象：打开“确认发布大屏”弹窗后按 Escape，弹窗仍存在。
- 复现：已登录编辑器点击“发布”，按 Escape，检查弹窗 heading 是否仍存在。
- 影响：键盘用户无法按预期取消高风险发布确认；仍可点击“取消”。
- 证据：`../blackbox-20260829/BB-014/BB-014-publish-dialog-escape.png`。
- 处理结果：`ScreenEditorView.vue` 注册并清理 Escape 键监听，发布进行中不允许关闭，其他状态可关闭确认弹窗。
- 验证证据：`AUTO-E2E-001.log` 中发布弹窗 Escape 回归通过；`AUTO-UNIT-006-targeted.log` 59 passed。焦点返回仍需人工补充。

## ISS-009：坏 JSON 上传未映射稳定错误

- 类型：后端异常处理/错误契约
- 优先级：P1
- 状态：已修复并完成自动化回归
- 现象：上传 malformed `.json` 时 `POST /api/admin/files` 返回 500，响应无 `X-Request-ID`；页面只显示“请求失败，请稍后重试”，后端日志出现未处理 `JSONDecodeError`。
- 复现：登录后打开文件数据集导入，上传 BB-006 的坏 JSON fixture。
- 影响：用户无法定位输入错误；500 堆栈污染服务日志，违反稳定错误 envelope/request ID 约定。
- 证据：`../blackbox-20260829/BB-006/BB-006-bad-json.png`、`bad-json-response.txt`。
- 处理结果：`filedata/parsers.py` 将 JSONDecodeError/UnicodeDecodeError 转换为 `FILE_PARSE_INVALID`；API 返回 422 和稳定 request ID。
- 验证证据：`apps/server/tests/filedata/test_api.py` 新增坏 JSON 回归；`AUTO-UNIT-004.log`、`AUTO-INT-001.log` 和全量后端测试通过。

## ISS-010：坏 JSON 上传失败后遗留未登记存储文件

- 类型：数据一致性/失败清理
- 优先级：P1
- 状态：已修复并完成自动化回归
- 现象：ISS-009 的 500 响应后，临时 `files/<orphan-id>/source.json` 存在，但 `file_asset` 表没有对应 id，文件列表不显示该资产。
- 复现：同 ISS-009 上传坏 JSON，检查临时 files 目录和 `file_asset` 元数据表。
- 影响：磁盘产生不可管理的孤儿文件，重复失败上传可能持续占用存储并破坏资产计数一致性。
- 证据：`../blackbox-20260829/BB-006/orphan-check.txt`、`orphan-source.json`。
- 处理结果：`filedata/service.py` 在解析或元数据创建失败时删除已保存文件，避免文件系统与 `file_asset` 元数据脱节。
- 验证证据：`apps/server/tests/filedata/test_api.py` 断言失败后 files 目录为空且资产列表为空；`AUTO-UNIT-004.log` 记录通过。

## ISS-011：AI 未配置时页面未显示配置状态或人工 SQL 入口

- 类型：产品可用性/错误降级
- 优先级：P1
- 状态：已修复并完成自动化回归
- 影响范围：BB-015；大屏 AI 生成和数据集 AI 分析入口。
- 现象：在 `DATAPULSE_AI_ENABLED=false` 的隔离实例中，`GET /api/admin/ai/status` 返回 `{"status":"unconfigured","model":null}`；大屏生成和数据集分析请求返回 503，错误 code 为 `AI_NOT_CONFIGURED`。两个页面只显示通用英文错误“The AI request could not be completed.”和 request ID，没有配置状态、可操作的降级说明或设计文档要求的人工 SQL 入口。
- 影响：管理员无法区分 AI 未启用、provider 故障和网络错误；默认关闭 AI 的部署缺少明确的人工分析路径。
- 复现：使用 `test-evidence/blackbox-20260829/BB-015/` 的临时实例，分别在大屏列表和数据集详情提交 AI 请求。
- 证据：`BB-015-status-response.txt`、`BB-015-screen-response.txt`、`BB-015-dataset-ai-error.png`、`BB-015-ai-not-configured.png`。
- 处理结果：AI 分析、AI 修改和 AI 生成对话框读取 `/api/admin/ai/status`，在未配置时显示明确中文状态；数据集详情提供 `#dataset-sql-editor` 人工 SQL 入口；后端错误 code 映射为中文稳定文案。
- 验证证据：`apps/web/src/features/ai/ai-panel.test.ts` 的未配置状态测试；`AUTO-E2E-001.log` 中 AI 分析/生成测试通过；未配置实例的原始响应仍保留为修复前基线。

## ISS-012：前端代理端口错误时登录页显示为账号登录失败

- 类型：环境中断下的错误映射/可观测性
- 优先级：P1
- 状态：已修复并完成自动化回归
- 影响范围：BB-019；管理员登录页在后端服务不可达时的错误提示。
- 现象：用户截图显示登录页已填入 `admin` 和密码并提示“登录失败，请稍后重试”。核对发现前端 `5173` 进程未设置 `VITE_API_PROXY_TARGET`，按 `apps/web/vite.config.ts` 默认代理到未监听的 `8000`；即使后端在 `8001` 恢复，`/api/auth/status` 仍返回 500。后端日志没有对应的 `POST /api/auth/login`，页面进入了 `LoginView.vue` 的非 `ApiError` 通用分支。
- 影响：开发服务端口配置错误被用户误解为凭据错误，无法区分代理故障和登录失败；该截图不能证明账号密码错误。
- 复现：使用 `pnpm --filter @datapulse/web dev --host 127.0.0.1 --port 5173` 且不设置 `VITE_API_PROXY_TARGET`，后端仅监听 `8001`，打开 `/studio/login` 并观察 `/api/auth/status` 500 与通用错误；设置 `VITE_API_PROXY_TARGET=http://127.0.0.1:8001` 后重启 Vite 可恢复。
- 证据：用户提供的登录失败截图；`../blackbox-20260829/BB-019/BB-019-service-health.txt`、`BB-019-server-recovery.log`。
- 当前恢复核对：Vite 已使用 `VITE_API_PROXY_TARGET=http://127.0.0.1:8001` 重启；隔离数据库的合成 `admin` 凭据已重置并撤销旧会话，`POST /api/auth/login` 返回 204、`GET /api/auth/session` 返回 200。该动作仅恢复本地测试环境，不代表默认端口配置或错误文案已完成产品修复；证据见 `../blackbox-20260829/BB-019/BB-019-login-after-reset.txt`。
- 处理结果：`LoginView.vue` 对 `HTTP_ERROR` 和非 ApiError 显示服务器/代理不可用提示；`auth.ts` 在状态探测遇到 5xx 时保持匿名状态，避免误判为凭据错误。Vite 实例已显式指向实际后端端口。
- 验证证据：`AUTO-UNIT-005-targeted.log`、`AUTO-E2E-001.log`；BB-019 恢复记录证明正确代理后登录请求可达。默认端口配置仍需部署环境确认。

## ISS-013：中文登录界面直接显示英文凭据错误

- 类型：产品可用性/本地化
- 优先级：P2
- 状态：已修复并完成自动化回归
- 影响范围：BB-020、BB-021；管理员登录页无效凭据错误展示。
- 现象：中文登录页在收到 401 `AUTH_INVALID_CREDENTIALS` 后直接显示后端英文文案 `The username or password is invalid.`；页面其他主要文案为中文。后端错误 code 仍统一区分用户名和密码，语义符合安全要求，但前端没有转换为中文用户提示。
- 影响：中文用户看到语言不一致的错误信息，降低可理解性和界面一致性；不影响认证安全边界。
- 复现：前端代理指向 `8001` 时，在 `/studio/login` 提交明确无效的测试账号/密码，观察 401 响应和页面文案。
- 证据：`../blackbox-20260829/BB-020/BB-020-user-login-401.png`、`../blackbox-20260829/BB-019/BB-019-after-recovery-invalid-credentials.json`、`../blackbox-20260829/BB-021/BB-021-auth-restart-observation.txt`、`../blackbox-20260829/BB-021/BB-021-login-invalid.png`。
- 处理结果：`LoginView.vue` 按 `AUTH_INVALID_CREDENTIALS`、`AUTH_RATE_LIMITED` 和网络错误映射中文提示，同时保留服务端 request ID 和字段错误。
- 验证证据：`AUTO-UNIT-005-targeted.log`、`AUTO-E2E-001.log`；BB-020/BB-021 的英文文案为修复前基线，后续真实浏览器中文文案仍可抽样确认。

## ISS-014：数据源空状态重复提供创建入口

- 类型：产品可用性/UI 冗余
- 优先级：P2
- 状态：已修复并完成自动化回归
- 影响范围：`/studio/datasources` 无数据源空状态。
- 现象：空状态同时显示可进入创建流程的加号和“新建数据源”文字按钮；两者都指向 `/studio/datasources/new`，操作能力重复。
- 证据：用户提供的 `../blackbox-20260829/` 外部截图路径 `/var/folders/vn/mfggccds6x1dy3d4pn48_2680000gn/T/codex-clipboard-92454e94-784b-4985-86b0-f90a7973e9c8.png`；代码位置为 `apps/web/src/features/datasources/DatasourceListView.vue` 空状态模板。
- 用户期望：只保留加号作为新建数据源入口，并保证加号仍可进入 `/studio/datasources/new`。
- 处理结果：`DatasourceListView.vue` 仅保留空状态加号入口，并在有数据源时显示顶部创建按钮；加号仍指向 `/studio/datasources/new`。
- 验证证据：`apps/web/src/features/datasources/datasource-list.test.ts`、`AUTO-UNIT-005-targeted.log`。

## ISS-015：数据源新建/编辑表单缺少测试连接入口

- 类型：产品需求/功能缺口
- 优先级：P1
- 状态：已修复并完成自动化回归
- 影响范围：`/studio/datasources/new` 和 `/studio/datasources/:id/edit` 表单。
- 现象：当前表单底部只有“取消”和“创建数据源/保存更改”，用户希望增加“测试连接”功能。现有 `apps/web/src/features/datasources/api.ts` 的 `testDatasource(datasourceId)` 与后端 `POST /api/admin/datasources/{datasource_id}/test` 只面向已保存数据源，不能直接验证尚未保存的表单配置。
- 影响：管理员在保存前无法确认新填写的连接配置；已保存数据源详情页也没有手动检查按钮，创建后会保持“连接状态：未检查、上次检查：尚未检查”，需要返回列表点击“测试”才会更新；新增按钮需要定义未保存配置请求契约、凭据处理、错误展示和重复点击行为。
- 证据：用户提供的截图 `/var/folders/vn/mfggccds6x1dy3d4pn48_2680000gn/T/codex-clipboard-7dac98f3-b705-420d-b6ea-4241f9b28ab1.png`、`/var/folders/vn/mfggccds6x1dy3d4pn48_2680000gn/T/codex-clipboard-f0864a1b-7b24-4b54-a7e1-90dd0e78af95.png`；代码位置为 `apps/web/src/features/datasources/DatasourceFormView.vue`、`apps/web/src/features/datasources/DatasourceDetailView.vue`、`apps/web/src/features/datasources/DatasourceListView.vue`、`apps/web/src/features/datasources/api.ts`、`apps/server/src/datapulse/datasource/api.py`。
- 处理结果：新增 `POST /api/admin/datasources/test` 临时配置测试接口；新建/编辑表单增加“测试连接”按钮，编辑时可复用已保存密文，测试请求不持久化配置或回显密码。
- 验证证据：`apps/server/tests/datasource/test_api.py`、`test_service.py`、`apps/web/src/features/datasources/datasource-form.test.ts`；`AUTO-INT-001.log`、`AUTO-UNIT-005-targeted.log`。

## ISS-017：AI 面板辅助文字与背景对比度不足

- 类型：产品可用性/无障碍视觉
- 优先级：P1
- 状态：已修复并完成自动化回归
- 影响范围：大屏编辑器右侧“AI 修改”“AI 分析”面板，以及 AI 生成大屏对话框。
- 现象：修复前面板使用半透明深色背景和浅灰/浅蓝辅助文字，说明、标签和命令列表与背景接近，截图中难以阅读。
- 证据：用户截图 `/var/folders/vn/mfggccds6x1dy3d4pn48_2680000gn/T/codex-clipboard-b4fd1d99-c492-4be5-bcea-54f81e426899.png`；代码位置为 `apps/web/src/features/ai/AiAnalysisPanel.vue`、`AiEditPanel.vue`、`AiScreenGeneratorDialog.vue`。
- 处理结果：AI 分析/修改面板改为不透明白底和深色边框；说明、占位、错误、命令和结果徽章改用高对比度文字；生成大屏对话框同步统一辅助文字、数据集区域和结果徽章配色。
- 验证证据：`AUTO-E2E-006.log`（AI 分析/编辑 E2E 计算样式断言、2 个 AI 单元测试文件/3 tests passed、Web 构建退出码 0）。

## BB-022 复现核对：从数据源创建数据集（非新增问题）

- 执行日期：2026-08-31；状态：已执行观察。
- 用户反馈“无法从数据源创建数据集”后，按正确入口“数据集 → 从数据源创建 → 数据源 → SQL 调试 → 保存为数据集”复核。数据源详情/Schema 请求返回 200，查询请求返回 200，保存数据集请求返回 201，并正常跳转数据集详情。
- 用户确认此前是找错入口。本次未复现产品故障，因此未创建新的 ISS 编号，也未修改业务代码、测试代码或配置。
- 证据：`../blackbox-20260829/BB-022/BB-022-observation.txt`、`../blackbox-20260829/BB-022/BB-022-detail-loaded.png`、`../blackbox-20260829/BB-022/BB-022-save-result.png`、`../blackbox-20260829/BB-022/BB-022-products-save.png`。

## ISS-016：ERP 测试数据中文字段存在双重编码（外部数据质量待确认）

- 类型：测试数据质量/数据一致性风险；优先级：P1；状态：待数据源所有者确认，未认定为 DataPulse 产品缺陷。
- 影响范围：BB-022 中 ERP `products.product_name` 查询结果及由该查询生成的数据集预览。
- 现象：SQL 查询返回的中文名称显示为 UTF-8 乱码；`HEX(product_name)` 显示数据库存储字节本身已是乱码字符串的 UTF-8 编码，连接字符集 `client/connection/results` 均为 `utf8mb4`。现有证据更支持测试数据写入源库时发生双重编码，不能仅凭页面结果归因于 DataPulse。
- 复现：在 BB-022 的 ERP 数据源执行 `SELECT product_name, HEX(product_name), @@character_set_client, @@character_set_connection, @@character_set_results FROM products LIMIT 1`，保存前后均观察到相同编码结果。
- 证据：`../blackbox-20260829/BB-022/BB-022-observation.txt`、`../blackbox-20260829/BB-022/BB-022-products-save.png`。
- 后续动作：由数据源所有者用数据库客户端核对原始值和导入脚本编码；确认源数据正确后，再复测 DataPulse 查询和数据集预览。当前不修改业务代码或测试数据源。
