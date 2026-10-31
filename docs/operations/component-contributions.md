# 组件贡献规范

DataPulse 组件必须通过同一份版本化合同进入编辑器、播放页和发布校验。内置组件在
`apps/web/src/features/runtime/registry.ts` 注册；第二、三批组件集中在
`apps/web/src/features/runtime/builtins/advancedComponents.ts`。外部组件使用离线插件
机制，安装与升级流程见 [离线模板目录与组件插件](ecosystem-plugins.md)。

## 合同

每个新增内置组件必须声明 `ComponentContract`：

- `schema_version` 当前固定为 `1`；合同结构不兼容时才提升该版本。
- `version` 使用 SemVer。props 或数据输入出现不兼容变更时提升主版本；兼容新增字段提升
  次版本；不改变合同的修复提升补丁版本。
- `type` 使用唯一的 `builtin.snake_case` 名称，注册后不得把同一名称改作其他语义。
- `props_schema` 和 `data_input_schema` 都是对象 JSON Schema，明确 properties、required
  和是否允许额外字段。
- `defaultProps` 必须通过 `props_schema`，并能在无人工配置时产生可辨识的标题、空态和格式。
- `defaultStyle` 使用主题令牌，显式提供背景、边框、文字和图表颜色的回退值。

公共合同由 `apps/server/src/datapulse/contracts/component.py` 定义。修改后必须运行
`pnpm generate:contracts`，提交 `packages/schema/schemas/component-contract.schema.json`、
`packages/schema/src/generated/component-contract.d.ts` 和更新后的导出文件。

## 数据边界

一个组件只能有一个 `data_binding`，且只能引用一个数据集。组件不得接收 dataset ID
数组、执行跨数据集 join，或在浏览器中自行请求第二个来源。需要合并数据时，先在源库建立
视图，或由上游接口返回合并结果，再通过现有 HTTP API 数据集接入。

组件只消费运行时提供的 `QueryResult`。计算、格式化和交互必须是确定性逻辑，不执行用户
输入代码。AI 模块不是组件依赖；无 AI 构建中的组件、规则推荐、编辑、发布和播放必须完整
可用。生成或迁移只能修改草稿，不能自动发布。

## 实现要求

1. 在注册表声明名称、分类、默认尺寸、默认属性、默认样式、属性控件和版本化合同。
2. 数据组件为演示模式提供固定 seed 的确定性数据，字段顺序与 `data_input_schema` 一致。
3. 支持 loading、empty、error 和正常数据四种状态；单组件异常由宿主隔离。
4. 尺寸和文字在组件最小尺寸内不溢出；数值、日期和空值使用共享格式化函数。
5. 使用资源的组件必须通过受控 `loadAsset`，并在服务端声明允许的资产类型。
6. 数据组件必须在发布服务声明允许的现有 `ChartType`；无数据组件不得接受数据绑定。

## 合并门槛

每个组件必须同时具备以下证据：

- 单元测试：注册、合同、正常渲染、空态/错误态及关键交互；测试不得留下未处理异常。
- 发布测试：草稿能通过发布校验，错误资产、属性或数据输入会被拒绝。
- 视觉回归：Chromium 基线覆盖默认外观；只在人工检查 actual/diff 后更新快照。
- E2E：至少一条真实浏览器路径覆盖创建草稿、发布和播放，并检查无组件降级提示。
- 完整门禁：仓库根目录的 `pnpm verify` 通过。

第二、三批组件的集中验收命令：

```sh
uv run --package datapulse-server pytest \
  apps/server/tests/contracts/test_component.py \
  apps/server/tests/screen/test_publishing.py -q
pnpm --filter @datapulse/web exec vitest run \
  src/features/runtime/builtins/advanced-components.test.ts
pnpm test:e2e -- advanced-components.spec.ts
pnpm verify
```

评审不得仅接受截图或手工演示。合同、单数据源限制、发布校验、自动化测试和视觉基线缺少
任意一项时，组件不能进入默认注册表或模板槽位。
