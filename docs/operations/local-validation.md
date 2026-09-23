# 本地容器与容量预检

下面的工具只使用临时 fixture，不连接目标生产环境。它验证容器启动、迁移、HTTP 功能、有限并发以及真实离线恢复；不能替代物理 4K、真实供应商、浏览器首屏或 8 小时验收。

```sh
docker build -t datapulse:phase-four-local .
uv run --package datapulse-server python tools/verify_phase_four_local.py \
  --image datapulse:phase-four-local \
  --evidence-dir test-evidence/phase-four/local-docker-UNIQUE
```

测试前固定资源为 2 核 CPU、4 GiB RAM、256 PID，50 个独立显示 Session 同时开始，各运行 5 次真实 CSV 数据集查询。共 250 次查询必须全部成功且内容正确，HTTP 查询 p95 不超过 3,000 ms。这是本地 HTTP 容量阈值，不是浏览器首屏指标；路线中约 3 秒首屏仍需浏览器和目标网络单独测量。

工具通过标准容器入口自动迁移、读取一次性初始化代码并完成初始化，创建 CSV、数据集、图片、大屏并发布。该一次性演练显式设置 `DATAPULSE_ENVIRONMENT=test`，传输仅使用 loopback HTTP；生产模式的 Secure Cookie 需要 TLS，仍由 P4-ENV-002 在实际代理链验证。首次用生产 Cookie 访问 HTTP 返回 401 的失败结果保留在证据中。随后停止 API，通过真实 CLI 创建和校验归档、恢复到空目录，重建容器并验证登录、查询、编辑、发布、独立播放、Embed 和图片字节，再重启复查持久化结果。随机密钥和密码只存活于临时环境文件和进程内存；输出只包含规模、资源、计时、状态与稳定错误类型。测试创建的容器和卷会在结束时清理。

Dockerfile 支持 `--build-arg NODE_IMAGE=...` 指定受控构建镜像，默认 `node:22-slim`。如果本地镜像仓库无法下载默认镜像，可使用已审查且包含 Node/Corepack 的缓存镜像做预检，必须记录实际镜像与 Node 版本，不将替代镜像的结果写成默认镜像通过。最终运行层仍使用 Dockerfile 的 Python 镜像。

# 请求日志、告警和扫描器

默认 Docker 入口关闭 Uvicorn 原始访问日志，应用为每个请求输出一行 JSON：时间、请求 ID、方法、路由模板、状态、耗时。路由模板不包含真实资源 ID；不记录正文、Cookie、Authorization 或 URL query。原始访问日志若在开发时开启，已有过滤器会脱敏 Ticket、显示 key 等常见凭据参数，但生产代理仍应直接省略 query string。

Prometheus 现有三个告警分别覆盖合成失败、任务失败比例和合成延迟。可先校验规则语法：

```sh
docker run --rm --entrypoint /bin/promtool \
  -v "$PWD/deploy/prometheus/datapulse-digital-human.yml:/rules.yml:ro" \
  prom/prometheus:v3.5.0 check rules /rules.yml
```

规则校验不能证明告警通知可达。目标环境需要配置实际 Alertmanager 接收器、演练告警、确认接收并保存脱敏证据；应用不代替组织的告警渠道和日志保留策略。

扫描器以 JSON argv 配置，例如 `DATAPULSE_UPLOAD_SCANNER_COMMAND=["/usr/bin/clamscan","--no-summary","--infected"]`，应用追加随机临时文件路径，不通过 shell 执行。默认镜像不包含 ClamAV，也不自动联网拉取病毒库；使用此配置前，在组织维护的派生镜像安装实际扫描器、供应签名库并验证退出码。`[]` 表示关闭扫描；一旦启用，感染、超时、程序不存在和非成功退出都会拒绝上传。实际恶意文件检测和签名更新策略仍需 P4-DH-004 验收。

处理器的 CPU、内存、并发和隔离限制见 [security-capacity.md](security-capacity.md)。子进程限额不代替整个容器的资源与出站网络限制。
