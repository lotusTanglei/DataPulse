# DataPulse

DataPulse 是一个面向私有部署、系统嵌入和 AI 辅助分析的开源数据分析与大屏创作软件。当前版本已经交付可实际使用的“数据源工作室”：单管理员登录、SQLite / PostgreSQL / MySQL（含 MariaDB）原生连接、Schema 浏览、只读参数化 SQL 调试，以及可保存和预览的数据集。

编辑端由 DataPulse 的单一管理员账号保护；未来发布的大屏页面以嵌入宿主系统为主，查看权限和身份由宿主系统承担。

## 当前能力与边界

已经具备：

- 一次性初始化代码、Argon2 密码哈希、管理员会话、CSRF 和登录限流
- SQLite、PostgreSQL、MySQL / MariaDB 原生异步连接器
- 数据库密码加密保存，响应与页面不回显明文密码
- Schema 按需浏览、只读 SQL 校验、参数绑定、超时/行数/并发限制
- 数据集保存、编辑和运行预览
- Vue 3 Studio 与 FastAPI 单镜像交付，容器启动自动执行 Alembic 迁移

DuckDB、本地文件导入、查询缓存、大屏编辑与发布、Web 嵌入/单点安全、插件定时刷新和 AI 自然语言分析将在后续阶段实现。

## 环境要求

- Git
- [uv](https://docs.astral.sh/uv/)
- Node.js 22
- pnpm 10
- Docker（容器部署和数据库集成测试需要）

## 本地开发

安装依赖并迁移元数据数据库：

```bash
uv sync --all-packages --group dev
pnpm install
uv run --package datapulse-server alembic -c apps/server/alembic.ini upgrade head
```

分别在两个终端启动后端和 Web：

```bash
uv run --package datapulse-server uvicorn datapulse.app:app --reload
pnpm dev:web
```

后端启动日志会输出仅可使用一次、且有有效期的初始化代码。打开 `http://127.0.0.1:5173/studio` 创建管理员。Vite 默认把 `/api` 代理到 `http://127.0.0.1:8000`，也可用 `VITE_API_PROXY_TARGET` 覆盖。

## Docker 部署

先生成独立的 32 字节主密钥：

```bash
python -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('='))"
```

复制 `.env.example` 为 `.env`，把输出替换到 `DATAPULSE_MASTER_KEY`，再启动：

```bash
docker compose up -d --build
docker compose logs datapulse
```

日志中的 `DataPulse one-time setup code` 是首次初始化代码。Studio 地址为 `http://127.0.0.1:8000/studio`，健康检查为 `http://127.0.0.1:8000/api/health`。容器会先执行 `alembic upgrade head`，成功后才启动 Web 服务。

运行数据保存在 `datapulse-data` 卷。SQLite 文件必须放在容器 `/data/sources` 下，并在表单中填写相对路径，例如 `sales.db`：

```bash
docker compose cp ./sales.db datapulse:/data/sources/sales.db
```

生产环境连接 PostgreSQL、MySQL 或 MariaDB 时，建议创建专用只读数据库账号，并只授予所需 Schema 的查询权限。

## 测试与验证

常规验证（协议、单元测试、类型和构建）：

```bash
pnpm verify
```

独立浏览器端到端测试会创建临时 SQLite 数据目录，并在结束时只清理该目录：

```bash
pnpm --filter @datapulse/web exec playwright install chromium
pnpm test:e2e
```

运行 PostgreSQL / MariaDB 连接器集成测试：

```bash
docker compose -f compose.test.yaml up -d --wait
DATAPULSE_TEST_POSTGRES_URL='postgresql+asyncpg://datapulse:datapulse@127.0.0.1:55432/datapulse' \
DATAPULSE_TEST_MYSQL_URL='mysql+asyncmy://datapulse:datapulse@127.0.0.1:53306/datapulse' \
pnpm test:integration
docker compose -f compose.test.yaml down -v
```

当测试数据库已经启动并设置上述环境变量时，可运行包括集成与浏览器测试的完整门禁：

```bash
pnpm verify:full
```

协议由 Python Pydantic 模型生成：

```bash
pnpm generate:contracts
pnpm check:contracts
```

## 设计文档

产品愿景、范围边界与完整技术路线见[产品与技术路线设计](docs/superpowers/specs/2026-07-29-datapulse-product-technical-route-design.md)。

本项目采用 [Apache License 2.0](LICENSE)。
