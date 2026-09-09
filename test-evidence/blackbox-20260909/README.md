# 2026-09-09 第二阶段黑盒证据索引

| 目录 | 结论 | 说明 |
| --- | --- | --- |
| `cross-browser/` | 通过 | Firefox/WebKit actual、diff、Chromium expected 与人工评审；最终完整复跑各 16/16 |
| `proxy-equivalent/` | 预检通过 | HTTPS Nginx、可信代理、Origin/Cookie/Storage/CSP 和日志脱敏；不替代目标生产代理链 |
| `display-target/` | 预检通过 | Retina/4K 最终图、指标和人工评审；过早 Canvas 图保留但不计通过 |
| `soak-preflight-60s/` | 通过 | 49/49 查询、无错误、堆最终下降 0.37 MB |
| `soak-preflight-10m-final/` | 预检通过 | 427/427 查询、最大并发 7、无错误、堆最终增长 1.27 MB |

真实密码管理器、目标生产代理链、物理 4K 和连续 8 小时播放没有目标环境证据，统一记阻塞。目录内不保留 Playwright trace；截图、JSON 和评审记录只包含 fixture 数据与脱敏结果。
