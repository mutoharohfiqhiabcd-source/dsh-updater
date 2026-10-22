v1.0.2 发布说明 —— **插件内更新对话框：复刻桌面更新器的完整体验**

> 本文件是「最新一版」的更新说明，发布新版本前请改成当版内容。
> GitHub Actions 在推送 `v*` tag 时会把这个文件的内容作为 Release 说明（`body_path`）。
>
> v1.0.1 把「更新」按钮改成弹桌面 EXE；v1.0.2 再往前走一步：**插件自己把桌面更新器的
> 流程复刻出来**——不用离开 DSH，就能完成「下载 → 关 DSH → 替换 → 构建 → 重启 DSH」。

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

### 1. 点「更新」→ 插件内更新对话框（不再直接弹 EXE）

对话框里和桌面版一样有：

| 项目 | 说明 |
|---|---|
| 目标目录 | 要更新的源码检出（运行时 profile 会指向同一个检出） |
| 版本 | 当前版本 → 官方最新版本 |
| ✅ 更新时自动关闭 DSH | 看护进程会自动结束 DSH（只结束占用端口的 PID），完成后自动重启 |
| ☐ 替换后运行 `pnpm install` | 依赖有变化时建议勾选 |
| ☐ 替换后运行 `pnpm run build` | 用源码版启动 DSH 时必需 |
| 按钮 | **开始更新** / 关闭 / **改用桌面更新器**（仍然可以启动 EXE） |

### 2. 勾「自动关闭 DSH」后的完整流程（复刻桌面版）

1. 插件下载官方源码到暂存目录（页面显示提示，可能要几分钟）；
2. 后台看护进程（脱离 DSH 独立存活）等 3 秒后**自动关闭 DSH**；
3. 备份旧目录 → 换入新源码 → 搬回 `node_modules` / `.git` → 按需 `pnpm install` / `pnpm run build`；
4. 用原来的启动参数**自动重新启动 DSH**；
5. 页面轮询到 DSH 重新监听端口后**自动刷新**，看到的就是新版本。

> 仍保留手动模式：不勾「自动关闭 DSH」时，流程变成「提示你关 DSH → 关闭后自动应用 → 自动重启」。

### 3. 安全细节

- 自动关闭**只对占用端口的 PID 发 SIGTERM**，不用 `taskkill /T`——看护进程是 DSH 的
  子进程，`/T` 会把它自己一起杀掉，导致更新卡死；
- 旧目录整目录备份，构建失败自动回滚到旧版本再重启 DSH（不会「DSH 被弄没」）；
- 目录被别的实例占用时保留暂存更新，界面提供「重试应用」，不用重新下载；
- 暂存后、关闭 DSH 前仍可「取消更新」。

## 📦 本版资产

| 文件 | 说明 |
|---|---|
| `DeepSeekHarnessUpdater.exe` | Windows 独立版桌面工具（无需 Python）。功能与 v1.0.1 一致，版本号同步 1.0.2 |
| `dsh-updater-src-v1.0.2.zip` | Python 源码版：解压后双击 `启动更新器.bat`，或运行 `python updater_gui.pyw`（需 Python 3.10+，含 tkinter）；同时附带 DSH 插件文件 |
| `SHA256.txt` | EXE 的 SHA256 校验值 |

> 网页版插件不在这些资产里：从 npm（`dsh-updater-plugin`）或本仓库直接安装即可。

## ⚠️ 注意

- 网页插件升级仍需「卸载 → 重新安装」并**重启 DSH**（Host 半边不会热替换）
- 自动关闭模式会让当前 DSH 会话短暂断开（会话记录不受影响），重启后页面自动刷新
- 同一目录启动了多个 DSH 实例时，建议先把它们都关掉再点更新（否则会进入「重试应用」）
- 更新期间需要能访问 GitHub（下载官方源码）；网络不好时下载会慢或失败，可稍后重试
- 桌面更新器 / Python 源码版 / DSH 插件三条线版本号统一为 **1.0.2**
