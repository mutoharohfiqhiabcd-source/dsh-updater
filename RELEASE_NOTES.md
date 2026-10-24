v1.0.4 发布说明 —— **慢网络也能更完：下载上限放宽到 10 小时**

> 本文件是「最新一版」的更新说明，发布新版本前请改成当版内容。
> GitHub Actions 在推送 `v*` tag 时会把这个文件的内容作为 Release 说明（`body_path`）。
>
> v1.0.3 把下载改成了后台任务并加了进度条；v1.0.4 根据实际网络情况，
> 把下载总时长上限从 15 分钟放宽到 **10 小时**，慢网也能挂着下完。

## 🔗 相关链接

| 名称 | 链接 |
| --- | --- |
| **本仓库（桌面版 + DSH 插件本体）** | <https://github.com/mutoharohfiqabcd-source/dsh-updater> |
| **npm 包页** | <https://www.npmjs.com/package/dsh-updater-plugin> |
| DSH 官方仓库（插件宿主） | <https://github.com/deepseek-ai/deepseek-harness> |
| 最新 Release 下载 | <https://github.com/mutoharohfiqabcd-source/dsh-updater/releases/latest> |
| 功能介绍推文 | <https://x.com/0ncv2l/status/2106351434749161735> |

安装（二选一，装完**重启 DSH**）：

```bat
:: 从 npm 安装 / 升级
dsh plugin --profile web add dsh-updater-plugin

:: 或从 GitHub 安装（安装地址一直没变）
dsh plugin --profile web add github:mutoharohfiqabcd-source/dsh-updater
```

## ⚡ 本版变化

### 1. 下载总时长上限：15 分钟 → **10 小时**

实测在很差的网络下，GitHub 官方 zip（约 43 MB）只有 14 KB/s，15 分钟连 1/3 都下不完，
直接被判「下载超时」太不友好。现在允许下载慢慢磨 **10 小时**：

- 后台 worker 不会因为时间被掐断；
- 对话框里的进度条一直显示百分比 / 已下载 / 速度 / 剩余时间；
- 不想等了随时点「**取消更新**」，立刻结束下载并清理暂存。

> 断网/连不上的情况仍会按正常网络错误快速失败（连接超时、TLS 错误等），
> 不会无意义地空等 10 小时。

### 2. 顺带修掉「DSH 重启后页面偶尔不自动刷新」

v1.0.3 的自动刷新逻辑要求先观察到「DSH 断开」再观察到「恢复」才刷新；
如果进度轮询晚到、页面晚打开，可能永远观察不到断开事件，页面就停在等待状态。
现在 12 秒内没观察到断开也会刷新一次（DSH 已重启完成时正好用上）。

## 🛠️ 技术细节

- `updater_core.py`：`_UPDATE_STAGE_DOWNLOAD_TIMEOUT` 900 → **36000** 秒；
  `download_file(max_total=...)` 逻辑不变，只是上限放宽
- `index.js`：非运行中目标的同步更新路由超时同步放宽到 10 小时；
  正在运行的目标仍走后台 worker（无请求超时）
- `lib/client.js`：`waiting-restart` 轮询增加 12 秒兜底刷新
- 测试 187 → **188**（断言下载上限 = 36000 秒）

## 📦 本版资产

| 文件 | 说明 |
|---|---|
| `DeepSeekHarnessUpdater.exe` | Windows 独立版桌面工具（无需 Python）。功能与 v1.0.3 一致，版本号同步 1.0.4 |
| `dsh-updater-src-v1.0.4.zip` | Python 源码版：解压后双击 `启动更新器.bat`，或运行 `python updater_gui.pyw`（需 Python 3.10+，含 tkinter）；同时附带 DSH 插件文件 |
| `SHA256.txt` | EXE 的 SHA256 校验值 |

> 网页版插件不在这些资产里：从 npm（`dsh-updater-plugin`）或本仓库直接安装即可。

## ⚠️ 注意

- 网页插件升级仍需「卸载 → 重新安装」并**重启 DSH**（Host 半边不会热替换）
- 更新下载需要能访问 GitHub；网络差时现在可以挂着慢慢下，也可以取消
- 自动关闭模式会让当前 DSH 会话短暂断开（会话记录不受影响），重启后页面自动刷新
- 桌面更新器 / Python 源码版 / DSH 插件三条线版本号统一为 **1.0.4**
