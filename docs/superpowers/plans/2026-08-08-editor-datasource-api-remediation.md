# Editor, Datasource, and API Data Sources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复大屏编辑与发布体验、提升 SQL 数据源可用性，并交付首版 HTTP API 数据源能力。
**Architecture:** 保留现有 FastAPI + SQLAlchemy/原生连接器 + Vue 工作台架构；Moveable 在未变换根容器中处理交互，Schema 预览由后端安全生成查询，HTTP API 作为独立连接器并复用 QueryResult。
**Tech Stack:** Python 3.12、FastAPI、Pydantic、httpx、pytest；Vue 3、TypeScript、Vite、Vitest、Moveable、Selecto。

## 全局约束

- [ ] 所有用户可见文案使用中文；保留协议字段和代码标识的英文。
- [ ] 不回显或记录数据库密码、API token、Basic 密码；不修改已有 `docs/known-issues.md` 历史记录。
- [ ] 每个任务先写失败测试，再修改实现；测试失败时停止并定位根因。
- [ ] 不引入多用户协作、复杂权限、模板市场或设备管理。

---

## 任务 1：MariaDB Schema 元数据兼容

- [ ] 为 MySQL 连接器增加回归测试，覆盖 `CHECK_CONSTRAINTS` 不含 `TABLE_NAME` 的 MariaDB 结构，并断言使用约束表关联查询。
- [ ] 将 `describe_relation` 的检查约束查询改为 `CHECK_CONSTRAINTS` 与 `TABLE_CONSTRAINTS` 的兼容 JOIN。
- [ ] 运行 `uv run --package datapulse-server pytest apps/server/tests/connectors/test_mysql.py -q`。

## 任务 2：安全的表数据预览

- [ ] 为数据源 API 增加 relation preview 测试：关系存在时返回统一 `QueryResult`，不存在或 limit 越界时返回可读错误。
- [ ] 在连接器协议和 SQL 连接器实现安全的标识符引用与 limit 参数；禁止前端传入任意 SQL。
- [ ] 增加 `GET /api/admin/datasources/{id}/relation/preview` 路由。
- [ ] Schema 浏览器增加“预览数据”操作和行表格，默认 100 行并显示加载/空态/错误态。
- [ ] 增加前后端测试并运行 datasource 相关测试。

## 任务 3：禁用数据源表单凭据自动填充

- [ ] 先补充新建和编辑表单的 autocomplete 回归测试，确保用户名/密码字段不会使用登录表单语义。
- [ ] 调整表单和字段 autocomplete 属性；保留登录/初始化页面的正常密码管理器行为。
- [ ] 运行 `pnpm --filter @datapulse/web test -- datasource-form` 并做一次构建。

## 任务 4：修复缩放画布拖拽与缩放跟手

- [ ] 为拖拽坐标换算和 resize 视觉帧更新补充 Vitest 测试，覆盖 0.5、1、1.5 缩放。
- [ ] 配置 Moveable `rootContainer`、`zoom`，监听 `drag`/`resize` 实时更新 DOM，结束事件只提交逻辑坐标。
- [ ] 在缩放改变、选区改变和组件删除后调用 `updateRect`，避免控制框漂移。
- [ ] 运行 canvas 测试、类型检查和浏览器手动拖拽验证。

## 任务 5：发布后使用方式面板

- [ ] 增加发布成功后的使用方式状态和组件测试。
- [ ] 增加 display key 获取/复用 API；独立播放 URL 可复制和新窗口打开。
- [ ] 在面板中展示 iframe 嵌入示例、尺寸说明、宿主后端换取短期 ticket 的流程和安全提醒。
- [ ] 运行 player/screens 相关测试和构建。

## 任务 6：HTTP API 数据源后端 MVP

- [ ] 为 HTTP API 配置、密文载荷和连接器协议补充模型测试，确保旧 SQL 配置反序列化不变。
- [ ] 实现 `http_api` 连接器：GET/POST、query/body/headers、Bearer/API Key/Basic、response path 到行数组映射。
- [ ] 实现请求安全策略：仅 HTTP/HTTPS、禁止 loopback/private/link-local/云元数据地址、超时、响应大小和重定向限制，敏感信息脱敏。
- [ ] 将 `RestQuery` 接入 DatasetService，输出现有 `QueryResult` 并支持手动/间隔刷新。
- [ ] 增加单元测试（mock httpx）和 API 集成测试。

## 任务 7：HTTP API 数据源前端闭环

- [ ] 数据源表单增加 HTTP API 类型及认证配置，密码/token 输入不回显。
- [ ] 数据集创建/编辑增加 API 查询配置、response path 和测试请求反馈。
- [ ] 增加前端表单/API 测试，运行全量 web test、typecheck、build。

## 任务 8：集成验证与交付

- [ ] 启动本地服务，浏览器验证编辑器拖拽、发布独立播放/嵌入提示、SQL 表预览和 HTTP API 数据集。
- [ ] 运行后端全量 pytest、前端全量测试、类型检查和生产构建。
- [ ] 检查 diff、敏感信息和迁移兼容性，按任务提交清晰 commit；只有验证通过后报告完成。
