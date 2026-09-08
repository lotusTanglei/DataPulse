# 2026-09-08 黑盒证据索引

- `BB-001/`：折线点击联动、10 秒刷新、URL 清理和查询计数。
- `BB-002/`：编辑器/播放多视口与主题；`light-theme-review/` 保存浅色 fixture 修复前后 actual/diff/旧 expected 和人工评审说明。
- `BB-003/`：单组件查询失败隔离和恢复。
- `BB-004/`：display key、Cookie、Embed Bearer、Origin、Storage、CSP 与过期 ticket 的脱敏摘要。
- `BB-005/`：查询/网络失败终态和恢复终态。
- `BB-006/`：草稿、published 快照和刷新后一致性。
- `cross-browser/`：Firefox/WebKit 的 actual/diff/expected 与脱敏错误上下文；未更新这些浏览器的视觉基线。原始 trace 可能含临时会话值，未保留。

BB-001～BB-006 是隔离 Chromium 环境中的等价可审计验证，不替代真实密码管理器、生产反向代理、4K/高 DPI、长期播放或跨浏览器人工验收。JSON 不保存 key、ticket、Cookie 值、凭据、SQL、文件存储路径或客户数据。
