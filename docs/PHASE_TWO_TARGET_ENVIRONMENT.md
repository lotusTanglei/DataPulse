# 产品第二阶段目标环境门禁

日期：2026-09-09

这些用例只用于关闭产品第二阶段的环境验收缺口。自动化仿真、开发代理和短时预检可以提前发现缺陷，但不能替代本文件明确要求的真实目标环境。

## 通用规则

- 使用专用测试账号、随机密钥、fixture 数据和隔离数据库；禁止生产凭据、客户数据和真实 AI provider。
- 每项记录提交、操作系统、浏览器及版本、部署拓扑、显示设备、开始/结束时间、命令退出码和脱敏证据路径。
- 失败、skip、deselect、仿真结果或未完成的人工步骤不能计为通过。
- URL、Cookie、Local/Session Storage、请求/响应头、代理日志和应用日志都要检查；证据中不得保留 display key、API key、ticket、Session、数据库密码或初始化代码。

## 真实密码管理器

前置条件：目标 Chrome/Safari/Firefox 与组织实际使用的密码管理器，建立全新浏览器配置，仅保存专用 DataPulse 管理员测试凭据。

1. 证明登录页能够填入并提交管理员凭据。
2. 登录后分别打开 PostgreSQL 和 MySQL/MariaDB 的新建、编辑表单。
3. 确认数据库用户名和密码没有被管理员凭据填入；编辑密码保持空白。
4. 检查页面、Network、URL 与 Storage，不得出现管理员密码。
5. 至少对组织支持矩阵中的每种密码管理器执行一次；浏览器原生密码存储和扩展式密码管理器分别计结果。

关闭条件：所有目标组合通过并有截图、浏览器版本、表单值摘要和脱敏 Network 证据。当前自动化只固定 `autocomplete` 契约，不能关闭此门禁。

## 生产反向代理与 CSP

DataPulse 容器只信任 `DATAPULSE_FORWARDED_ALLOW_IPS` 指定的代理地址。保持默认 `127.0.0.1`，除非前方确有可信代理；禁止配置为 `*`。代理必须覆盖客户端传入的 `X-Forwarded-For`、`X-Real-IP` 和 `X-Forwarded-Proto`，不能追加不可信链；参考 `deploy/nginx/datapulse.conf`。

本地生产等价预检：

```bash
uv run --package datapulse-server python tools/verify_proxy_boundary.py \
  --evidence-dir test-evidence/blackbox-YYYYMMDD/proxy-equivalent
```

目标环境还必须复核：

1. HTTPS Studio 的写请求不出现 `AUTH_ORIGIN_INVALID`，Session/CSRF Cookie 为 Secure。
2. 伪造转发头不能绕过 IP 策略；允许/拒绝的真实客户端 IP 符合负载均衡器和代理链定义。
3. `/embed/{id}` 与嵌入 API 保留精确 `frame-ancestors`、`no-store`、`no-referrer` 和 `nosniff`。
4. WAF/CDN/代理不缓存播放或嵌入响应，不改宽 CSP，不把 query string 写入访问日志。
5. 应用日志中的 ticket 只能显示 `[REDACTED]`；display key、API key、Session 和数据库凭据均不出现。

关闭条件：在将要上线的完整代理链执行，而不是只在本机 Nginx 预检通过。

## 物理 4K 与高 DPI

目标设备必须报告至少 3840×2160 物理分辨率和实际 DPR；远程桌面缩放、无头浏览器或 Playwright `deviceScaleFactor` 仿真不能替代。

```bash
pnpm --filter @datapulse/web exec playwright install chromium
pnpm test:e2e:display
```

人工核对深色/浅色的编辑器、草稿预览、独立播放和嵌入：标题、坐标、图例、表格、图片和地图清晰；16:9 contain 留白正确；无重叠、裁切、横向滚动或空白 Canvas；系统“减少动效”开启时图表首帧完整且不播放入场动画。

关闭条件：物理 4K 设备截图/照片、系统显示信息、DPR 指标和人工核对记录齐全。3024×1964 Retina 可以关闭高 DPI 抽样，但不能关闭 4K 子项。

## 长期播放

第二阶段门禁时长固定为连续 8 小时。使用目标浏览器、目标代理和接近上线的刷新策略；浏览器窗口保持前台或使用部署时实际的 kiosk 模式。

```bash
DATAPULSE_E2E_SOAK_SECONDS=28800 \
DATAPULSE_TARGET_EVIDENCE_DIR=test-evidence/blackbox-YYYYMMDD/soak \
pnpm test:e2e:soak
```

通过标准：进程不中断；所有查询完成且无失败；最大并发不超过单轮 7 个绑定组件；无残留 loading/错误；标题和数据组件持续可见；每分钟 JS 堆采样无持续失控增长且总增长低于 128 MiB。另用目标系统监控记录浏览器 RSS、CPU、页面崩溃和网络重连。

关闭条件：完整 8 小时退出码为 0，并保存指标 JSON、结束截图、浏览器资源趋势和代理/应用脱敏日志。10 分钟预检不能计为长期播放通过。

## 2026-09-09 本地预检记录

- 生产等价 HTTPS Nginx：通过；结果见 `test-evidence/blackbox-20260909/proxy-equivalent/result.json`。
- 3024×1964 Retina、DPR 2 和 3840×2160、DPR 2 仿真：最终自动化 2/2，通过人工视觉复核；首张过早截取的 Canvas 证据保留但不计通过。
- 60 秒浸泡：49/49 次查询完成，无错误；10 分钟浸泡：427/427 次完成、最大并发 7、JS 堆最终增长 1.27 MB，无请求、页面或 console 错误。
- 上述三组仅为预检。真实密码管理器、目标生产代理链、物理 4K 和连续 8 小时仍为阻塞，不能据此标记第二阶段完成。
