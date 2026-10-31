# 场景案例库

案例使用仓库固定 fixture、现有模板和单数据集组件合同，可随 `pnpm verify` 重复验证。脏数据用于画像和质量提示，不在案例层执行清洗代码或跨数据集 join。

| 场景 | 文档 | 模板 | 数据 |
| --- | --- | --- | --- |
| 经营分析 | [business.md](business.md) | `overview-grid` | `fixtures/golden/business/data.csv` |
| 运营监控 | [operations.md](operations.md) | `analysis-lab` | `fixtures/golden/operations/data.csv` |
| 销售分析 | [sales.md](sales.md) | `comparison-board` | `fixtures/golden/sales/data.csv` |
| 设备监控 | [equipment.md](equipment.md) | `status-wall` | `fixtures/golden/equipment/data.csv` |

清单合同位于 `fixtures/scenarios/manifest.json`，验证命令：

```bash
uv run --package datapulse-server pytest apps/server/tests/quality/test_scenario_fixtures.py
```
