# DataPulse `E3` Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复提交 `699b63f` 的质量门禁、AI 分析与整屏生成、文件数据集预览维护和 `E3` 发布验收问题。

**工程里程碑：** `E3` 文件数据与 AI 的修复验收。这里的“阶段三”是工程交付编号，产品层面仍属于第一阶段收口和第二阶段准备工作。

**Architecture:** 在现有 FastAPI/Vue 单体边界内做向后兼容扩展：AI 分析一次返回结论、图表规范和预览；屏幕创建可携带初始文档并原子写入；未落库屏幕通过管理员文档查询接口复用运行时；文件资产通过独立预览接口提供 Sheet 和样例。所有行为先用失败测试固定，再做最小实现。

**Tech Stack:** Python 3.13、FastAPI、Pydantic v2、SQLAlchemy、DuckDB、openpyxl、PyArrow、Vue 3、TypeScript、Vitest、Playwright、pnpm、uv、Ruff。

## Global Constraints

- AI 结果只能创建或修改草稿，任何路径都不能调用发布接口。
- 管理接口继续依赖管理员 Session 和 CSRF。
- 文件查询继续使用 DuckDB；外部数据库继续使用原生连接器。
- 保持普通空白屏幕创建、SQL 数据集编辑、`/api/admin/ai/chart`、独立播放和嵌入接口兼容。
- AI 上下文最多 100 行和 50 个字段；不得向前端或日志返回 API Key、连接密码、文件绝对路径。
- 不引入任务队列、临时屏幕记录、多用户权限或发布历史。
- 每个生产行为先写失败测试并确认按预期失败，再实现最小代码。

---

### Task 1: 恢复 Python 测试与 Ruff 门禁

**Files:**
- Create: `apps/server/tests/ai/__init__.py`
- Create: `apps/server/tests/filedata/__init__.py`
- Modify: `apps/server/src/datapulse/ai/gateway.py`
- Modify: `apps/server/src/datapulse/ai/screen_generator.py`
- Modify: `apps/server/src/datapulse/ai/service.py`
- Modify: `apps/server/src/datapulse/lifespan.py`
- Modify: `apps/server/tests/ai/test_api.py`
- Modify: `apps/server/tests/ai/test_chart_generation.py`
- Modify: `apps/server/tests/ai/test_context.py`
- Modify: `apps/server/tests/ai/test_screen_generator.py`
- Modify: `apps/server/tests/ai/test_service.py`

**Interfaces:**
- Produces: pytest 可唯一导入的 `tests.ai.*` 和 `tests.filedata.*` 模块。

- [ ] **Step 1: 复现测试收集失败**

Run:

```bash
uv run --package datapulse-server pytest apps/server/tests/ai/test_api.py apps/server/tests/filedata/test_api.py --collect-only -q
```

Expected: FAIL，出现 `import file mismatch`，两个文件都被识别为 `test_api`。

- [ ] **Step 2: 建立测试包边界**

创建两个空 `__init__.py`，使模块名分别为 `tests.ai.test_api` 和 `tests.filedata.test_api`。

- [ ] **Step 3: 验证收集通过**

Run:

```bash
uv run --package datapulse-server pytest apps/server/tests/ai apps/server/tests/filedata --collect-only -q
```

Expected: PASS，无模块导入冲突。

- [ ] **Step 4: 修复本阶段 Ruff 问题**

仅做换行、导入排序、重复导入和 Python 3.13 类型标注修正，不改变运行行为。

- [ ] **Step 5: 验证 Ruff**

Run:

```bash
changed_py=($(git diff --name-only 31c7291 -- '*.py'))
uv run --package datapulse-server ruff check "${changed_py[@]}"
```

Expected: PASS。

- [ ] **Step 6: 提交门禁修复**

```bash
git add apps/server/tests/ai apps/server/tests/filedata/__init__.py apps/server/src/datapulse/ai apps/server/src/datapulse/lifespan.py
git commit -m "fix(test): restore phase three quality gates"
```

### Task 2: 单次 AI 分析与前置配置校验

**Files:**
- Modify: `apps/server/src/datapulse/contracts/ai.py`
- Modify: `apps/server/src/datapulse/ai/gateway.py`
- Modify: `apps/server/src/datapulse/ai/context.py`
- Modify: `apps/server/src/datapulse/ai/service.py`
- Modify: `apps/server/tests/ai/test_gateway.py`
- Modify: `apps/server/tests/ai/test_service.py`
- Modify: `apps/server/tests/ai/test_context.py`
- Modify: `apps/server/tests/contracts/test_ai.py`
- Modify generated schemas/types through `pnpm generate:contracts`

**Interfaces:**
- Produces: `AiGateway.ensure_configured() -> None`。
- Produces: `AiAnalysisResponse.preview: QueryResult`。
- Consumes: existing `AiGatewayError("AI_NOT_CONFIGURED", ...)` and `_validate_and_preview`.

- [ ] **Step 1: 写 AI 未配置不读取数据的失败测试**

在 `test_service.py` 使用记录调用次数的 fake context：

```python
with pytest.raises(AiGatewayError) as error:
    await service.analyze(request, request_id="req-1")
assert error.value.code == "AI_NOT_CONFIGURED"
assert context_service.calls == []
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
uv run --package datapulse-server pytest apps/server/tests/ai/test_service.py -k unconfigured -q
```

Expected: FAIL，当前上下文服务已被调用。

- [ ] **Step 3: 实现网关前置断言**

在 `AiGateway` 增加：

```python
def ensure_configured(self) -> None:
    if not self._is_configured() or self._client is None:
        raise AiGatewayError("AI_NOT_CONFIGURED", "AI is not configured.")
```

三个 AI 服务入口在读取数据前调用它，`complete_json` 复用同一断言。

- [ ] **Step 4: 写数据集错误转换失败测试**

覆盖 `analyze` 中不存在的数据集和上下文中的 `FileAssetNotFound`，断言分别成为 `AI_DATASET_INVALID`，而不是泄漏 repository 异常。

- [ ] **Step 5: 运行错误转换测试确认失败**

Run:

```bash
uv run --package datapulse-server pytest apps/server/tests/ai/test_service.py -k "missing or invalid" -q
```

Expected: FAIL，当前 `DatasetContextService.build` 异常直接上抛。

- [ ] **Step 6: 先校验数据集并统一上下文异常**

`analyze` 先通过 `_dataset` 加载请求数据集，再构建上下文；`DatasetContextService` 或 AI 服务边界把数据集、数据源和文件资产缺失翻译为现有 AI 错误码。

- [ ] **Step 7: 写分析响应包含预览的失败测试**

```python
response = await service.analyze(request, request_id="req-2")
assert response.preview.rows == (("2026-01", 100),)
```

Expected: 当前 `AiAnalysisResponse` 没有 `preview`。

- [ ] **Step 8: 返回实际执行的预览**

保存 `_validate_and_preview` 返回值，并构造带 `preview` 的响应；更新契约测试和 fake 响应。

- [ ] **Step 9: 增加请求资源上限**

测试并实现：分析/整屏数据集数量最多 8 个、问题最多 4000 字符、画布宽高最大 7680。超限由 Pydantic 返回 `REQUEST_VALIDATION_ERROR`。

- [ ] **Step 10: 生成契约并验证后端**

```bash
pnpm generate:contracts
uv run --package datapulse-server pytest apps/server/tests/ai apps/server/tests/contracts/test_ai.py -q
pnpm check:contracts
```

Expected: PASS。

- [ ] **Step 11: 提交 AI 服务修复**

```bash
git add apps/server/src/datapulse/ai apps/server/src/datapulse/contracts apps/server/tests/ai apps/server/tests/contracts packages/schema apps/web/src/contracts
git commit -m "fix(ai): validate configuration and return one analysis preview"
```

### Task 3: 原子创建屏幕草稿

**Files:**
- Modify: `apps/server/src/datapulse/screen/models.py`
- Modify: `apps/server/src/datapulse/screen/service.py`
- Modify: `apps/server/tests/screen/test_service.py`
- Modify: `apps/server/tests/screen/test_api.py`
- Modify: `apps/web/src/features/screens/types.ts`
- Modify: `apps/web/src/features/screens/screen-list.test.ts`
- Modify: `apps/web/src/features/screens/ScreenListView.vue`

**Interfaces:**
- Produces: `ScreenCreate.draft_document: DashboardDocument | None = None`。
- Consumes: existing atomic `ScreenRepository.create(name, document, ...)`.

- [ ] **Step 1: 写服务层失败测试**

构造带组件的 `ScreenCreate`，断言 repository 只收到一次 `create`，且文档就是传入草稿；普通创建仍收到 `_empty_document()`。

- [ ] **Step 2: 运行服务测试确认失败**

```bash
uv run --package datapulse-server pytest apps/server/tests/screen/test_service.py -k initial_document -q
```

Expected: FAIL，`ScreenCreate` 拒绝 `draft_document`。

- [ ] **Step 3: 实现可选初始文档**

`ScreenService.create` 使用：

```python
document = data.draft_document or _empty_document()
return await self._repository.create(data.name, document, ...)
```

- [ ] **Step 4: 写 API 和前端失败测试**

后端断言一次 POST 可返回带组件草稿；前端断言 AI 确认只出现一个 `/api/admin/screens` POST，不再出现 PATCH。

- [ ] **Step 5: 运行测试确认失败**

```bash
uv run --package datapulse-server pytest apps/server/tests/screen/test_api.py -k initial_document -q
pnpm --filter @datapulse/web exec vitest run src/features/screens/screen-list.test.ts
```

Expected: 前端测试看到 PATCH 或 POST 请求体缺少 `draft_document`。

- [ ] **Step 6: 前端改为一次创建请求**

扩展 `ScreenCreatePayload`，`submitAiCreate` 将 `draft_document` 与名称一起传给 `createScreen`，成功后直接跳转。

- [ ] **Step 7: 验证屏幕相关测试并提交**

```bash
uv run --package datapulse-server pytest apps/server/tests/screen/test_service.py apps/server/tests/screen/test_api.py -q
pnpm --filter @datapulse/web exec vitest run src/features/screens/screen-list.test.ts
git add apps/server/src/datapulse/screen apps/server/tests/screen apps/web/src/features/screens
git commit -m "fix(screen): create generated drafts atomically"
```

### Task 4: 未落库屏幕运行时预览

**Files:**
- Modify: `apps/server/src/datapulse/screen/runtime.py`
- Modify: `apps/server/src/datapulse/screen/runtime_api.py`
- Modify: `apps/server/tests/screen/test_runtime.py`
- Modify: `apps/server/tests/screen/test_runtime_api.py`
- Modify: `apps/web/src/features/screens/api.ts`
- Create: `apps/web/src/features/ai/ScreenDraftPreview.vue`
- Modify: `apps/web/src/features/ai/AiScreenGeneratorDialog.vue`
- Modify: `apps/web/src/features/screens/screen-list.test.ts`

**Interfaces:**
- Produces: `ScreenDocumentQueryRequest(document, component_id, parameters)`。
- Produces: `ScreenRuntimeService.query_document_component(data, request_id) -> QueryResult`。
- Produces: `POST /api/admin/screens/query-document`。
- Produces: `queryScreenDocument(document, componentId, parameters, signal?)`。

- [ ] **Step 1: 写运行时服务失败测试**

使用已有 SQL/file fake，直接传 `DashboardDocument`，断言无需 repository screen ID 即可执行组件查询，并继续拒绝未知组件、非法字段和参数。

- [ ] **Step 2: 运行确认失败**

```bash
uv run --package datapulse-server pytest apps/server/tests/screen/test_runtime.py -k document_component -q
```

Expected: FAIL，方法不存在。

- [ ] **Step 3: 提取文档查询核心**

移除 `_query` 未使用的 `screen` 参数，让已保存草稿、已发布文档和未落库文档都调用同一私有实现；新增公开 `query_document_component`。

- [ ] **Step 4: 写管理员 API 失败测试**

断言未登录为 401、缺 CSRF 为 403、合法文档返回 200、非法绑定返回稳定 422。

- [ ] **Step 5: 实现 `/query-document`**

路由接收 `ScreenDocumentQueryRequest`，复用 `_raise_runtime_error`，trigger 使用 `screen-document-preview`。

- [ ] **Step 6: 写前端可视化预览失败测试**

生成整屏后断言对话框存在 `.screen-runtime`，每个数据组件调用 `/api/admin/screens/query-document`，取消前没有创建或发布请求。

- [ ] **Step 7: 实现 `ScreenDraftPreview`**

组件使用 `ScreenRuntime`、`loadPreviewAsset` 和 `queryScreenDocument`；外层按可用宽度等比缩放，预览模式固定为 `preview`。

- [ ] **Step 8: 验证并提交**

```bash
uv run --package datapulse-server pytest apps/server/tests/screen/test_runtime.py apps/server/tests/screen/test_runtime_api.py -q
pnpm --filter @datapulse/web exec vitest run src/features/screens/screen-list.test.ts
git add apps/server/src/datapulse/screen apps/server/tests/screen apps/web/src/features/ai apps/web/src/features/screens
git commit -m "feat(studio): preview generated screens before creation"
```

### Task 5: 前端单次 AI 分析与旧结果清理

**Files:**
- Modify: `apps/web/src/features/ai/types.ts`
- Modify: `apps/web/src/features/ai/AiAnalysisPanel.vue`
- Modify: `apps/web/src/features/ai/ai-panel.test.ts`

**Interfaces:**
- Consumes: `AiAnalysisResponse.preview` and `AiAnalysisResponse.chart_spec`。
- Produces: one `/api/admin/ai/analyze` request per submit.

- [ ] **Step 1: 改写失败测试**

测试只 mock `/analyze`，响应包含 `preview`；断言没有 `/chart` 请求。再生成一次并让第二次失败，断言旧结论、旧卡片和应用按钮消失。

- [ ] **Step 2: 运行确认失败**

```bash
pnpm --filter @datapulse/web exec vitest run src/features/ai/ai-panel.test.ts
```

Expected: FAIL，当前仍请求 `/chart` 且保留旧结果。

- [ ] **Step 3: 实现单请求渲染**

删除 `generateChart` 调用；提交开始以及问题/数据集变化时设置 `analysis = null`、`chart = null`。用分析响应的 `chart_spec` 和 `preview` 构造 `ChartSuggestionCard` 所需数据。

- [ ] **Step 4: 验证并提交**

```bash
pnpm --filter @datapulse/web exec vitest run src/features/ai/ai-panel.test.ts src/features/screens/editor/store.test.ts
git add apps/web/src/features/ai
git commit -m "fix(studio): use one AI analysis request"
```

### Task 6: 文件资产 Sheet 与样例预览 API

**Files:**
- Modify: `apps/server/src/datapulse/contracts/filedata.py`
- Modify: `apps/server/src/datapulse/filedata/parsers.py`
- Modify: `apps/server/src/datapulse/filedata/service.py`
- Modify: `apps/server/src/datapulse/filedata/api.py`
- Modify: `apps/server/tests/filedata/test_parsers.py`
- Modify: `apps/server/tests/filedata/test_api.py`
- Modify: `apps/server/tests/contracts/test_filedata.py`
- Modify: `apps/web/src/features/files/types.ts`
- Modify: `apps/web/src/features/files/api.ts`

**Interfaces:**
- Produces: `FilePreviewResponse(format, sheet_names, selected_sheet, result)`。
- Produces: `GET /api/admin/files/{asset_id}/preview?sheet_name=...`。
- Produces: `previewFileAsset(assetId, sheetName?, signal?)`。

- [ ] **Step 1: 写双 Sheet 解析失败测试**

创建包含 `Summary`、`Detail` 的内存 Excel fixture，断言 `excel_sheet_names(path)` 保持 workbook 顺序，按 Sheet 解析返回不同字段和行。

- [ ] **Step 2: 运行确认失败**

```bash
uv run --package datapulse-server pytest apps/server/tests/filedata/test_parsers.py -k sheet_names -q
```

Expected: FAIL，sheet 列表函数不存在。

- [ ] **Step 3: 实现 Sheet 元数据与文件预览服务**

Excel 在后台线程只读加载 workbook 名称；非 Excel 返回空列表。预览服务限制最多 100 行并把 `ParsedFile.sample_rows` 转成统一 `QueryResult`。

- [ ] **Step 4: 写 API 失败测试**

覆盖 CSV、Excel 默认 Sheet、指定 Sheet、不存在 Sheet、文件不存在和管理员/CSRF 边界，断言稳定错误码。

- [ ] **Step 5: 实现预览路由和前端 API 类型**

GET 预览不修改状态，因此只要求管理员 Session，不要求 CSRF；`sheet_name` 使用查询参数并经过 `NonBlankStr` 等价校验。

- [ ] **Step 6: 验证并提交**

```bash
uv run --package datapulse-server pytest apps/server/tests/filedata apps/server/tests/contracts/test_filedata.py -q
git add apps/server/src/datapulse/filedata apps/server/src/datapulse/contracts/filedata.py apps/server/tests/filedata apps/server/tests/contracts/test_filedata.py apps/web/src/features/files
git commit -m "feat(filedata): expose sheet-aware file previews"
```

### Task 7: 文件导入预览、维护与清理界面

**Files:**
- Modify: `apps/server/src/datapulse/dataset/service.py`
- Modify: `apps/server/src/datapulse/dataset/api.py`
- Modify: `apps/server/tests/dataset/test_api.py`
- Modify: `apps/server/tests/dataset/test_service.py`
- Modify: `apps/web/src/features/datasets/api.ts`
- Modify: `apps/web/src/features/datasets/FileDatasetCreateView.vue`
- Modify: `apps/web/src/features/datasets/DatasetDetailView.vue`
- Modify: `apps/web/src/features/datasets/datasets.test.ts`
- Modify: `apps/web/src/features/files/api.ts`

**Interfaces:**
- Produces: file dataset `PATCH` supporting name/max_rows/timeout_seconds while rejecting SQL/parameters.
- Produces: `deleteDataset(datasetId)` and `deleteFileAsset(assetId)`.
- Consumes: `FilePreviewResponse` and existing `QueryResultTable`.

- [ ] **Step 1: 写文件数据集更新失败测试**

断言 file dataset 可改名、最大行数和超时并重新解析字段；携带 `sql` 或 `parameters` 返回稳定 `DATASET_DEFINITION_INVALID`。

- [ ] **Step 2: 运行确认失败**

```bash
uv run --package datapulse-server pytest apps/server/tests/dataset -k file_update -q
```

Expected: FAIL，当前服务抛出 `Only SQL datasets can be edited`。

- [ ] **Step 3: 实现文件数据集安全更新**

按 query 类型分支：SQL 保持原逻辑；FileQuery 禁止 SQL/parameters，重新解析当前 asset/sheet，并更新名称、字段、max_rows 和 timeout。

- [ ] **Step 4: 写文件创建页面失败测试**

断言上传后显示 `QueryResultTable`；Excel 显示服务端 Sheet 下拉框；切换 Sheet 发新预览请求；删除未引用资产成功并从列表移除。

- [ ] **Step 5: 实现文件创建页面**

上传或选择 asset 后调用 preview；CSV/JSON/Parquet 直接显示样例，Excel 先选择默认 Sheet。错误使用 `InlineNotice`，预览加载支持 AbortController 防止旧响应覆盖新选择。

- [ ] **Step 6: 写详情页维护失败测试**

文件详情允许修改名称/限制并保存；删除要求 `window.confirm`，成功返回数据集列表；SQL 详情行为不变。

- [ ] **Step 7: 实现维护 API 与界面**

增加 `deleteDataset`、`deleteFileAsset`，文件详情复用现有保存状态和错误展示；删除数据集不自动删 asset。

- [ ] **Step 8: 验证并提交**

```bash
uv run --package datapulse-server pytest apps/server/tests/dataset -q
pnpm --filter @datapulse/web exec vitest run src/features/datasets/datasets.test.ts
git add apps/server/src/datapulse/dataset apps/server/tests/dataset apps/web/src/features/datasets apps/web/src/features/files
git commit -m "feat(studio): complete file dataset preview and maintenance"
```

### Task 8: 确定性 E2E、文档和完整门禁

**Files:**
- Create: `apps/web/e2e/ai-analysis.spec.ts`
- Create: `apps/web/e2e/ai-screen-generation.spec.ts`
- Create: `apps/web/e2e/fixtures/file-dataset-zh.csv`
- Create: `apps/web/e2e/fixtures/file-dataset.xlsx`
- Create: `apps/web/e2e/fixtures/file-dataset.json`
- Create: `apps/web/e2e/fixtures/file-dataset.parquet`
- Modify: `tools/run_e2e.py`
- Modify: `apps/web/e2e/file-dataset.spec.ts`
- Modify: `apps/server/tests/test_lifespan.py`
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `package.json`

**Interfaces:**
- Produces: E2E 期间启动的本地 fake OpenAI-compatible `/chat/completions` 服务。
- Produces: fake 模式 `valid-analysis`、`valid-screen`、`invalid-field`、`malformed-json`、`timeout`。

- [ ] **Step 1: 写 fake AI 网关测试**

在 E2E runner 测试或轻量自检中启动 fake 服务，使用 `httpx` 请求每种模式并断言 JSON、超时和 malformed 行为确定。

- [ ] **Step 2: 实现 fake 服务并注入 E2E 环境**

runner 为服务器设置 `DATAPULSE_AI_ENABLED=true`、本地 base URL、固定假 key/model；fake 服务只绑定随机 `127.0.0.1` 端口，测试结束后关闭。

- [ ] **Step 3: 编写 AI 分析 E2E**

覆盖状态、一次分析、图表预览、应用到组件、刷新保留、未配置/超时/非法输出，并监听所有请求断言没有 `/publish`。

- [ ] **Step 4: 编写 AI 整屏 E2E**

覆盖真实预览、取消不创建、确认后原子创建并进入编辑器、刷新保留、非法组件和越权数据集不落库，断言没有 PATCH 半成品流程和 publish。

- [ ] **Step 5: 扩充文件 E2E**

fixture 通过受控脚本生成 Excel/Parquet；E2E 覆盖中文 CSV、双 Sheet Excel、JSON、Parquet、改名、删除和引用保护。DOM 断言优先使用 role/label，不依赖 CSS 类。

- [ ] **Step 6: 更新生命周期测试和文档**

测试 AI gateway 启动/关闭；README 写明 DuckDB 只处理文件数据、支持格式、配置变量、上下文限制和第三方模型数据披露风险；删除第 25 行过期描述。

- [ ] **Step 7: 执行完整验证**

```bash
pnpm check:contracts
pnpm test
pnpm typecheck
pnpm build
uv run --package datapulse-server pytest -m "not integration"
uv run --package datapulse-server ruff check apps/server tools
pnpm test:e2e
pnpm test:integration
git diff --check
git status --short --branch
```

Expected: 本地依赖测试全部通过；PostgreSQL/MySQL 未配置时按既有标记跳过；工作区只包含本计划预期变更。

- [ ] **Step 8: 提交发布门禁**

```bash
git add apps/web/e2e apps/server/tests/test_lifespan.py tools/run_e2e.py .env.example README.md package.json
git commit -m "test: complete phase three release gates"
```

## Final Review Checklist

- [ ] `git log 699b63f..HEAD --oneline` 只包含设计和上述修复提交。
- [ ] 普通新建大屏仍创建空白文档，AI 新建只发一次创建请求。
- [ ] 所有 AI 前端流程没有 publish 请求。
- [ ] AI 未配置路径没有 dataset/data source/file query 调用。
- [ ] 一次分析只有一个模型请求和一套上下文/预览链路。
- [ ] 文件预览不返回绝对路径，Sheet/样例最多遵守服务端上限。
- [ ] README 与 `.env.example` 和实际 Settings 字段一致。
