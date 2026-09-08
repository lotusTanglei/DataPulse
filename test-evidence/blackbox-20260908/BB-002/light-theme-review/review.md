# 浅色主题视觉差异评审

- 日期：2026-09-08
- 触发原因：E2E fixture 仍使用已废弃的 `component_surface` / `component_border`，运行时实际读取 `panel_background` / `panel_border`，导致历史浅色基线保留深色面板并出现深色文字低对比度。
- 人工核对：`actual.png`、`diff.png`、`expected-before-fix.png` 已逐张查看。修正后的画面使用白色组件面板、深色正文、浅色边框和网格；标题、KPI、进度、图例、坐标轴、地图标尺及表格内容可读；组件位置、尺寸和查询结果未发生非预期变化。
- 决策：接受修正后的 `actual.png` 作为新的 Chromium Darwin `light-player.png` 基线。只更新该文件，不接受或更新 Firefox/WebKit 的编辑器差异。
- 原始失败日志：`test-evidence/automation-20260908/AUTO-026-light-theme-visual-diff.log`
- 可审计产物：`actual.png`、`diff.png`、`expected-before-fix.png`。原始 trace 可能包含临时播放会话值，脱敏审计后未保留。
