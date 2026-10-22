v1.0.1 发布说明 —— **「更新」按钮直接弹出桌面更新器窗口**

> 本文件是「最新一版」的更新说明，发布新版本前请改成当版内容。
> GitHub Actions 在推送 `v*` tag 时会把这个文件的内容作为 Release 说明（`body_path`）。
>
> v1.0.0 是首个「完善版」；v1.0.1 修掉插件「更新」入口的几个问题，让更新 DSH 本体
> 回到桌面版那套成熟流程上。

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

### 1. 「检测」按钮改名「更新器」

标题栏三个按钮现在是「**更新器 / 回滚 / 版本**」，面板标题简化为「**DSH 自动更新器**」。
检测本来就是为了更新，不必再分开叫。

### 2. 「更新」按钮 → 直接弹出桌面更新器窗口

| | 之前（v1.0.0） | 现在（v1.0.1） |
| --- | --- | --- |
| 点「更新」后 | 插件自己下载暂存，提示你关 DSH，再靠看护进程替换 | **直接弹出桌面更新器窗口（EXE）** |
| 更新流程 | 插件内两段式：暂存 → 关 DSH → 替换+构建+重启 | 桌面版完整流程：检测 DSH 在跑 → 询问后自动关闭 DSH → 备份旧目录 → 下载官方源码 → 整目录替换（可选 `pnpm install` / `pnpm run build`） |
| 适合谁 | 习惯「插件自己搞定」的人 | 想直接更新 DSH 本体、且复用桌面版成熟流程的人 |

> 插件里找不到本地更新器 EXE 时，会自动**回退**到原来的插件内更新流程，不会点了没反应。

### 3. 更新器 EXE 永远挑最新的

profile 里配置的 `updaterPath` 可能指向很旧的构建（本机配置还指着一个 0.8.0 的 dist）。
现在会把「配置路径 + `searchDirs`」里的 EXE 全部找出来，按修改时间取**最新**的
（文件名带 updater / dsh 优先），不会再弹出旧版本。

### 4. 修复「点了更新报 `log is not defined`」

上一版（未发布到 npm 的开发提交）里接口返回 502、面板红字报错，**但 EXE 其实已经启动**。
v1.0.1 修好，现在正常返回 200，窗口弹出、提示正常显示。

## 📦 本版资产

| 文件 | 说明 |
|---|---|
| `DeepSeekHarnessUpdater.exe` | Windows 独立版桌面工具（无需 Python）。本版内容与 v1.0.0 功能一致，版本号同步为 1.0.1 |
| `dsh-updater-src-v1.0.1.zip` | Python 源码版：解压后双击 `启动更新器.bat`，或运行 `python updater_gui.pyw`（需 Python 3.10+，含 tkinter）；同时附带 DSH 插件文件 |
| `SHA256.txt` | EXE 的 SHA256 校验值 |

> 网页版插件不在这些资产里：从 npm（`dsh-updater-plugin`）或本仓库直接安装即可。

## ⚠️ 注意

- 网页插件升级仍需「卸载 → 重新安装」并**重启 DSH**（DSH 插件页不支持自动更新；
  Host 半边不会热替换，不重启会出现旧按钮 404 / 旧路径报错）
- 插件点「更新」弹出的桌面更新器会先关掉当前 DSH（有确认框），更新完重新打开 DSH 即可；
  会话记录不受影响
- 同一目录启动了多个 DSH 实例时，桌面更新器更新前需要把它们**全部关闭**
- 桌面更新器 / Python 源码版 / DSH 插件三条线版本号统一为 **1.0.1**
