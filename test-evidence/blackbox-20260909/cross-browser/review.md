# Firefox/WebKit 编辑器视觉基线评审

- 日期：2026-09-09
- 环境：macOS 26.6.2 arm64，Playwright 1.62.0，Firefox 153.0，WebKit 26.5。
- 前置修正：截图前等待组件查询结束，显式把左右编辑器面板滚动到顶部，并移除焦点状态。
- Firefox：与 Chromium Darwin 基线差 13,682 像素；修正前为 16,472 像素。实际图的组件库已回到顶部，画布、组件、数据、工具栏和属性面板完整，无重叠或缺失。
- WebKit：与 Chromium Darwin 基线差 18,400 像素。实际图结构与 Chromium 一致，差异集中在文字、图表 Canvas 和细线的引擎栅格化。
- 决策：接受两张 `editor-shell-actual-prebaseline.png` 分别作为 Firefox 和 WebKit 的 Darwin 独立基线。其他播放视觉断言继续使用已有公共基线，因为两种浏览器此前均已通过，避免无评审的批量快照更新。
- 审计产物：各浏览器目录保留 actual、diff 和 Chromium expected。建立独立基线后必须完整复跑 16 项，不能用本次定向结果代替。
