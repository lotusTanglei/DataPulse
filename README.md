# DataPulse

DataPulse 是一个面向私有部署、系统嵌入和 AI 辅助分析的开源数据分析与大屏创作软件。它的目标是让分析人员通过可视化编辑与自然语言完成数据探索、图表生成和大屏发布，同时允许业务系统通过安全的 Web 嵌入方式承接身份与权限。

当前仓库处于“工程基础与协议”阶段，已经具备：

- FastAPI API 与 Vue 3 Web 工程骨架
- 仪表板、图表、数据集、AI 计划、插件和嵌入协议
- 从 Pydantic 确定性生成 JSON Schema 与 TypeScript 类型
- SPA 静态交付、Docker 镜像和持续集成基础

数据源连接、可视化编辑器、嵌入票据签发与校验、定时刷新和 AI 分析能力将在后续计划中实现。

## 环境要求

- Git
- [uv](https://docs.astral.sh/uv/)
- Node.js 22
- pnpm 10
- Docker（容器运行时需要）

## 本地开发

安装依赖：

```bash
uv sync --all-packages --group dev
pnpm install
```

启动后端：

```bash
uv run --package datapulse-server uvicorn datapulse.app:app --reload
```

启动 Web 开发服务器：

```bash
pnpm dev:web
```

Vite 默认把 `/api` 代理到 `http://127.0.0.1:8000`。

## 协议生成与验证

Python Pydantic 模型是协议的唯一源头。生成共享 JSON Schema 和 TypeScript 声明：

```bash
pnpm generate:contracts
```

检查生成物是否与模型同步：

```bash
pnpm check:contracts
```

执行完整本地验证：

```bash
pnpm verify
```

## 容器运行

```bash
docker compose up --build
```

服务启动后访问 `http://127.0.0.1:8000`，健康检查位于 `http://127.0.0.1:8000/api/health`。运行数据保存在名为 `datapulse-data` 的 Docker 卷中。

## 设计文档

产品愿景、范围边界与完整技术路线见[产品与技术路线设计](docs/superpowers/specs/2026-07-29-datapulse-product-technical-route-design.md)。

本项目采用 [Apache License 2.0](LICENSE)。
