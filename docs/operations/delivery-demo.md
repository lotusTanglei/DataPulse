# 交付演示

## 一键部署

环境需要 Docker、Node.js 22、pnpm 10 和 uv。在仓库根目录运行：

```bash
pnpm demo:deploy
```

命令会创建被 Git 忽略且权限为 `0600` 的 `.env.demo`，生成互不相同的主密钥、签名密钥和演示管理员密码，构建单镜像，等待健康检查，并幂等导入仓库内的 `fixtures/demo/business.csv`。再次运行会复用原密钥、管理员和示例资源，不会轮换现有播放或嵌入凭据。

命令完成后输出 Studio URL、示例大屏 ID 和环境文件位置。管理员凭据只保存在 `.env.demo`，命令输出不包含密码或密钥。演示环境默认关闭 AI，规则推荐、数据接入、编辑、发布、独立播放和嵌入保持可用。

## 演示流程

1. 接入数据：在“数据集”中打开 `DataPulse 经营样例`，核对中文字段、类型画像和样例行。
2. 生成草稿：打开 `DataPulse 经营分析示例`，确认趋势图只绑定上述一个数据集，数字人播报引用趋势图的统一运行时结果。
3. 静态播报：保持无 TTS 配置，确认数字人显示由 `QueryResult` 派生的话术；浏览器语音不可用时字幕仍保留。
4. 发布：在编辑器中人工确认后发布。AI 预览或 AI 生成不会自动发布。
5. 独立播放：生成显示密钥并打开 `/play/{screen_id}?key=...`，确认密钥从地址栏移除。
6. 嵌入：轮换宿主 API Key，由宿主后端换取限定 Origin 的短票据，再用 Embed SDK 加载发布版本。
7. 权限：修改大屏 Origin 或 IP 策略，确认不匹配的既有票据返回 `EMBED_ORIGIN_DENIED`；恢复策略后重新验证。

## 一键复跑

以下命令在临时干净数据目录中执行迁移、导入固定样例、画像、创建草稿、静态播报降级、发布、独立播放、嵌入和权限拒绝，并输出不含凭据的 JSON：

```bash
pnpm demo:verify
```

需要归档证据时直接指定输出文件：

```bash
uv run --package datapulse-server python tools/run_delivery_demo.py \
  --output test-evidence/delivery/demo.json
```

该本地复跑证明功能闭环可重复执行，不替代目标网络、物理显示设备或人工计时的一日交付验收。
