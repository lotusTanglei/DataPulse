# `E3` 文件数据与 AI 分析实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变外部数据库连接器和设计时已有九类组件协议的前提下，交付文件数据集、DuckDB 查询、AI 数据分析、自然语言生成 `ChartSpec` 和完整大屏草稿生成。组件注册表后续已在产品第二阶段扩展为当前 21 类。

**工程里程碑：** `E3` 文件数据与 AI。它支撑产品第一阶段的 AI 创建入口和第二阶段的数据理解基础；产品第三阶段现定义为完整数字人播报，因此本计划不属于产品第三阶段。

**Architecture:** 文件上传形成受控 `FileAssetRecord`，文件数据集使用现有 `DatasetDefinition.query` 的 `FileQuery` 分支；SQL 数据集继续走 SQLite/PostgreSQL/MySQL 原生连接器，文件数据集走只读 `FileDatasetQueryService`。AI 通过 OpenAI 兼容 HTTP 的 `AiGateway` 获取结构化 `AnalysisPlan`、`ChartSpec` 或受限 `DashboardDocument` 草稿，服务端重新校验后交给现有查询编译器、编辑器 Store 和发布流程。

**Tech Stack:** Python 3.13、FastAPI、Pydantic v2、SQLAlchemy/Alembic、DuckDB Python API、httpx、Vue 3、TypeScript、Vitest、pytest、Playwright、现有 `ChartSpec` / `DashboardDocument` 协议。

## Global Constraints

- 外部 SQLite、PostgreSQL、MySQL/MariaDB 必须继续使用现有原生连接器，DuckDB 不得代理外部数据库。
- 只允许管理员上传文件、创建文件数据集和调用 AI 管理 API；发布播放和嵌入鉴权不变。
- 允许的文件格式只有 CSV、Excel、JSON、Parquet；默认单文件 100 MB、单次解析 5,000 行。
- DuckDB 查询必须使用服务端受控绝对路径、只读连接、最多 2 线程、512 MB 内存和 30 秒超时。
- AI 不得执行任意 SQL/Python/JavaScript，不得返回数据库密码、文件绝对路径或完整表数据。
- AI 生成结果必须先通过 `AnalysisPlan` / `ChartSpec` / `DashboardDocument` Pydantic 校验和字段白名单校验，用户确认后才能创建或修改草稿，不能自动发布。
- 本 `E3` 工程里程碑不新增大屏组件、不实现设备管理、播放列表、插件 SDK、模板市场、查询缓存和后台调度；完整数字人播报属于后续产品第三阶段。
- 每个任务都先写失败测试，再写最小实现，任务结束提交一个可独立回滚的 commit。

## 文件结构与边界

- `apps/server/src/datapulse/filedata/`: 文件校验、存储、解析、DuckDB 查询，不依赖 Web 页面。
- `apps/server/src/datapulse/dataset/`: 扩展现有数据集模型、服务和 API，使 SQL 与 FileQuery 使用统一响应。
- `apps/server/src/datapulse/ai/`: AI 网关、上下文裁剪、分析服务、草稿生成器和 API；不直接修改 ScreenRecord。
- `apps/server/src/datapulse/contracts/`: 扩展文件上传、文件数据集和 AI 请求/响应模型；通过现有 schema 生成流程同步 TypeScript 类型。
- `apps/web/src/features/file-datasets/`: 文件上传、解析结果和数据集创建页面。
- `apps/web/src/features/ai/`: AI 分析面板、图表建议预览、完整草稿预览和确认写入草稿的交互。
- `apps/web/src/features/datasets/` 与 `apps/web/src/features/screens/editor/`: 只增加调用和展示，不复制查询或组件逻辑。

---

### Task 1: 固化 E3 契约与运行参数

**Files:**
- Modify: `apps/server/src/datapulse/contracts/dataset.py`
- Modify: `apps/server/src/datapulse/contracts/ai.py`
- Create: `apps/server/src/datapulse/contracts/filedata.py`
- Modify: `apps/server/src/datapulse/dataset/models.py`
- Create: `apps/server/tests/contracts/test_filedata.py`
- Modify: `apps/server/tests/contracts/test_ai.py`
- Modify: `apps/server/pyproject.toml`
- Modify: `apps/server/src/datapulse/settings.py`
- Modify: `packages/schema/schemas/dataset-definition.schema.json`
- Modify: `packages/schema/schemas/analysis-plan.schema.json`

**Interfaces:**
- `FileFormat = Literal["csv", "excel", "json", "parquet"]`。
- `FileAssetResponse(id, original_name, format, mime_type, size_bytes, sha256, row_count, fields, created_at)`。
- `FileDatasetCreate(name, file_asset_id, sheet_name=None, max_rows=5000, timeout_seconds=30)`。
- `AiAnalysisRequest(question, dataset_ids, mode: Literal["analysis", "chart"] = "analysis")`。
- `AiAnalysisResponse(plan: AnalysisPlan, narrative: str, chart_spec: ChartSpec | None, warnings: tuple[str, ...])`。
- `Settings.file_max_bytes=100*1024*1024`, `file_max_rows=5000`, `duckdb_threads=2`, `duckdb_memory_limit="512MB"`, `duckdb_timeout_seconds=30`。

- [ ] **Step 1: 写契约失败测试**

  在 `test_filedata.py` 中验证四种文件格式、大小正数、文件 ID 非空、Sheet 名可选；验证非法格式、负行数和空文件名被拒绝。在 `test_ai.py` 中验证 AI 请求必须有非空问题和至少一个数据集。

- [ ] **Step 2: 运行契约测试确认失败**

  Run: `uv run --package datapulse-server pytest apps/server/tests/contracts/test_filedata.py apps/server/tests/contracts/test_ai.py -q`

  Expected: 新增模型尚未存在或校验断言失败。

- [ ] **Step 3: 实现模型和配置**

  保持现有 `FileQuery` 和 `AnalysisPlan` 的版本兼容；将 `DatasetResponse.data_source_id` 改为 `str | None`，让文件数据集不依赖外部 `DataSourceRecord`。将配置字段加入 `.env.example`，并为每个值设置 Pydantic 范围校验。

- [ ] **Step 4: 生成并校验共享 Schema**

  Run: `pnpm generate:contracts && pnpm check:contracts && uv run --package datapulse-server pytest apps/server/tests/contracts -q`

  Expected: Python 模型、JSON Schema 和 TypeScript 类型一致，全部契约测试通过。

- [ ] **Step 5: 提交**

  ```bash
  git add apps/server/src/datapulse/contracts apps/server/src/datapulse/dataset/models.py apps/server/src/datapulse/settings.py apps/server/tests/contracts packages/schema .env.example
  git commit -m "feat: define phase three file and ai contracts"
  ```

### Task 2: 建立文件资产元数据与安全存储

**Files:**
- Create: `apps/server/migrations/versions/0007_file_datasets.py`
- Modify: `apps/server/src/datapulse/metadata/models.py`
- Create: `apps/server/src/datapulse/filedata/models.py`
- Create: `apps/server/src/datapulse/filedata/repository.py`
- Create: `apps/server/src/datapulse/filedata/storage.py`
- Create: `apps/server/src/datapulse/filedata/service.py`
- Create: `apps/server/tests/filedata/test_storage.py`
- Create: `apps/server/tests/filedata/test_repository.py`
- Modify: `apps/server/src/datapulse/lifespan.py`

**Interfaces:**
- `FileAssetRecord(id, original_name, format, mime_type, sha256, size_bytes, storage_path, row_count, fields_json, created_at)`。
- `FileAssetRepository.create/get/list/delete(asset_id)`。
- `FileStorage.save(upload: UploadFile) -> StoredFile`；`StoredFile` 只包含随机存储路径、哈希、大小和原始文件名。
- `FileStorage.open_read(asset_id) -> BinaryIO`；只能从配置的 `resolved_files_dir()` 返回文件。
- `FileAssetService.ingest(upload, *, request_id) -> FileAssetResponse`。

- [ ] **Step 1: 写安全失败测试**

  测试路径穿越文件名、软链接、未知 MIME、扩展名不匹配、超过 `file_max_bytes`、空文件、哈希重复和删除后读取。断言异常码分别为 `FILE_TYPE_UNSUPPORTED`、`FILE_TOO_LARGE`、`FILE_EMPTY`、`FILE_NOT_FOUND`。

- [ ] **Step 2: 运行测试确认失败**

  Run: `uv run --package datapulse-server pytest apps/server/tests/filedata/test_storage.py -q`

  Expected: `filedata` 模块和迁移尚未存在。

- [ ] **Step 3: 增加元数据迁移**

  新建 `file_asset` 表，保存格式、校验和、大小、存储路径和解析字段 JSON；将 `dataset.data_source_id` 改为可空，并保留已有 SQL 数据集外键约束。迁移必须兼容现有 SQLite 元数据库，使用 Alembic batch 操作完成列可空变更。

- [ ] **Step 4: 实现安全存储**

  将上传内容流式写入临时文件，计算 SHA-256 和大小，校验完成后以 UUID 文件名移动到 `DATAPULSE_DATA_DIR/files/<asset_id>/source.<extension>`；任何异常都删除临时文件。读取前解析数据库路径并验证其父目录等于 `resolved_files_dir()` 下的资产目录。

- [ ] **Step 5: 运行存储和迁移测试**

  Run: `uv run --package datapulse-server alembic -c apps/server/alembic.ini upgrade head && uv run --package datapulse-server pytest apps/server/tests/filedata apps/server/tests/metadata/test_migrations.py -q`

  Expected: 新迁移、文件安全边界和原有迁移测试全部通过。

- [ ] **Step 6: 提交**

  ```bash
  git add apps/server/migrations/versions/0007_file_datasets.py apps/server/src/datapulse/metadata apps/server/src/datapulse/filedata apps/server/tests/filedata apps/server/tests/metadata/test_migrations.py
  git commit -m "feat: add secure file asset storage"
  ```

### Task 3: 实现文件解析与 DuckDB 执行器

**Files:**
- Create: `apps/server/src/datapulse/filedata/parsers.py`
- Create: `apps/server/src/datapulse/filedata/duckdb_executor.py`
- Create: `apps/server/src/datapulse/filedata/query.py`
- Modify: `apps/server/pyproject.toml`
- Modify: `apps/server/src/datapulse/lifespan.py`
- Create: `apps/server/tests/filedata/test_parsers.py`
- Create: `apps/server/tests/filedata/test_duckdb_executor.py`

**Interfaces:**
- `parse_file(path, format, *, sheet_name, max_rows) -> ParsedFile(fields, row_count, sample_rows, normalized_path)`。
- `FileDatasetQueryService.query(dataset, chart_spec, parameters, request_id) -> QueryResult`。
- `DuckDBExecutor.execute(sql, parameters, *, source_path, timeout_seconds, max_rows) -> QueryResult`。
- `FileQueryCompiler.compile(spec: ChartSpec, dataset: DatasetDefinition, source_path: Path) -> CompiledFileQuery(sql, parameters)`。

- [ ] **Step 1: 写四种格式的失败测试**

  使用临时 fixture 验证 CSV UTF-8、CSV BOM、Excel 两个 Sheet、JSON 数组根节点、Parquet 数字/日期字段；验证空 JSON、嵌套对象、缺失列和超过行数的行为。

- [ ] **Step 2: 运行解析测试确认失败**

  Run: `uv run --package datapulse-server pytest apps/server/tests/filedata/test_parsers.py -q`

- [ ] **Step 3: 实现解析器**

  CSV 使用 DuckDB `read_csv` 自动识别并限制 `sample_size`；JSON 只接受对象数组或记录数组；Excel 解析指定 Sheet 并转换为 Parquet；Parquet 通过 DuckDB `DESCRIBE` 读取 schema。将日期、时间、布尔、整数、浮点和字符串统一映射到 `DataType`。

- [ ] **Step 4: 写 DuckDB 安全失败测试**

  测试参数化过滤、未知字段、`max_rows`、超时、源文件不在允许目录、SQL 中出现文件系统函数和资源超限；断言不会执行请求传入的任意原始 SQL。

- [ ] **Step 5: 实现只读执行器**

  每次查询新建 DuckDB 内存连接，执行 `SET threads=2` 和 `SET memory_limit='512MB'`，只允许服务端生成的 `SELECT`；使用线程池执行同步 DuckDB API，超时后关闭连接并返回 `FILE_QUERY_TIMEOUT`。所有结果通过现有 `QueryResult` 归一化。

- [ ] **Step 6: 运行文件查询测试**

  Run: `uv run --package datapulse-server pytest apps/server/tests/filedata/test_parsers.py apps/server/tests/filedata/test_duckdb_executor.py apps/server/tests/screen/test_chart_query.py -q`

  Expected: 四种格式、参数过滤和查询资源限制通过。

- [ ] **Step 7: 提交**

  ```bash
  git add apps/server/src/datapulse/filedata apps/server/pyproject.toml apps/server/src/datapulse/lifespan.py apps/server/tests/filedata
  git commit -m "feat: query file datasets with duckdb"
  ```

### Task 4: 接入数据集服务和管理员 API

**Files:**
- Modify: `apps/server/src/datapulse/dataset/repository.py`
- Modify: `apps/server/src/datapulse/dataset/service.py`
- Modify: `apps/server/src/datapulse/dataset/api.py`
- Create: `apps/server/src/datapulse/filedata/api.py`
- Modify: `apps/server/src/datapulse/app.py`
- Modify: `apps/server/src/datapulse/lifespan.py`
- Create: `apps/server/tests/filedata/test_api.py`
- Modify: `apps/server/tests/dataset/test_service.py`
- Modify: `apps/server/tests/screen/test_runtime.py`

**Interfaces:**
- `POST /api/admin/files` multipart `file` -> `FileAssetResponse`。
- `GET /api/admin/files` -> `tuple[FileAssetResponse, ...]`。
- `DELETE /api/admin/files/{asset_id}` -> 204；被数据集引用时返回 `FILE_IN_USE`。
- `POST /api/admin/datasets/files` `FileDatasetCreate` -> `DatasetResponse`。
- `POST /api/admin/datasets/{dataset_id}/preview` 对 SQL 和 FileQuery 都返回 `QueryResult`。
- `DatasetService.create_file(data, *, request_id) -> DatasetResponse`。

- [ ] **Step 1: 写 API 失败测试**

  测试管理员上传四种格式、创建文件数据集、列出字段、预览、删除；测试未登录、CSRF 缺失、错误数据集、文件被引用和外部 SQL 数据集行为不回归。

- [ ] **Step 2: 实现数据集分支**

  `DatasetService.preview` 按 `definition.query` 类型分支：SQL 走现有 `DatasourceService`，FileQuery 走 `FileDatasetQueryService`；`create_file` 使用解析结果生成 `DatasetDefinition(query=FileQuery(asset_id, format))`，`data_source_id=None`。

- [ ] **Step 3: 接入路由和错误码**

  所有写操作复用 `require_admin` 和 `require_csrf`；将存储、解析、DuckDB、引用冲突异常映射为稳定的 `FILE_*` / `DATASET_*` 错误码，不返回内部绝对路径或 DuckDB 堆栈。

- [ ] **Step 4: 运行后端测试**

  Run: `uv run --package datapulse-server pytest apps/server/tests/filedata apps/server/tests/dataset apps/server/tests/screen/test_runtime.py -q`

- [ ] **Step 5: 提交**

  ```bash
  git add apps/server/src/datapulse/dataset apps/server/src/datapulse/filedata apps/server/src/datapulse/app.py apps/server/src/datapulse/lifespan.py apps/server/tests/filedata apps/server/tests/dataset apps/server/tests/screen/test_runtime.py
  git commit -m "feat: expose file datasets through admin api"
  ```

### Task 5: 完成文件数据集工作台

**Files:**
- Create: `apps/web/src/features/file-datasets/api.ts`
- Create: `apps/web/src/features/file-datasets/types.ts`
- Create: `apps/web/src/features/file-datasets/FileDatasetUploadView.vue`
- Create: `apps/web/src/features/file-datasets/FileDatasetPreview.vue`
- Modify: `apps/web/src/features/datasets/DatasetListView.vue`
- Modify: `apps/web/src/features/datasets/DatasetDetailView.vue`
- Modify: `apps/web/src/features/datasets/api.ts`
- Modify: `apps/web/src/features/datasets/types.ts`
- Modify: `apps/web/src/router/index.ts`
- Create: `apps/web/src/features/file-datasets/file-dataset.test.ts`
- Create: `apps/web/e2e/file-dataset.spec.ts`

**Interfaces:**
- `uploadFile(file: File): Promise<FileAsset>`。
- `createFileDataset(payload: FileDatasetCreatePayload): Promise<Dataset>`。
- 页面必须显示上传进度、解析字段、行数、Sheet 选择、数据预览和错误码。

- [ ] **Step 1: 写 Vue 失败测试**

  测试上传按钮、格式错误提示、Sheet 选择、字段类型展示、预览表格、创建成功跳转和未配置 AI 时页面不受影响。

- [ ] **Step 2: 实现 API 类型和页面**

  文件使用 `FormData` 上传，不把文件内容放入 JSON；页面沿用 Notion 风格 Studio Shell、现有 `InlineNotice` 和 `QueryResultTable`，不复制表格渲染逻辑。

- [ ] **Step 3: 加入数据集列表入口**

  在数据集列表增加“上传文件数据集”，详情页展示 `query.kind=file`、原始文件名、格式、字段和预览入口；SQL 数据集编辑路径保持原样。

- [ ] **Step 4: 运行前端与 E2E 测试**

  Run: `pnpm --filter @datapulse/web exec vitest run src/features/file-datasets/file-dataset.test.ts && pnpm test:e2e -- file-dataset.spec.ts`

- [ ] **Step 5: 提交**

  ```bash
  git add apps/web/src/features/file-datasets apps/web/src/features/datasets apps/web/src/router/index.ts apps/web/e2e/file-dataset.spec.ts
  git commit -m "feat: add file dataset workspace"
  ```

### Task 6: 建立 AI 配置与模型网关

**Files:**
- Create: `apps/server/src/datapulse/ai/gateway.py`
- Create: `apps/server/src/datapulse/ai/models.py`
- Create: `apps/server/src/datapulse/ai/service.py`
- Create: `apps/server/src/datapulse/ai/__init__.py`
- Modify: `apps/server/src/datapulse/settings.py`
- Modify: `apps/server/src/datapulse/lifespan.py`
- Modify: `apps/server/pyproject.toml`
- Create: `apps/server/tests/ai/test_gateway.py`
- Create: `apps/server/tests/ai/test_service.py`

**Interfaces:**
- `AiGateway.complete_json(*, system: str, user: str, response_model: type[T]) -> T`。
- `AiGateway.health() -> AiHealth(status: Literal["configured", "unconfigured", "unavailable"], model: str | None)`。
- `AiService.analyze(request: AiAnalysisRequest, *, request_id) -> AiAnalysisResponse`。

- [ ] **Step 1: 写模型网关失败测试**

  Mock `httpx.AsyncClient`，测试 OpenAI 兼容 `/chat/completions` 请求、Bearer Header、JSON 模式、超时、非 2xx、非法 JSON、模型拒绝和一次重试；断言 API Key 不出现在异常文本和日志中。

- [ ] **Step 2: 实现 Settings 和 Gateway**

  增加 `AI_ENABLED`、`AI_BASE_URL`、`AI_API_KEY`、`AI_MODEL`、`AI_TIMEOUT_SECONDS=30`、`AI_MAX_CONTEXT_ROWS=100`。当未配置时 `AiGateway` 返回 `AI_NOT_CONFIGURED`，不发网络请求；请求体包含 `response_format={"type":"json_object"}`，并用 Pydantic 解析结果。

- [ ] **Step 3: 实现生命周期注入**

  在 `lifespan.py` 创建 `app.state.ai_gateway` 和 `app.state.ai_service`，不影响未配置 AI 时的启动；关闭时释放 httpx client。

- [ ] **Step 4: 运行测试**

  Run: `uv run --package datapulse-server pytest apps/server/tests/ai/test_gateway.py apps/server/tests/ai/test_service.py -q`

- [ ] **Step 5: 提交**

  ```bash
  git add apps/server/src/datapulse/ai apps/server/src/datapulse/settings.py apps/server/src/datapulse/lifespan.py apps/server/pyproject.toml apps/server/tests/ai
  git commit -m "feat: add openai compatible ai gateway"
  ```

### Task 7: 实现数据上下文与安全 AI 分析服务

**Files:**
- Create: `apps/server/src/datapulse/ai/context.py`
- Modify: `apps/server/src/datapulse/ai/service.py`
- Create: `apps/server/src/datapulse/ai/api.py`
- Modify: `apps/server/src/datapulse/app.py`
- Create: `apps/server/tests/ai/test_context.py`
- Modify: `apps/server/tests/ai/test_service.py`
- Create: `apps/server/tests/ai/test_api.py`

**Interfaces:**
- `DatasetContextService.build(dataset_ids, *, max_rows) -> tuple[DatasetContext, ...]`。
- `DatasetContext(dataset_id, name, fields, sample_rows, summary)`。
- `AiService.analyze(request, *, request_id) -> AiAnalysisResponse`。
- `POST /api/admin/ai/analyze` -> `AiAnalysisResponse`。
- `GET /api/admin/ai/status` -> `AiHealth`。

- [ ] **Step 1: 写上下文和安全失败测试**

  测试上下文最多 100 行样例、字段最多 50 个、字符串截断、密码/连接配置/路径不出现；测试不存在的数据集、跨管理员不可见数据集、非法字段和非法图表类型均在调用模型前失败。

- [ ] **Step 2: 实现上下文构建器**

  从 `DatasetDefinition.fields` 生成字段目录；通过现有数据集预览接口取受限样例和列统计，只保留列名、类型、非敏感摘要和少量值。文件数据集样例走 DuckDB，SQL 数据集走已有查询服务。

- [ ] **Step 3: 实现分析流程**

  将用户问题和上下文发送给模型，要求返回 `AnalysisPlan` 与简短结论；服务端检查所有 dataset ID、dimension、measure、filter、sort 和 `recommended_chart`，再用 `ChartQueryCompiler` 或 `FileDatasetQueryService` 执行一次预览查询，返回 `AiAnalysisResponse`。

- [ ] **Step 4: 接入管理员路由和错误映射**

  所有接口依赖管理员 Session；错误码固定为 `AI_NOT_CONFIGURED`、`AI_UNAVAILABLE`、`AI_TIMEOUT`、`AI_INVALID_OUTPUT`、`AI_DATASET_INVALID`、`AI_CHART_INVALID`，响应不包含模型原始堆栈。

- [ ] **Step 5: 运行 AI 后端测试**

  Run: `uv run --package datapulse-server pytest apps/server/tests/ai -q`

- [ ] **Step 6: 提交**

  ```bash
  git add apps/server/src/datapulse/ai apps/server/src/datapulse/app.py apps/server/tests/ai
  git commit -m "feat: add safe ai data analysis service"
  ```

### Task 8: 实现自然语言生成 ChartSpec

**Files:**
- Modify: `apps/server/src/datapulse/contracts/ai.py`
- Modify: `apps/server/src/datapulse/ai/service.py`
- Modify: `apps/server/src/datapulse/ai/api.py`
- Create: `apps/server/tests/ai/test_chart_generation.py`
- Modify: `apps/server/tests/contracts/test_ai.py`

**Interfaces:**
- `AiChartRequest(question, dataset_id, target_component_type: ChartType | None = None)`。
- `AiChartResponse(chart_spec: ChartSpec, explanation: str, preview: QueryResult, warnings: tuple[str, ...])`。
- `POST /api/admin/ai/chart` -> `AiChartResponse`。

- [ ] **Step 1: 写失败测试**

  用固定模型 JSON 测试“按区域统计销售额”生成合法柱状图；测试模型请求未知字段、空 measures、与组件类型不匹配、limit 超限和非法 filter 时均拒绝。

- [ ] **Step 2: 实现 ChartSpec 生成和重校验**

  在提示词中只列出允许字段、聚合、过滤器和受注册表约束的组件能力；原始 E3 实现以九类组件为白名单，当前实现使用 21 类注册表。模型结果先解析为 `ChartSpec`，再补齐 dataset ID、限制 limit、校验字段和组件能力，最后执行预览查询。

- [ ] **Step 3: 运行测试并提交**

  Run: `uv run --package datapulse-server pytest apps/server/tests/ai/test_chart_generation.py apps/server/tests/contracts/test_ai.py -q`

  ```bash
  git add apps/server/src/datapulse/contracts/ai.py apps/server/src/datapulse/ai apps/server/tests/ai apps/server/tests/contracts/test_ai.py
  git commit -m "feat: generate safe chart specs with ai"
  ```

### Task 9: 实现 AI 生成完整大屏草稿

**Files:**
- Modify: `apps/server/src/datapulse/contracts/ai.py`
- Create: `apps/server/src/datapulse/ai/screen_generator.py`
- Modify: `apps/server/src/datapulse/ai/service.py`
- Modify: `apps/server/src/datapulse/ai/api.py`
- Create: `apps/server/tests/ai/test_screen_generator.py`
- Modify: `apps/server/tests/ai/test_service.py`

**Interfaces:**
- `AiScreenRequest(question, dataset_ids, canvas_width=1920, canvas_height=1080, theme: Literal["dark", "light"] = "dark")`。
- `AiScreenResponse(document: DashboardDocument, explanation: str, warnings: tuple[str, ...])`。
- `POST /api/admin/ai/screen` -> `AiScreenResponse`。
- `ScreenDraftGenerator.generate(request, *, request_id) -> AiScreenResponse`。
- `validate_ai_document(document, allowed_dataset_ids) -> DashboardDocument`。

- [ ] **Step 1: 写失败测试**

  使用固定模型 JSON 测试“销售运营大屏”至少生成标题、指标卡、趋势图、分类图、明细表和参数；测试未知组件、越权数据集、非法字段、越界 frame、脚本属性、超过组件上限和自动发布字段均被拒绝。

- [ ] **Step 2: 定义生成约束**

  提示词只允许 `builtin.text`、`builtin.image`、`builtin.kpi`、`builtin.table`、`builtin.progress`、`builtin.line`、`builtin.bar`、`builtin.pie`、`builtin.geo_map`；模型不得输出 SQL、JavaScript、图片路径或外部 URL。服务端为缺失的组件 ID、state、style、interaction 和 refresh 字段填充安全默认值。

- [ ] **Step 3: 实现草稿校验和规范化**

  校验所有 `data_binding.chart_spec.dataset_id` 属于请求中的数据集；每个字段、过滤器和聚合通过数据集定义重新检查；frame 必须落在画布内；组件总数最多 12 个；主题只接受现有 token；删除任何未知扩展字段。生成结果只作为内存响应返回，不创建 `ScreenRecord`。

- [ ] **Step 4: 接入服务端路由**

  `POST /api/admin/ai/screen` 复用管理员鉴权、AI 配置检查和上下文构建；返回可直接交给编辑器预览的 `DashboardDocument`，但不调用发布服务。

- [ ] **Step 5: 运行测试并提交**

  Run: `uv run --package datapulse-server pytest apps/server/tests/ai/test_screen_generator.py apps/server/tests/ai/test_service.py -q`

  ```bash
  git add apps/server/src/datapulse/contracts/ai.py apps/server/src/datapulse/ai apps/server/tests/ai
  git commit -m "feat: generate validated dashboard drafts with ai"
  ```

### Task 10: 增加 AI 分析、图表建议和大屏生成工作台

**Files:**
- Create: `apps/web/src/features/ai/api.ts`
- Create: `apps/web/src/features/ai/types.ts`
- Create: `apps/web/src/features/ai/AiAnalysisPanel.vue`
- Create: `apps/web/src/features/ai/ChartSuggestionCard.vue`
- Create: `apps/web/src/features/ai/AiScreenGeneratorDialog.vue`
- Modify: `apps/web/src/features/datasets/DatasetDetailView.vue`
- Modify: `apps/web/src/features/screens/ScreenEditorView.vue`
- Modify: `apps/web/src/features/screens/editor/store.ts`
- Create: `apps/web/src/features/ai/ai-panel.test.ts`
- Modify: `apps/web/src/features/screens/screen-list.test.ts`

**Interfaces:**
- `getAiStatus(): Promise<AiHealth>`。
- `analyzeDataset(payload): Promise<AiAnalysisResponse>`。
- `generateChart(payload): Promise<AiChartResponse>`。
- `generateScreen(payload): Promise<AiScreenResponse>`。
- `AiAnalysisPanel` 通过 `onApplyChart(chartSpec)` 回调，不直接调用 Screen API。
- `AiScreenGeneratorDialog` 通过 `onConfirm(document)` 回调，确认前不创建或发布大屏。

- [ ] **Step 1: 写前端失败测试**

  测试未配置状态、加载状态、分析结论、图表建议、字段校验错误、重试按钮；确认“应用到草稿”只调用编辑器 store 命令，不调用发布 API。

- [ ] **Step 2: 实现数据集分析面板**

  在数据集详情页增加 AI 分析入口，显示问题输入、示例问题、结论、假设、推荐图表和预览结果；模型不可用时显示配置状态和人工 SQL 入口。

- [ ] **Step 3: 实现图表建议预览**

  使用现有 `ChartSpec` 预览组件，不复制 ECharts 配置；建议卡片展示维度、指标、聚合、过滤器和解释。

- [ ] **Step 4: 接入大屏草稿**

  用户在编辑器中选择已有组件后点击“应用 AI 图表建议”，通过现有编辑器命令写入 `data_binding.chart_spec`；未选组件时只复制 JSON/提示，不自动创建组件、不自动发布。

- [ ] **Step 5: 实现 AI 生成整张大屏**

  在大屏列表增加“AI 创建大屏”，用户输入目标、选择数据集和主题后调用 `generateScreen`；对返回的 `DashboardDocument` 使用现有编辑器预览。点击“确认创建草稿”后才调用现有 `createScreen` 和 `updateScreen`，然后跳转编辑页；取消或关闭对话框不产生数据库记录，流程中不能出现 publish 请求。

- [ ] **Step 6: 运行前端测试**

  Run: `pnpm --filter @datapulse/web exec vitest run src/features/ai/ai-panel.test.ts src/features/screens/editor/store.test.ts src/features/screens/screen-list.test.ts`

- [ ] **Step 7: 提交**

  ```bash
  git add apps/web/src/features/ai apps/web/src/features/datasets/DatasetDetailView.vue apps/web/src/features/screens/ScreenEditorView.vue apps/web/src/features/screens/editor/store.ts
  git commit -m "feat: add ai analysis and screen generation workspace"
  ```

### Task 11: 完成端到端测试、文档和发布门禁

**Files:**
- Create: `apps/web/e2e/file-dataset.spec.ts`
- Create: `apps/web/e2e/ai-analysis.spec.ts`
- Create: `apps/web/e2e/ai-screen-generation.spec.ts`
- Create: `apps/server/tests/filedata/fixtures/*`
- Modify: `apps/web/e2e/fixtures/sales.sql`
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `package.json`
- Modify: `apps/server/tests/test_lifespan.py`

**Interfaces:**
- E2E AI 使用本地可控 fake OpenAI-compatible endpoint，不连接真实模型、不提交真实 API Key。
- 完整门禁继续使用 `pnpm verify:full`，外部 PostgreSQL/MySQL 测试在配置 DSN 时执行。

- [ ] **Step 1: 增加确定性 fixture 和 fake model**

  fixture 至少包含中文 CSV、两个 Sheet Excel、数组 JSON 和 Parquet；fake model 根据请求中的问题返回固定合法 `AnalysisPlan`、`ChartSpec` 或 `DashboardDocument`，也能按测试参数返回非法字段、超时和 malformed JSON。

- [ ] **Step 2: 编写文件数据集 E2E**

  覆盖上传、字段解析、Sheet 选择、预览、创建数据集、绑定现有折线图和删除保护；禁止通过 CSS 类名断言可访问流程。

- [ ] **Step 3: 编写 AI E2E**

  覆盖 AI 状态、自然语言分析、ChartSpec 预览、应用到选中组件、草稿刷新后保留、未配置 AI、超时和非法输出；断言没有发布请求。

- [ ] **Step 4: 编写 AI 大屏生成 E2E**

  使用 fake model 返回包含当前注册组件的确定性草稿；覆盖输入问题、数据集选择、深色/浅色主题、生成预览、取消不创建、确认创建后进入编辑器、刷新后草稿保留；监听发布 API，确认生成流程始终没有调用发布接口。再用非法组件和越权数据集响应验证前端展示错误且不落库。

- [ ] **Step 5: 更新文档和环境样例**

  README 明确 DuckDB 只处理文件数据，列出 `DATAPULSE_FILE_MAX_BYTES`、`DATAPULSE_FILE_MAX_ROWS`、`DATAPULSE_AI_ENABLED`、`DATAPULSE_AI_BASE_URL`、`DATAPULSE_AI_MODEL`、`DATAPULSE_AI_API_KEY` 和安全建议。

- [ ] **Step 6: 执行完整门禁**

  ```bash
  pnpm check:contracts
  pnpm test
  pnpm typecheck
  pnpm build
  pnpm test:integration
  pnpm test:e2e
  uv run --package datapulse-server ruff check apps/server tools
  git diff --check
  ```

- [ ] **Step 7: 提交**

  ```bash
  git add apps/web/e2e apps/server/tests/filedata apps/web/e2e/fixtures .env.example README.md package.json apps/server/tests/test_lifespan.py
  git commit -m "test: verify phase three file data and ai screen generation"
  ```

## 验收清单

- [ ] 四种文件格式上传、解析、预览和删除受控可用。
- [ ] 文件数据集与 SQL 数据集都能被当前 21 类组件中具备对应数据能力的组件使用。
- [ ] DuckDB 只读、路径隔离、资源限制和稳定错误码有测试。
- [ ] AI 配置可选，未配置时核心功能不降级。
- [ ] AI 分析上下文有字段、行数、敏感信息和数据集范围限制。
- [ ] 自然语言图表生成输出合法 `ChartSpec`，非法输出不会执行。
- [ ] AI 可以生成完整 `DashboardDocument` 草稿，非法组件/字段/布局不会落库。
- [ ] AI 只能预览或修改草稿，不能自动发布。
- [ ] E2E 覆盖成功、空/坏/超限文件、AI 超时和非法模型输出。
- [ ] 完整验证命令通过；外部数据库集成测试在提供 DSN 时通过。
