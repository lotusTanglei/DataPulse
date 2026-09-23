# 离线模板目录与组件插件

DataPulse 的“模板与插件”是本实例的离线目录。管理员上传 ZIP，检查来源、许可证和版本后确认安装；编辑者可使用已安装组件、应用模板和显式切换草稿版本。安装和卸载需要管理员身份及 CSRF 校验。插件是管理员信任的同源 JavaScript，组件错误边界和取消信号用于故障隔离与清理，不构成恶意代码沙箱。

## 安装包

插件 ZIP 在根目录包含 `manifest.json` 和自包含的 `.mjs` 入口。构建工具应把依赖打进入口；运行时通过临时 blob URL 导入模块，不能依赖相对模块导入或远端模块。插件只从宿主接收配置、受控 QueryResult、状态、主题和取消信号，无需数据源凭据。

```json
{
  "schema_version": 1,
  "id": "org.example.metrics",
  "version": "1.0.0",
  "compatible_api": ">=1,<2",
  "name": "Metrics",
  "description": "A locally reviewed metric component",
  "source": "internal team",
  "license": "MIT",
  "entry": "index.mjs",
  "components": [{
    "type": "org.example.metric",
    "name": "Metric",
    "category": "Data",
    "default_props": {"label": "Total"},
    "property_schema": {
      "type": "object",
      "properties": {"label": {"type": "string"}},
      "required": ["label"],
      "additionalProperties": false
    },
    "data_schema": {"type": "object", "required": ["columns", "rows"]}
  }]
}
```

ID 和组件类型使用反向域名格式，版本使用语义版本。`compatible_api` 使用 Python packaging 的版本范围，当前宿主 API 为 `1.0.0`。内置 `builtin.*` 类型不可覆盖，不同插件不能声明相同组件类型。

属性和数据 schema 均采用 JSON Schema Draft 7，支持包内 `definitions`/`$ref`，不允许远端引用、新版 dialect 或未知关键字。`format` 和其他 annotation 不作为断言，不自动填充 `default`。浏览器使用解释执行的 validator，不需要 `unsafe-eval`；后端安装及保存/发布验证属性，宿主在调用插件前验证属性及非空 QueryResult。属性面板为 string、number/integer、boolean 和 enum 生成控件，嵌套配置仍受完整 schema 约束。

上传限制为 20 MiB，解压总量 50 MiB，单文件 10 MiB，最多 256 个成员，压缩比不得超过 100。目录成员、符号链接、绝对路径、父路径、重复或大小写冲突、文件/目录冲突及加密 ZIP 都会被拒绝。安装在私有暂存目录完成解包和校验后原子移动，不保留失败的半成品。

目录记录包 SHA-256、各文件哈希和安装时间。相同 ID/版本只能对应相同 ZIP 字节，重复上传同一包是幂等操作；修改内容必须使用新版本。保留最初发布的 ZIP，重新打包即使源码相同也可能改变 ZIP 哈希。

## 使用、升级与回退

1. 在“模板与插件”上传 ZIP、勾选信任确认并安装。
2. 打开大屏编辑器，在“已安装插件”添加组件。首次添加同时将精确 `{id, version}` 写入草稿依赖。
3. 在属性面板配置，在数据面板绑定固定数据、演示数据或授权数据集。检查预览，再单独发布。
4. 升级时先安装新版本，在“已安装插件”点击“草稿切换至 VERSION”。这会加载目标入口，对该插件的所有组件调用目标版本可选的 `migrate(props, fromVersion)`，然后校验每份新配置。
5. 仅所有组件成功时，依赖版本和完整 props 才作为一次可撤销操作写入草稿。任何迁移异常、组件被目标版本删除、schema 不通过或加载期间草稿有修改，都会保留原草稿。布局、绑定和组件 ID 保留。
6. 检查迁移后的预览及自动保存结果，再决定是否发布。撤销/重做作用于整次迁移；也可选择较旧的已安装版本，按同样流程验证降级。目标版本必须能处理当前 props，否则需要提供对应迁移逻辑。

安装、草稿版本切换和撤销都不会改写已有发布。独立播放和 Embed 始终读取发布文档的精确版本；只有下一次主动发布才改变播放版本。旧版本仍被草稿、发布或模板引用时不能卸载，接口返回 `ECOSYSTEM_IN_USE`。解除所有引用后才能卸载。卸载保留版本哈希历史，原 ID/版本不能重用为另一份内容。

独立播放资源遵守已有播放授权。Embed 模块请求使用 Bearer ticket，不发送 Cookie，也不把 ticket 放进模块 URL；入口页面首次导航仍使用 Embed SDK 的 ticket 引导协议。后端 `/embed` 对带插件的发布设置 `script-src 'self' blob:`，不允许 `unsafe-eval`，且只向被授权文档提供其实际依赖的版本文件。

## 模板

模板 ZIP 包含 `manifest.json` 和 `document.json`。manifest 声明 `kind: "template"`、ID、版本、名称、API 范围，以及完整的 `datasets` 和 `assets` 原引用 ID 列表；这些列表必须与文档引用一致。含插件的模板需要先安装文档声明的精确插件依赖。

应用模板时为每个数据集和资产提供显式目标映射；服务端检查存在性和读取权限。原始 datasource ID、凭据字段、Bearer token、含凭据的 URL 及 token/API key 查询参数不能嵌入模板。组件 ID、组件之间的引用及分组 ID 在每次创建时重映射，交互参数名保留。创建的是新草稿，不会自动发布；安装模板本身不会创建大屏。

## 运维与验证

目录内容存放在数据目录的 `ecosystem/` 中。备份应覆盖 `packages/` 和 `history/`，并与屏幕元数据一起恢复，保留发布依赖及版本不可变约束；不要手工替换已安装版本的文件，资源读取会验证哈希。`.staging/` 为临时安装/移除内容，不能当作已安装目录恢复。

常见错误：`ECOSYSTEM_INVALID_PACKAGE` 表示包或 schema 不合法；`ECOSYSTEM_VERSION_CONFLICT` 表示同版本内容不同；`ECOSYSTEM_IN_USE` 表示仍被引用；`ECOSYSTEM_CORRUPT` 表示已安装内容与记录不一致。修复时恢复原始备份或安装新版本，不修改版本历史绕过检查。

从仓库根目录执行：

```sh
uv run --package datapulse-server pytest apps/server/tests/ecosystem -q
pnpm --filter @datapulse/plugin-sdk typecheck
pnpm --filter @datapulse/web test src/features/ecosystem
pnpm test:e2e -- --project=chromium --project=firefox --project=webkit ecosystem.spec.ts
```

浏览器用例构建当前网页和示例包，覆盖导入、组件配置、真实查询、发布、显式草稿升级及原发布保留，并让 iframe 加载后端生产 `/embed` 页面，验证 CSP 与凭据传输。无需外部服务。完整 SDK 合同见 [plugin-sdk](../../packages/plugin-sdk/README.md)，示例构建与操作见 [metric-plugin](../../examples/metric-plugin/README.md)。
