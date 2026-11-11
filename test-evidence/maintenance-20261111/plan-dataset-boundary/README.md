# Plan 数据集边界维护回归（2026-11-11）

原始红灯日志以 gzip 无损归档，使用 `gzip -cd focused-red.log.gz` 阅读；字节哈希与原退出码见 `../budget-guard/raw-log-archives.json`。

- **有证据**：旧 `PlanValidator` 只逐组件检查数据集；模型返回 `dataset_ids=("sales", "private")`、所有组件仍绑定 `sales` 时，生成器直接接受该 Plan。负向测试在原代码得到 `4 failed, 14 passed`，退出码 1，原始输出见 `focused-red.log.gz`。
- **有证据**：修复在现有 `screen/planning.py` 的共享校验器中补齐未被组件引用的数据集声明的授权及存在检查；沿用 `PLAN_DATASET_UNAUTHORIZED` / `PLAN_DATASET_UNKNOWN`，报告 `dataset_ids[index]`。已有组件错误定位不变。
- **有证据**：回归覆盖未授权声明、已授权但不存在声明、已授权存在且未使用声明、生成器修复重试及三次失败后的拒绝。保持未使用但有效的数据集声明兼容，不增加产品能力。
- **有证据**：修复后连同既有文档编译和规划服务回归共 35 passed，退出码 0，无跳过；见 `focused-green.log`。
- **推断**：该缺陷使模型返回 Plan 超出用户所选数据集范围；此证据不证明 HTTP 资源授权被绕过。HTTP 身份层另有 `identity/service.py::check_references` 对客户端提交引用的检查。

## 复跑命令

红灯（新增回归，修改校验器之前）：

```sh
uv run --package datapulse-server pytest apps/server/tests/screen/test_plan_validator.py apps/server/tests/ai/test_plan_generator.py -q
```

绿灯（修复之后）：

```sh
uv run --package datapulse-server pytest apps/server/tests/screen/test_plan_validator.py apps/server/tests/ai/test_plan_generator.py apps/server/tests/screen/test_document_compiler.py apps/server/tests/screen/test_planning_service.py -q
```

完整 `pnpm verify` 及静态检查由本轮成本保护维护记录统一绑定。以上测试使用本地 fixture，不请求真实供应商，不代表 M1/M2 真实模型质量通过；用户已要求真实模型配置先等一等。没有执行 P4 目标环境验收。
