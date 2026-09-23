# 示例指标插件

从仓库根目录构建并打包：

```sh
pnpm --filter @datapulse/web exec vite build --config ../../examples/metric-plugin/vite.config.ts
python3 examples/metric-plugin/package.py
```

在“模板与插件”导入生成的 `dist/org.datapulse.example.metrics-1.0.0.zip`，核实来源后确认安装。进入大屏编辑器，在“已安装插件”添加“示例指标”。可在属性面板修改标签、数值字段、精度及颜色；数据面板选择固定数据、演示数据或授权的数据集。

发布后通过独立播放地址或 Embed 加载。发布文档保存 `org.datapulse.example.metrics@1.0.0`；安装新版本不会改写现有草稿或发布。示例不发起网络请求，只使用宿主传入的受控 `QueryResult`。

尝试升级时修改 manifest 的 `version` 并生成另一版本的包（同时修改打包输出文件名），不要用已安装版本覆盖不同内容。在编辑器“已安装插件”点击“草稿切换至 VERSION”；目标组件可定义同步 `migrate(props, fromVersion)` 返回完整的新配置。无迁移函数时旧配置必须满足新 schema。全部组件通过才更新草稿，失败不改变任何组件；成功后可撤销或选择旧版本验证降级。发布需要另外确认，旧发布保持原版本。

实际三浏览器回归：

```sh
pnpm test:e2e -- --project=chromium --project=firefox --project=webkit ecosystem.spec.ts
```

该用例重新构建网页和示例，将生产构建复制到临时后端目录，通过真实 `/embed` 路由验证 `script-src 'self' blob:`，同时检查查询结果、版本迁移、旧发布及 Embed Bearer 请求。SDK 仅提供类型和 `definePlugin` identity helper；运行时测试位于 `apps/web/src/features/ecosystem`。

插件属于管理员信任的同源代码。生命周期取消和组件错误边界用于清理与故障隔离，不是恶意代码沙箱。

参见 [SDK 合同](../../packages/plugin-sdk/README.md) 和 [安装与运维](../../docs/operations/ecosystem-plugins.md)。
