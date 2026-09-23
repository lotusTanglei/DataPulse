# 本地完整恢复演练记录

2026-09-21 在临时目录执行真实运维 CLI，加入数字人资源后的结果为 `1 passed in 12.57s`。这是一份小规模本地功能演练证据，不是目标部署环境验收或生产恢复时间承诺；八项目标环境 gate 仍保持 blocked。

复现命令：

```sh
uv run --package datapulse-server pytest apps/server/tests/operations/test_restore_rehearsal.py -q -s
```

测试通过 HTTP 初始化管理员，创建编辑者、带加密凭据的 SQLite 数据源、SQL/CSV 数据集、海报图片、独立数字人肖像、真实 WAV 录音、插件和已发布大屏。大屏包含确认过文字、摘要及音频时长的数字人录音配置。关闭 API 生命周期后，通过独立 Python 进程执行 `backup create`、`verify`、`inspect` 和 `restore --target <空目录> --maintenance`，再重建应用。

| 本次测量 | 值 |
| --- | --- |
| 账号 | 2 |
| 数据源 / 数据集 | 1 / 2 |
| SQL / CSV 行数 | 2 / 2 |
| 媒体资源 / 已发布大屏 / 插件 | 3 / 1 / 1 |
| 数字人组件 | 1 |
| 归档成员数 | 11 |
| 归档大小 | 300,683 字节 |
| 清单中文件总大小 | 296,543 字节 |
| CLI 备份耗时（含进程启动） | 0.933 秒 |
| CLI 恢复耗时（含校验及进程启动） | 1.037 秒 |
| 恢复后应用启动次数 | 2 |

恢复后验证管理员登录、SQL 与 CSV 的真实查询结果、三份媒体的原始字节、插件版本和已发布文档。编辑者凭原有账号登录，其资源授权和传递依赖仍有效，可以编辑并重新发布。随后重新生成显示密钥与 Embed API Key/Ticket，独立播放和 Embed 均验证文档、数据查询、数字人肖像与录音 ID、媒体类型、逐字节内容及被声明的插件文件。关闭应用并再次启动后，编辑结果、查询、新播放凭证以及数字人肖像和 WAV 资源请求继续有效。此处验证资源恢复及传输，不宣称浏览器真实发声或外部 TTS 供应商通过验收。

原管理员会话、显示密钥、Embed API Key 和旧 Ticket 均返回 401。恢复时单独提供原始主密钥，确认数据源凭据可正确解密；签名密钥独立生成并在恢复后轮换。密钥不存放于归档目录。测试检查归档不含 `.env`、`.key`、`.log` 文件，并断言 CLI 标准输出、标准错误及证据 JSON 均不包含所用密钥、密码、会话或播放令牌。

测试在临时目录留下 `rehearsal-evidence.json`，标准输出用 `RESTORE_REHEARSAL` 前缀输出同样的无秘密测量字段。每次运行重新生成随机测试秘密与资源 ID，归档字节数和耗时会略有变化。

完整本地日志为 `test-evidence/phase-four/local-20260921/restore-rehearsal-digital-human.log`，提取后的测量字段为 `restore-rehearsal-digital-human.json`。账号、授权、编辑发布、独立播放、Embed、数字人媒体、插件及第二次启动均重新验证。
