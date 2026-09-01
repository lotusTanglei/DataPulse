# DataPulse

DataPulse 是一个面向私有部署、系统嵌入和 AI 辅助分析的开源数据分析与大屏创作软件。当前版本已经交付数据源工作室和完整的大屏创作链路：单管理员登录、数据库与 HTTP API 数据源、可复用数据集、5 个内置模板、21 类内置组件、可视化编辑、草稿预览、发布、独立播放和安全嵌入。

编辑端由 DataPulse 的单一管理员账号保护；未来发布的大屏页面以嵌入宿主系统为主，查看权限和身份由宿主系统承担。

## 当前能力与边界

已经具备：

- 一次性初始化代码、Argon2 密码哈希、管理员会话、CSRF 和登录限流
- SQLite、PostgreSQL、MySQL / MariaDB 原生异步连接器，以及受 SSRF 防护的 HTTP/HTTPS JSON API 连接器（无认证、Bearer、API Key、Basic）
- 数据库密码加密保存，响应与页面不回显明文密码
- Schema 按需浏览、只读 SQL 校验、参数绑定、超时/行数/并发限制
- 数据库表/只读 SQL、HTTP API JSON 和文件数据集的保存、编辑与运行预览
- CSV、Excel、JSON、Parquet 文件数据集，包含 Sheet 选择、样例预览和维护
- AI 自然语言分析、图表建议、整张大屏草稿生成，以及编辑器内的局部修改预览
- 1920 × 1080 大屏画布、拖拽缩放、多选对齐/等距、成组、图层、撤销/重做和自动保存
- 5 个内置大屏模板；模板和组件支持确定性的演示数据与受校验的静态数据，不连接真实数据源也能完成设计预览
- 文本、图片、面板、分割线、数字翻牌、指标、进度、仪表盘、状态矩阵、表格、排行榜、告警列表、时间线、折线图、柱状图、饼图、雷达图、热力图、散点图、漏斗图和地图组件
- 数据绑定、全局参数、点击联动、10/30/60/300 秒定时刷新
- 草稿预览和覆盖式发布；需要历史版本时可在发布前复制大屏
- 可撤销显示密钥保护的独立播放页面
- 宿主 API Key、最长 8 小时短票据、精确 Origin 和 CSP 保护的系统嵌入
- `@datapulse/embed-sdk` 的刷新、参数、全屏、错误回调和多实例通信
- 运行时组件级错误隔离和手动刷新
- Vue 3 Studio 与 FastAPI 单镜像交付，容器启动自动执行 Alembic 迁移

当前不包含多用户协作、复杂权限、模板市场、组件市场、插件 SDK 或任意
JavaScript/HTML 注入。内置模板不等于模板市场。AI 生成和局部修改只会先产生预览或
写入草稿，不会自动发布；发布仍需管理员在编辑器中明确确认。

## 路线口径

项目总路线中的“第一阶段、第二阶段、第三阶段”表示产品成熟度；仓库计划中的
`E1`、`E2`、`E3` 表示工程交付顺序。当前工程阶段不等同于产品第三阶段：

- `E1` 数据基础：数据源、数据集和安全查询，对应产品第一阶段的基础能力。
- `E2` 编辑与交付：编辑器、预览、发布、独立播放和嵌入，对应产品第一阶段的核心闭环。
- `E3` 文件数据与 AI：文件数据集、DuckDB、AI 分析和整屏草稿生成，支撑产品第一阶段的 AI 入口和第二阶段的数据理解。
- `E4` 融合式创作：当前仓库已交付首批能力，包括内置模板、演示/静态数据和编辑器内 AI 局部修改预览；后续仍需完成更完整的创作验收。
- `E5` 真实项目质量和 `E6` 产品成熟度，分别对应产品第二、第三阶段的后续验收工作。

产品路线的阶段验收不能仅以工程里程碑完成作为依据；还必须继续验证预览确认撤销、
长期播放、跨浏览器视觉回归、版本迁移和 AI 质量评估等用户侧结果。

播放和嵌入共享同一份已发布文档与组件运行时，但访问方式不同：独立播放使用可撤销
显示密钥，系统嵌入由宿主后端使用 API Key 换取短期 Embed Ticket。编辑端 Session
不会暴露给播放页或宿主前端。

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

先分别生成数据库主密钥和页面签名密钥。两者都必须是独立随机的
32 字节值，不要复用：

```bash
python3 -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('='))"
```

运行两次命令，复制 `.env.example` 为 `.env`，分别填写
`DATAPULSE_MASTER_KEY` 和 `DATAPULSE_SIGNING_KEY`。容器数据目录固定为
`DATAPULSE_DATA_DIR=/data`，然后启动：

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs datapulse
```

日志中的 `DataPulse one-time setup code` 是首次初始化代码。Studio 地址为 `http://127.0.0.1:8000/studio`，健康检查为 `http://127.0.0.1:8000/api/health`。容器会先执行 `alembic upgrade head`，成功后才启动 Web 服务。

运行数据保存在 `datapulse-data` 卷。SQLite 文件必须放在容器 `/data/sources` 下，并在表单中填写相对路径，例如 `sales.db`：

```bash
docker compose cp ./sales.db datapulse:/data/sources/sales.db
```

生产环境连接 PostgreSQL、MySQL 或 MariaDB 时，建议创建专用只读数据库账号，并只授予所需 Schema 的查询权限。

## HTTP API 数据集

先在“数据源”中创建 HTTP API 连接，再从“数据集 → API 数据集”保存请求定义。请求
支持 `GET` 和 `POST`、查询参数、POST JSON 请求体，以及用点号路径选择嵌套响应，例如
`data.items`。响应可以是对象数组、单个对象或标量；对象数组会合并字段并转换为统一的
查询结果，之后可像数据库和文件数据集一样绑定到图表、表格和指标组件。

```json
{
  "method": "GET",
  "url": "https://api.example.com/v1/orders",
  "query": {"region": "east"},
  "response_path": "data.items"
}
```

HTTP API 凭据保存在数据源的加密密钥信封中，支持无认证、Bearer、API Key 和 Basic。
请求不会自动跟随重定向，会拦截 `localhost` 与私有/链路本地字面量地址，且请求 URL 必须
与数据源保持相同协议、主机和端口；响应体上限为 5 MB，数据集行数和超时仍受统一的
5,000 行与 300 秒上限约束。部署时仍应在网络出口层配置 DNS 解析和内网访问控制。
HTTP API 数据源没有数据库 Schema 或 SQL 调试页，使用 API 数据集请求定义进行预览和查询。

## 文件数据集与 DuckDB

Studio 可以上传 CSV、Excel（`.xlsx`）、JSON 对象数组和 Parquet 文件。上传后会
显示最多 100 行样例；Excel 会列出工作簿中的 Sheet，并允许在创建数据集前切换
预览。文件数据集创建后可以修改名称、最大行数和查询超时。删除数据集不会自动
删除源文件；仍被数据集引用的文件不能删除。

DuckDB 只负责 DataPulse 托管文件的本地分析查询。SQLite、PostgreSQL、MySQL /
MariaDB 等外部数据库始终走各自的原生异步连接器，DuckDB 不充当数据库代理。
文件路径由服务端控制，接口不会返回存储绝对路径。相关资源限制可通过
`DATAPULSE_FILE_MAX_BYTES`、`DATAPULSE_FILE_MAX_ROWS`、
`DATAPULSE_DUCKDB_THREADS`、`DATAPULSE_DUCKDB_MEMORY_LIMIT` 和
`DATAPULSE_DUCKDB_TIMEOUT_SECONDS` 配置。

## AI 分析与大屏生成

DataPulse 使用 OpenAI-compatible `/chat/completions` 接口。默认关闭 AI；启用时
至少配置以下变量：

```bash
DATAPULSE_AI_ENABLED=true
DATAPULSE_AI_BASE_URL=https://your-ai-provider.example/v1
DATAPULSE_AI_API_KEY=replace-with-secret
DATAPULSE_AI_MODEL=your-model
DATAPULSE_AI_TIMEOUT_SECONDS=30
DATAPULSE_AI_MAX_CONTEXT_ROWS=100
```

单次分析、整屏生成或局部修改的问题最长 4000 字符；分析和整屏生成最多选择 8 个
数据集，局部修改最多选择 8 个组件和 8 个数据集。每个数据集发送给模型的上下文最多
100 行和 50 个字段。上下文包含数据集名称、字段结构和受限的
样例数据，因此使用第三方模型服务前必须确认数据分类、脱敏、跨境传输和供应商
留存策略符合组织要求。API Key、数据库连接密码和文件绝对路径不会放入模型
上下文。模型返回的字段、数据集、组件类型、组件边界和编辑命令都会由服务端再次校验，
非法输出不会创建或修改草稿。

## 大屏播放与系统嵌入

独立播放适合电视、展厅和无人值守浏览器。管理员发布大屏后调用
`POST /api/admin/screens/{screen_id}/display-key` 生成显示密钥，再打开：

```text
/play/{screen_id}?key=<display-key>
```

页面会立即从地址栏移除密钥并换取仅限 `/api/player` 的 HttpOnly 会话。
再次生成显示密钥会立即撤销旧密钥和旧播放会话。

系统嵌入由宿主后端持有 API Key。管理员调用
`POST /api/admin/embed/api-key` 轮换宿主 API Key；宿主后端使用该 Key 调用
`POST /api/embed/tickets`，为一个大屏、一个 HTTPS Origin 和一组参数签发最长
8 小时的短票据。API Key 和票据都不应下发到日志、持久化存储或 URL 之外的
第三方页面。

宿主前端使用 SDK 挂载：

```ts
import { DataPulseEmbed } from "@datapulse/embed-sdk";

const screen = DataPulseEmbed.mount(document.querySelector("#screen")!, {
  url: "https://datapulse.example.com/embed/screen-id",
  ticket,
});

await screen.setParameters({ region: "华东" });
screen.refresh();
const parameters = await screen.getParameters();
await screen.fullscreen();
screen.destroy();
```

SDK 和播放器会同时校验消息来源、窗口实例和请求 ID。票据只在 iframe
首次启动时出现在 URL，随后立即移入内存并通过 Bearer 请求使用；不会写入
Cookie、Local Storage 或 Session Storage。查看者身份和业务权限仍由宿主系统
控制，DataPulse 只执行票据中明确授权的大屏和参数范围。

### 播放访问限制

管理员可以在已发布大屏的编辑器中配置访问限制，也可以调用：

```text
PATCH /api/admin/screens/{screen_id}/access-policy
```

`allowed_origins` 使用完整 Origin（包含协议、主机和非默认端口），
`allowed_ips` 支持单个 IP 和 CIDR，每行或逗号分隔一个值。两组策略都为空时
表示不限制；配置后，域名 Origin 或 IP 任一命中即可访问，二者都未命中则拒绝。
策略校验使用服务端看到的直接 TCP 对端地址，不信任未明确配置的
`X-Forwarded-For` 等代理头；部署在反向代理后时，应让网络层提供可验证的客户端
地址，或按代理实际对端地址配置策略。

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
