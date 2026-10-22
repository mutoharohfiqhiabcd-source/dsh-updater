v1.0.3 发布说明 —— **更新进度条 + 后台下载（不再卡 20 分钟超时）**

> 本文件是「最新一版」的更新说明，发布新版本前请改成当版内容。
> GitHub Actions 在推送 `v*` tag 时会把这个文件的内容作为 Release 说明（`body_path`）。
>
> v1.0.2 把桌面更新器的流程搬进了插件；v1.0.3 修掉它最难受的两个体验问题：
> **看不到进度**、**下载慢时会一直卡到超时**。

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

### 1. 下载/解压改成后台 worker —— 不再阻塞请求

之前：点「开始更新」后插件同步跑 Python 下载，网络慢就会一直卡在请求里，
最长 20 分钟超时（超时后下载进程还可能挂在后台）。

现在：`POST /update-source` 立刻返回，真正的下载/解压交给**脱离 DSH 的后台 worker**
（`python updater_core.py --json stage-source ...`），界面轮询 `/update-progress`
拿进度。HTTP 请求不会再超时。

### 2. 对话框里有实时进度条

进度来自 `updater_core.py` 写出的 `%APPDATA%\dsh-updater\update-progress.json`：

```
正在下载官方源码… 37% · 12.3 MB / 33.1 MB · 1.2 MB/s · 18s
[██████████░░░░░░░░░░░░░░░░]
下载期间可以取消；暂存完成后看护进程会自动关闭 DSH 并更新
```

覆盖：准备 → 下载 → 解压 → 暂存，每一步都有百分比、速度、剩余时间。

### 3. 下载期间可以「取消更新」

点对话框里的「取消更新」会结束后台 worker、清掉暂存目录、把进度标记为已取消。

### 4. 真的卡死会明确报错，而不是无限等

单次下载总时长上限 **15 分钟**：超过就报「下载超时（网络太慢）」，不会无声无息挂着。

### 5. 后续流程不变（仍是 v1.0.2 那套）

暂存完成后：按勾选自动关闭 DSH → 备份旧目录 → 换入新源码 → 按需
`pnpm install` / `pnpm run build` → 自动重启 DSH → 页面轮询到 DSH 恢复后自动刷新。
不勾自动关闭时仍是「提示你关 DSH → 关后自动应用 → 自动重启」。

## 🛠️ 技术细节

- `updater_core.py`：`download_file` / `_extract_zip_with_progress` 新增 `detail_cb`
  （结构化进度）与 `max_total`（总时长上限）；新增 `update-progress.json` 读写、
  `--json update-progress` 动作；`cancel-staged` 在还没有 manifest 时也能取消下载
- `index.js`：`/update-source` 对「正在运行的 DSH」改为 detached 后台 worker；
  新增 `GET /update-progress`（直接读文件，不启动 Python）；进度文件路径与
  `updater_core.py` 的 `_settings_dir()` 保持一致（支持 `DSH_UPDATER_SETTINGS_DIR`）
- `lib/client.js`：新增进度条组件与轮询；下载中可取消；「先断后连」逻辑确保
  DSH 重启完成后才刷新页面（不会刚断开就误刷新）
- 测试 183 → **187**（staged/failed 进度落盘、下载中取消杀 worker、进度 CLI）

## 📦 本版资产

| 文件 | 说明 |
|---|---|
| `DeepSeekHarnessUpdater.exe` | Windows 独立版桌面工具（无需 Python）。功能与 v1.0.2 一致，版本号同步 1.0.3 |
| `dsh-updater-src-v1.0.3.zip` | Python 源码版：解压后双击 `启动更新器.bat`，或运行 `python updater_gui.pyw`（需 Python 3.10+，含 tkinter）；同时附带 DSH 插件文件 |
| `SHA256.txt` | EXE 的 SHA256 校验值 |

> 网页版插件不在这些资产里：从 npm（`dsh-updater-plugin`）或本仓库直接安装即可。

## ⚠️ 注意

- 网页插件升级仍需「卸载 → 重新安装」并**重启 DSH**（Host 半边不会热替换）
- 更新下载需要能访问 GitHub；网络不好时会走得慢，但现在能看到进度、也能取消
- 自动关闭模式会让当前 DSH 会话短暂断开（会话记录不受影响），重启后页面自动刷新
- 桌面更新器 / Python 源码版 / DSH 插件三条线版本号统一为 **1.0.3**
