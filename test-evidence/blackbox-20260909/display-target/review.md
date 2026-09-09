# Retina/4K 显示证据人工评审

- 日期：2026-09-09
- 代码基线：本地第二阶段提交 `08adadb`
- 环境：物理 3024×1964 Retina（DPR 2）与 3840×2160、DPR 2 Playwright 仿真；后者启用 `prefers-reduced-motion: reduce`

## 评审过程

首次 `physical-retina.png` 在 ECharts Canvas 入场动画结束前截取：折线仅绘制一段、柱状图高度不足、饼图接近一条竖线。该图另存为 `physical-retina-premature-canvas.png`，本次自动化结果不计视觉通过，也没有更新任何视觉快照。

修正采证等待时间后执行 `AUTO-032-display-target-stable-canvas-final.log`，2/2 通过。人工查看最终 `physical-retina.png` 和 `emulated-4k.png`：折线、柱状、饼图和地图均已完整绘制；标题、KPI、进度、表格和图例可见；运行时保持 16:9；文档无水平或垂直溢出。4K 减少动效图在首帧直接呈现完整图表。

## 结论

真实 Retina 高 DPI 抽样和 4K 高 DPI 仿真预检通过。当前设备物理分辨率不足 3840×2160，因此物理 4K 门禁仍阻塞；仿真不替代该结论。
