# DataPulse 第三阶段：文件数据集与 AI 分析设计

**状态：** 已确认范围

**日期：** 2026-08-01

**前置阶段：** DataPulse 第一阶段数据源工作台、第二阶段大屏编辑/播放/安全嵌入

## 1. 目标

第三阶段只聚焦两个用户价值：

1. 让用户可以上传 CSV、Excel、JSON、Parquet 文件，使用 DuckDB 将文件转换为可查询的数据集，并直接绑定现有大屏组件。
2. 让用户可以用自然语言进行数据分析、生成图表建议或生成完整大屏草稿，AI 输出结构化 `AnalysisPlan` / `ChartSpec` / `DashboardDocument`，再复用现有查询安全层和九类组件展示。

本阶段不扩展组件种类、不做设备管理、不做插件市场；允许 AI 使用现有组件生成一张可编辑的草稿大屏，但不允许自动发布。

## 2. 已有能力与本阶段边界

当前九类内置组件已经覆盖本阶段验证所需的指标卡、表格、进度条、折线图、柱状图、饼图、地图、文本和图片。第三阶段只补充组件属性、空状态和错误状态中直接影响文件数据/AI 体验的缺陷，不新增雷达图、漏斗图、桑基图、3D 地图等组件。

外部 SQLite、PostgreSQL、MySQL/MariaDB 继续使用原生连接器。DuckDB 是文件数据集的本地分析引擎，不代理外部数据库，也不替换元数据库。

以下能力明确留到后续阶段：

- 查询结果缓存、Parquet 物化缓存和后台调度；
- AI 批量修改现有整张 `DashboardDocument`；
- 组件插件 SDK、插件市场和模板市场；
- 播放列表、轮播、设备注册、心跳和远程设备管理；
- 多账号、RBAC、多人协作和发布版本历史。

## 3. 方案选择

### 3.1 文件查询方案

采用“文件资产 + `FileQuery` + 独立 DuckDB 执行器”的方案。

- 文件上传后存储在 `DATAPULSE_DATA_DIR/files`，数据库只保存文件元数据、哈希、格式、大小和解析结果。
- Excel 在导入阶段按选定 Sheet 转换为内部 Parquet；CSV、JSON、Parquet 保留原文件并由 DuckDB 的受限读取函数查询。
- `DatasetDefinition.query.kind == "file"` 时，运行时进入 `FileDatasetQueryService`；`kind == "sql"` 时继续进入现有原生连接器路径。
- 文件路径只来自服务端元数据映射，不能由请求体直接拼接；DuckDB 连接以只读方式创建，并限制线程、内存、结果行数和执行时间。

这样可以保持外部数据库连接器不变，又让文件数据和现有 `ChartSpec`、大屏运行时复用同一套结果结构。

### 3.2 AI 接入方案

采用 OpenAI 兼容 HTTP 接口 + Pydantic 结构化输出，不引入通用 Agent 框架。

- `AiGateway` 只负责模型请求、超时、重试一次和 JSON 解析。
- `DatasetContextService` 只向模型提供字段元数据、类型、有限样例和统计摘要，不提供数据库密码、连接配置、文件绝对路径或全表数据。
- 模型输出必须校验为 `AnalysisPlan` 或 `ChartSpec`；字段、聚合、过滤器、排序和图表类型必须再次通过服务端规则校验。
- 生成整张大屏时，模型输出必须校验为受限的 `DashboardDocument` 草稿；组件类型、数据集引用、图表绑定、画布边界和组件数量由服务端再次校验。
- AI 不能执行任意 SQL、Python、JavaScript，也不能直接写入或发布大屏。
- 没有配置 AI 时，数据源、数据集和大屏功能保持完整可用，AI 页面显示明确的配置提示。

## 4. 数据流

```text
管理员上传文件
  → 文件类型/大小/哈希校验
  → 解析字段和样例
  → 保存 FileAssetRecord
  → 创建 DatasetDefinition(query.kind = file)
  → 复用 ChartSpec 查询
  → DuckDB 只读执行
  → QueryResult
  → 九类内置组件
```

```text
自然语言问题
  → DatasetContextService
  → AiGateway(JSON)
  → AnalysisPlan / ChartSpec 校验
  → 现有 ChartQueryCompiler 或 FileDatasetQueryService
  → 用户预览并确认
  → 只写入当前编辑草稿的组件绑定
```

```text
“生成销售运营大屏”
  → 数据集上下文
  → AiGateway(JSON DashboardDocument 草稿)
  → 组件/字段/布局/资源引用校验
  → 用户预览草稿
  → 创建或写入编辑草稿
  → 管理员手动发布
```

## 5. 安全与资源限制

- 仅管理员 Session 可以上传文件、创建文件数据集和调用 AI 管理接口。
- 默认单文件上限 100 MB，单次解析结果最多 5,000 行；限制通过 `DATAPULSE_FILE_MAX_BYTES` 和 `DATAPULSE_FILE_MAX_ROWS` 配置。
- 允许扩展名与 MIME 必须同时匹配；文件名只作为展示文本，存储名使用随机 ID；禁止路径穿越、软链接和任意目录读取。
- CSV、JSON、Parquet 使用 DuckDB 的只读读取函数；Excel 先转换为 Parquet，转换失败不创建数据集。
- DuckDB 单次执行最多 30 秒、最多 2 个线程、最多 512 MB 内存；超时、内存和结果超限返回稳定错误码。
- AI 请求上下文最多 100 行样例和 50 个字段；API Key 只从服务端环境读取，不能返回前端。
- AI 生成的字段必须属于目标数据集，数据集 ID 必须属于当前管理员可见范围；所有查询仍经过现有只读校验和参数校验。

## 6. 验收标准

1. 管理员可以上传 CSV、Excel、JSON、Parquet，并看到解析出的字段、类型、行数和样例。
2. 文件数据集可以预览、编辑名称、删除，并绑定到现有九类组件。
3. 相同 `ChartSpec` 在原生数据库和文件数据集上都能返回统一 `QueryResult`。
4. CSV 中文编码、Excel Sheet 选择、JSON 数组根节点和 Parquet 类型至少有自动化覆盖。
5. 未配置 AI 时核心数据功能不受影响；配置兼容 OpenAI 的服务后可以完成一次自然语言分析。
6. AI 输出非法字段、非法图表类型、越权数据集或无法解析的 JSON 时不会执行查询，并返回稳定错误码。
7. 用户可以预览 AI 生成的 `ChartSpec`，确认后只修改草稿组件绑定，不能自动发布。
8. 用户可以输入一句话生成使用现有九类组件的完整大屏草稿，确认后才创建草稿记录；生成结果不能直接发布。
9. AI 生成的组件、数据集引用、`ChartSpec`、边界和资源引用非法时不会写入数据库。
10. AI 上下文和日志不泄露连接密码、签名密钥、文件绝对路径和完整数据集。
11. 前端、后端、契约、集成和 E2E 测试覆盖成功、空文件、坏文件、超限、AI 未配置、AI 超时和 AI 非法输出。
