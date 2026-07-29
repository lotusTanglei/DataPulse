# DataPulse 数据源工作台设计

**状态：** 已批准  
**日期：** 2026-07-29  
**基础设计：** [DataPulse 产品与技术路线设计](2026-07-29-datapulse-product-technical-route-design.md)

## 1. 目标

本阶段为 DataPulse 建立第一个可以由最终用户操作的数据分析闭环：

```text
首次初始化
→ 管理员登录
→ 创建数据库连接
→ 测试连接
→ 浏览 Schema、表和字段
→ 编写并执行安全的只读 SQL
→ 表格预览查询结果
→ 保存为数据集
```

首批外部数据库连接器：

- SQLite。
- PostgreSQL。
- MySQL/MariaDB。

编辑管理端由 DataPulse 自己认证。未来发布播放器不使用编辑端 Session，而由宿主系统完成查看权限判断并签发短期 Embed Ticket。

## 2. 范围边界

### 2.1 本阶段包含

- 单一管理员账号。
- 一次性初始化码和首次设置页面。
- 管理员登录、退出、修改密码和服务端 Session。
- CSRF 防护和登录失败限流。
- DataPulse 元数据库和 Alembic 迁移。
- SQLite、PostgreSQL、MySQL/MariaDB 原生异步连接器。
- 数据源创建、修改、删除、测试连接和状态诊断。
- Schema、表、视图和字段浏览。
- SQLGlot 只读 SQL 安全检查。
- 查询参数、超时、返回行数和并发限制。
- SQL 调试和虚拟滚动结果预览。
- 数据集创建、修改、删除和预览。
- 稳定错误码、请求 ID 和 QueryRun 诊断记录。
- Notion 风格的 `/studio` 管理工作台。
- 本地、集成、前端和端到端测试。

### 2.2 本阶段不包含

- 多账号、邀请、用户列表、RBAC、OIDC 和多人实时协作。
- CSV、Excel、JSON、Parquet 和 DuckDB。
- 跨数据源关联。
- 查询结果缓存和服务端定时刷新。
- 可视化数据加工和 ETL。
- 大屏拖拽画布和图表组件。
- 发布播放器和 Embed Ticket 的运行时实现。
- SQL Server、Oracle 和 ClickHouse。

## 3. 已确认的关键决策

| 主题 | 决策 |
|---|---|
| 项目元数据库 | 默认 SQLite，文件为 `/data/datapulse.db` |
| 外部数据库 | 原生异步驱动，不通过 DuckDB 代理 |
| PostgreSQL | SQLAlchemy 2 + `asyncpg` |
| MySQL/MariaDB | SQLAlchemy 2 + `asyncmy` |
| SQLite 数据源 | SQLAlchemy 2 + `aiosqlite`，只读文件连接 |
| SQL 安全 | SQLGlot 按连接器方言解析和拒绝危险 AST |
| 管理端身份 | 单一管理员、本地密码、服务端 Session |
| 密码哈希 | Argon2id |
| 数据源密码 | `DATAPULSE_MASTER_KEY` + AES-256-GCM |
| 前端 | Vue 3、Vue Router、Pinia、CodeMirror 6 |
| 视觉方向 | Notion 式暖白、低对比、文档式工作台 |
| DuckDB | 延后到文件数据和 Parquet 缓存阶段 |

DuckDB 在长期架构中只负责本地文件、Parquet 缓存和内存数据分析。它不是元数据库，也不是本阶段的外部数据库连接器。

## 4. 系统结构

后端保持单体部署，模块通过接口隔离：

```text
datapulse
├── auth
│   ├── models
│   ├── password
│   ├── session
│   ├── bootstrap
│   └── api
├── metadata
│   ├── database
│   ├── models
│   └── migrations
├── datasource
│   ├── contracts
│   ├── registry
│   ├── engine_manager
│   ├── secrets
│   ├── sqlite
│   ├── postgresql
│   ├── mysql
│   └── api
├── query
│   ├── safety
│   ├── parameters
│   ├── limits
│   ├── execution
│   └── result
└── dataset
    ├── repository
    ├── service
    └── api
```

依赖方向：

- `auth` 和 `metadata` 不依赖连接器。
- `datasource` 依赖 `metadata` 保存配置，依赖 `secrets` 解密凭据。
- `query` 通过连接器协议执行，不直接判断数据库类型。
- `dataset` 调用 `query`，不直接持有数据库连接。
- API 层只做 HTTP 映射，不包含数据库方言分支。

前端结构：

```text
apps/web/src
├── router
├── stores/auth
├── features/setup
├── features/login
├── features/datasources
├── features/query
├── features/datasets
└── ui
```

## 5. 元数据库

### 5.1 数据库位置

默认连接：

```text
sqlite+aiosqlite:////data/datapulse.db
```

本地开发使用 `Settings.data_dir` 下的同名文件。元数据库通过 SQLAlchemy 2 的异步接口访问，使用 Alembic 管理迁移。应用启动时只检查迁移状态，不在生产环境隐式修改表结构。Docker 入口脚本在启动 Uvicorn 前显式执行 `alembic upgrade head`；本地开发使用同一命令初始化或升级数据库。

### 5.2 AdminAccount

系统最多存在一条管理员记录：

- `id`：固定单例标识。
- `username`：管理员登录名。
- `password_hash`：Argon2id 哈希。
- `password_changed_at`。
- `created_at`。
- `updated_at`。

密码不加密保存，也不能恢复；只保存单向哈希。

### 5.3 AdminSession

- `id`：随机 Session ID 的 SHA-256 哈希。
- `csrf_token_hash`。
- `created_at`。
- `expires_at`。
- `last_seen_at`。

浏览器 Cookie 保存 32 字节随机 Session Token，数据库只保存哈希。Session 默认绝对有效期为 8 小时。

### 5.4 DataSource

- `id`：UUID。
- `name`：工作台显示名，同一安装内唯一。
- `connector_type`：`sqlite`、`postgresql` 或 `mysql`。
- `config_json`：通过连接器专属 Pydantic 模型校验的非敏感配置。
- `secret_envelope`：可空 AES-GCM 密文信封。
- `status`：`unknown`、`available` 或 `unavailable`。
- `last_checked_at`。
- `last_latency_ms`。
- `last_error_code`。
- `created_at`。
- `updated_at`。

后端响应永不包含 `secret_envelope`，也不返回已保存密码的占位字符串。更新请求未传密码时保留原凭据；明确选择“清除密码”才删除密文。

### 5.5 Dataset

- `id`：UUID。
- `name`：显示名。
- `data_source_id`。
- `definition_json`：符合 `DatasetDefinition` v1 的完整定义。
- `created_at`。
- `updated_at`。

删除被数据集引用的数据源返回冲突错误，不做级联删除。

### 5.6 QueryRun

- `id`：UUID，同时作为请求诊断 ID。
- `data_source_id`。
- `dataset_id`：调试查询时为空。
- `trigger`：`debug` 或 `dataset_preview`。
- `query_hash`：规范化 SQL 的 SHA-256，不保存明文 SQL。
- `status`：`running`、`succeeded`、`failed`、`timed_out` 或 `cancelled`。
- `duration_ms`。
- `row_count`。
- `truncated`。
- `error_code`。
- `started_at`。
- `finished_at`。

不保存完整查询结果、数据库密码和参数值。

## 6. 管理员认证

### 6.1 首次初始化

当 `AdminAccount` 不存在时：

1. 服务启动生成高熵一次性初始化码。
2. 服务只在标准错误日志中输出初始化码。
3. 数据库保存初始化码哈希和过期时间。
4. 初始化码有效期为 30 分钟；服务重启或过期后生成新码。
5. `/studio/setup` 要求初始化码、用户名和新密码。
6. 创建管理员成功后删除初始化码，并创建管理员 Session。
7. 管理员存在时 `/api/auth/setup` 固定返回 404，不能再次初始化。

初始化码不能放入 URL、访问日志或浏览器持久存储。

### 6.2 密码和登录

- 密码最少 10 个字符。
- 使用 Argon2id 默认安全参数哈希。
- 登录错误统一返回 `AUTH_INVALID_CREDENTIALS`，不区分用户名和密码。
- 同一来源 IP 在 15 分钟内连续失败 5 次后返回 429。
- 成功登录清除对应失败窗口。
- 登录限流保存在进程内；当前单实例架构不引入 Redis。

### 6.3 Session 和 CSRF

Cookie 名为 `datapulse_session`：

- `HttpOnly=true`。
- `SameSite=Lax`。
- `Path=/`。
- 生产环境 `Secure=true`。

创建 Session 时同时设置可由同源前端读取的 `datapulse_csrf` Cookie。它使用独立的 32 字节随机值、`SameSite=Lax`、生产环境 `Secure=true`，但不设置 `HttpOnly`。数据库只保存该值的 SHA-256 哈希。前端把 Cookie 原值复制到 `X-CSRF-Token`；后端同时校验 Cookie、请求头和数据库哈希。`GET /api/auth/session` 只返回当前管理员信息，不返回新的 CSRF 值。

所有带 Session 的 `POST`、`PATCH` 和 `DELETE` 请求必须发送 `X-CSRF-Token`。登录与初始化接口没有既有 Session，通过默认不允许跨域的 CORS、严格 `Origin` 校验和限流保护。

管理员修改密码后撤销除当前请求外的全部 Session；退出登录撤销当前 Session 并清除 Cookie。

## 7. 数据源秘密

`DATAPULSE_MASTER_KEY` 是 URL-safe Base64 编码的 32 字节随机值。后端启动时校验格式，但允许在只使用 SQLite 数据源时不配置。

PostgreSQL 或 MySQL/MariaDB 创建、测试或查询需要密码且主密钥缺失时，返回 HTTP 503 和 `DATASOURCE_SECRET_KEY_MISSING`。

AES-GCM 信封包含：

```json
{
  "version": 1,
  "nonce": "base64url",
  "ciphertext": "base64url"
}
```

- 每次保存生成新的 12 字节随机 nonce。
- AAD 由数据源 ID、字段名和信封版本组成。
- 解密失败返回稳定错误，不把加密库异常或密文写入日志。
- API、日志、QueryRun 和项目导出均不返回密码。

## 8. 连接器协议

连接器注册表按 `connector_type` 解析实现。核心协议：

```python
class Connector(Protocol):
    type: ConnectorType
    dialect: str

    async def test_connection(
        self,
        config: ConnectorConfig,
        secret: ConnectorSecret | None,
    ) -> ConnectionTestResult: ...

    async def list_namespaces(
        self,
        config: ConnectorConfig,
        secret: ConnectorSecret | None,
    ) -> tuple[NamespaceInfo, ...]: ...

    async def list_relations(
        self,
        config: ConnectorConfig,
        secret: ConnectorSecret | None,
        namespace: str | None,
    ) -> tuple[RelationInfo, ...]: ...

    async def describe_relation(
        self,
        config: ConnectorConfig,
        secret: ConnectorSecret | None,
        namespace: str | None,
        relation: str,
    ) -> RelationSchema: ...

    async def stream_query(
        self,
        config: ConnectorConfig,
        secret: ConnectorSecret | None,
        query: ValidatedQuery,
        parameters: JsonObject,
        policy: QueryPolicy,
    ) -> QueryStream: ...
```

API 和数据集服务只依赖该协议。每个官方连接器必须通过相同的连接器契约测试。

### 8.1 EngineManager

- PostgreSQL 和 MySQL/MariaDB 使用按数据源缓存的异步 Engine。
- Engine 键由数据源 ID 和 `updated_at` 组成。
- 修改或删除数据源立即 `dispose()` 旧 Engine。
- `pool_pre_ping=true`。
- 单数据源池上限为 2。
- SQLite 使用只读连接，不维持面向写入的长连接池。

### 8.2 SQLiteConnector

- 配置只保存相对于 `Settings.sources_dir` 的 POSIX 路径。
- `Settings.sources_dir` 默认为 `/data/sources`。
- 解析后的真实路径必须位于该目录内。
- 文件必须存在且是普通文件。
- 使用 SQLite URI `mode=ro`。
- 禁止 `ATTACH`、`DETACH`、`PRAGMA` 和扩展加载。
- namespace 为空；表和视图从 SQLite catalog 读取。

### 8.3 PostgreSQLConnector

- 配置包含 host、port、database、username、SSL 模式。
- 默认端口 5432。
- 使用 `asyncpg`。
- 每次用户查询运行在 `READ ONLY` 事务中。
- 使用 PostgreSQL `statement_timeout` 作为数据库侧超时。
- 系统 catalog 查询与用户 SQL 使用同一只读凭据。

### 8.4 MySQLConnector

- 同时支持 MySQL 和 MariaDB。
- 配置包含 host、port、database、username、SSL 设置。
- 默认端口 3306。
- 使用 `asyncmy`。
- 每次用户查询运行在只读事务中。
- 使用驱动读取超时和应用层超时；支持时设置数据库语句超时。
- Schema 浏览从 `information_schema` 读取。

## 9. 安全查询

### 9.1 AST 规则

SQLGlot 使用连接器方言解析。必须满足：

- 恰好一条语句。
- 顶层是查询表达式。
- 允许 `SELECT`、`WITH`、`UNION`、`INTERSECT` 和 `EXCEPT`。
- 递归拒绝写入、DDL、事务控制、锁、文件和命令类节点。
- 拒绝 `INSERT`、`UPDATE`、`DELETE`、`MERGE`、`CREATE`、`ALTER`、`DROP`、`TRUNCATE`、`COPY`、`ATTACH`、`DETACH`、`PRAGMA`、`CALL`、`EXECUTE` 和 `SELECT ... FOR UPDATE`。
- 注释不影响判定。

数据库账号仍必须由部署者配置为只读账号。AST 检查不是数据库权限的替代品。

### 9.2 参数

- 用户 SQL 使用统一命名参数 `:name`。
- 参数值来自 JSON 对象。
- 参数名称必须与数据集定义一致。
- 后端只通过驱动绑定参数，不做字符串插值。
- 不提供表名、字段名等标识符参数。

### 9.3 超时、限行和并发

- 默认查询超时 30 秒。
- 请求可降低超时，不能超过 300 秒。
- 默认最大返回 1,000 行，绝对上限 5,000 行。
- 连接器流式读取至 `max_rows + 1`；多出的第 1 行只用于设置 `truncated=true`。
- 不通过改写用户 SQL 强行注入 `LIMIT`，避免改变方言语义。
- 全局查询 Semaphore 默认为 4。
- 每个数据源 Semaphore 默认为 2。
- 无法立即取得并发槽时返回 429，不无限排队。
- 应用层超时后关闭结果流并尝试取消数据库查询。

### 9.4 QueryResult

HTTP 响应：

```json
{
  "request_id": "uuid",
  "columns": [
    {"name": "month", "data_type": "string"},
    {"name": "sales", "data_type": "number"}
  ],
  "rows": [
    ["2026-06", 284320],
    ["2026-07", 319840]
  ],
  "row_count": 2,
  "truncated": false,
  "duration_ms": 86
}
```

日期和时间使用 ISO 8601；二进制值使用 Base64；无法安全表示为 JSON number 的高精度 Decimal 使用字符串并保留列类型。列名重复时保持位置，不把每行转换为对象。

## 10. API

### 10.1 认证

```text
GET    /api/auth/status
POST   /api/auth/setup
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/session
PATCH  /api/auth/password
```

`status` 只返回是否已经初始化，不返回管理员名称。

### 10.2 数据源

```text
GET    /api/admin/datasources
POST   /api/admin/datasources
GET    /api/admin/datasources/{id}
PATCH  /api/admin/datasources/{id}
DELETE /api/admin/datasources/{id}
POST   /api/admin/datasources/{id}/test
GET    /api/admin/datasources/{id}/namespaces
GET    /api/admin/datasources/{id}/relations
GET    /api/admin/datasources/{id}/relation
POST   /api/admin/datasources/{id}/query
```

关系详情接口用查询参数传 `namespace` 和 `relation`，不把任意数据库标识符拼接到路由。Schema 浏览结果分页或懒加载，避免一次返回整个 catalog。

### 10.3 数据集

```text
GET    /api/admin/datasets
POST   /api/admin/datasets
GET    /api/admin/datasets/{id}
PATCH  /api/admin/datasets/{id}
DELETE /api/admin/datasets/{id}
POST   /api/admin/datasets/{id}/preview
```

“保存为数据集”使用已通过安全检查的 SQL、参数定义和推断字段创建 `DatasetDefinition` v1。每次预览仍重新运行安全检查。

## 11. 前端体验

### 11.1 路由

```text
/studio/setup
/studio/login
/studio/datasources
/studio/datasources/new
/studio/datasources/:id
/studio/query
/studio/datasets
/studio/datasets/:id
```

Vue Router 在进入 `/studio/*` 前读取认证状态：

- 未初始化跳转 `/studio/setup`。
- 已初始化但未登录跳转 `/studio/login`。
- 已登录访问 setup/login 时跳转数据源列表。

### 11.2 数据源页面

数据源列表采用类似 Notion Database 的轻量表格，显示：

- 名称。
- 类型。
- 安全处理后的地址或文件名。
- 连接状态。
- 最近检查。
- 最近查询。
- 测试、编辑和删除操作。

连接表单按数据库类型展示字段。编辑时密码字段为空并提示“留空则保留现有密码”，后端不返回密码或密码长度。

### 11.3 数据源详情

同一页面提供：

- 概览。
- Schema。
- SQL 调试。
- 设置。

Schema 树逐级加载 namespace、relation 和 fields。SQLite 不显示无意义的 namespace 层级。

### 11.4 SQL 调试

- CodeMirror 6 SQL 编辑器。
- 方言高亮。
- `Ctrl/Cmd + Enter` 执行。
- 单独的参数输入区。
- 固定显示只读、最大行数和超时。
- 使用 `AbortController` 终止浏览器请求，后端尝试取消数据库执行。
- 结果使用虚拟滚动表格。
- 显示耗时、行数、截断状态和请求 ID。
- 成功结果可以保存为数据集。
- 查询失败保留 SQL 和参数。

## 12. 视觉规范

设计语言以用户批准的 Notion 风格工作台为准：

- 背景：`#FFFFFF` 和 `#F7F7F5`。
- 主文字：`#37352F`。
- 次文字：`#787774`。
- 边界：`#E9E9E7`。
- 主操作：近黑色实心按钮。
- 成功色只用于连接和执行状态，不做大面积品牌铺色。
- 字体：Inter、PingFang SC 和系统无衬线字体。
- 间距使用 4/8 像素体系。
- 常规圆角 5～8 像素。
- 几乎不使用渐变和大阴影。
- 信息布局像可操作文档，不堆叠传统仪表盘卡片。
- 编辑工作台最小支持宽度为 1,200px。
- 登录和初始化页面支持移动端；SQL 工作台不针对手机优化。

后续大屏编辑器、预览页和发布播放器沿用相同字体、灰阶、间距和控件语义，但大屏画布本身允许用户主题覆盖。

## 13. 错误模型

统一错误响应：

```json
{
  "error": {
    "code": "QUERY_NOT_READ_ONLY",
    "message": "只允许执行只读查询。",
    "request_id": "uuid",
    "field_errors": []
  }
}
```

错误类别：

- `AUTH_*`：初始化、登录、Session、CSRF 和限流。
- `DATASOURCE_*`：配置、密钥、连接和 catalog。
- `QUERY_*`：解析、只读、参数、超时、限行和并发。
- `DATASET_*`：定义、依赖和预览。

HTTP 映射：

- 400：请求语义或 SQL 规则错误。
- 401：未登录或 Session 过期。
- 403：CSRF 或 Origin 拒绝。
- 404：资源不存在。
- 409：名称冲突或资源依赖。
- 422：字段校验失败。
- 429：登录或查询并发限制。
- 503：主密钥缺失或外部数据库不可用。
- 504：查询超时。

驱动原始异常仅写入脱敏后的服务端诊断，不直接返回浏览器。

## 14. 测试

### 14.1 单元测试

- Argon2id 哈希和验证。
- 初始化码生命周期。
- Session 撤销、过期和 CSRF。
- 登录限流。
- AES-GCM round-trip、随机 nonce、错误密钥和 AAD。
- SQLGlot 三种方言的允许及拒绝矩阵。
- 参数名称和值绑定。
- JSON 值和数据库类型标准化。
- SQLite 路径穿越和只读模式。
- 全局及单数据源并发槽。

### 14.2 连接器契约测试

同一测试套件验证三个连接器：

- 测试连接成功和失败。
- namespace、表、视图和字段浏览。
- 参数化 SELECT。
- 空结果和重复列名。
- 超时。
- 最大行数和截断。
- 写入语句拒绝。
- 凭据或配置错误的稳定错误码。

SQLite 测试使用临时文件。PostgreSQL 和 MariaDB 测试使用 CI 服务容器；本地在 Docker 可用时运行同一套集成测试。

### 14.3 API 和前端测试

- FastAPI 初始化、登录、Cookie、CSRF 和数据源 CRUD。
- 数据源密码不会出现在响应和日志。
- 数据源依赖冲突。
- Vue setup/login 路由守卫。
- 三种数据源表单。
- Schema 懒加载。
- SQL 参数、执行状态、错误保留和结果虚拟表格。
- 保存为数据集。

### 14.4 端到端测试

Playwright 使用 SQLite 完成：

```text
初始化管理员
→ 退出和重新登录
→ 创建 SQLite 数据源
→ 测试连接
→ 浏览表字段
→ 执行参数化查询
→ 保存数据集
→ 预览数据集
```

## 15. 验收标准

本阶段完成必须同时满足：

- 新安装只能通过日志中的有效初始化码创建管理员。
- 未登录请求不能访问任何 `/api/admin/*`。
- CSRF 缺失或错误的写请求被拒绝。
- 数据源密码加密保存且不出现在 API、日志或 QueryRun。
- SQLite、PostgreSQL 和 MySQL/MariaDB 通过统一连接器契约测试。
- 危险 SQL 在连接数据库前被拒绝。
- 查询遵守参数绑定、超时、限行和并发限制。
- 管理员能在前端完成连接、Schema 浏览、SQL 调试和保存数据集。
- Notion 风格在数据源列表、详情、SQL 调试和数据集页面一致。
- Python 3.13 和 3.14 测试通过。
- 前端类型检查、单元测试、构建和 Playwright 通过。
- Docker 镜像继续以非 root 用户运行。
- 现有协议生成无漂移。
