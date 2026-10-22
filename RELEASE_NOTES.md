v0.10.0 发布说明 —— **在 DSH 插件里直接更新 DSH**

> 本文件是「最新一版」的更新说明，发布新版本前请改成当版内容。
> GitHub Actions 在推送 `v*` tag 时会把这个文件的内容作为 Release 说明（`body_path`）。

## 🔗 相关链接

| 名称 | 链接 |
| --- | --- |
| **本仓库（桌面版 + DSH 插件本体）** | <https://github.com/mutoharohfiqhiabcd-source/dsh-updater> |
| **npm 包页** | <https://www.npmjs.com/package/dsh-updater-plugin> |
| DSH 官方仓库（插件宿主） | <https://github.com/deepseek-ai/deepseek-harness> |
| 最新 Release 下载 | <https://github.com/mutoharohfiqhiabcd-source/dsh-updater/releases/latest> |
| 功能介绍推文 | <https://x.com/0ncv2l/status/2106351434749161735> |

安装（二选一，装完**重启 DSH**）：

```bat
:: 从 npm 安装
dsh plugin --profile web add dsh-updater-plugin

:: 或从 GitHub 安装（安装地址一直没变）
dsh plugin --profile web add github:mutoharohfiqhiabcd-source/dsh-updater
```

## ⚡ 本版新功能：在插件里点一下就能更新 DSH

「检测」面板里，**可更新的源码检出**那一行会多出一个「**更新**」按钮：

1. 点两下确认（第一次变「确认更新？」，第二次才执行）；
2. 插件自动下载官方源码并**暂存**（此时不碰正在运行的 DSH 目录）；
3. 完成后提示你**关闭 DSH**（同一目录开了多个实例就都关掉）；
4. 后台看护进程在 DSH 关闭后自动完成：整目录替换 → 按需 `pnpm install` →
   按需 `pnpm run build` → **自动重新启动 DSH**（约 2~5 分钟）；
5. 刷新页面，版本已经更新。

下载、替换、构建、重启的全过程都有日志（界面里会显示日志路径），
什么时候该关、关掉之后在干什么，都不用猜。

## 🧠 为什么不能「点完立刻在线替换」

Windows **不允许**对一个正被其他进程当作工作目录的目录改名（实测 `Move-Item`
直接报「文件正被另一进程使用」）。而 DSH 的源码检出正是它自己的运行目录，
所以只能拆成两段：

| 阶段 | 时机 | 做什么 |
|---|---|---|
| ① 暂存 | DSH 运行中（安全） | 下载官方源码 → 解压到目标同级暂存目录 → 写清单、启动看护进程 |
| ② 应用 | DSH 关闭后（看护进程） | 旧目录改名为备份 → 暂存目录换到位 → 恢复 node_modules/.git → 按需 install/build → 重启 DSH |

这样替换那一刻磁盘上的文件不会被任何进程占用，也才能保证「构建失败还能回到旧版本」。

## 🔒 安全设计（都是自动的）

- **旧目录整目录备份**：替换前改名成 `*.dsh-bak-时间戳`，更新失败自动回滚；
- **构建失败自动回滚**：`pnpm run build` 失败会把旧目录换回来，保证重启后一定能用；
- **目录被占用不判死刑**：如果关闭 DSH 后目录仍被别的实例占用，暂存更新会保留，
  界面提示「重试应用」——关掉占用进程再点一次即可，**不用重新下载**；
- **可取消**：暂存后、关闭 DSH 前可随时「取消更新」（会结束看护进程并清理暂存目录）；
- **换错目标不会乱动手**：应用前重新校验目标仍是 DSH 源码检出、版本与清单一致；
- 只处理**源码检出**；npm 全局安装不在本功能范围。
  **运行时 profile 如果其 `@deepseek-ai/dsh` 是指向源码检出的 junction（本机就是），
  那一行也会有「更新」按钮**——它更新的就是这个源码检出，更新并重启后，
  所有使用该运行时的 profile 都会变成新版本。

## 📋 使用步骤

| 步骤 | 你会看到 |
|---|---|
| 1. 检测 → 点「更新」→ 再点「确认更新？」 | 行尾变成「下载中…（可能要几分钟）」 |
| 2. 下载完成 | 面板顶部出现「更新包已就绪：旧版本 → 新版本」+ 关闭提示 |
| 3. 关闭 DSH（所有从该目录启动的实例） | ——（DSH 已退出，看护进程接手） |
| 4. 等待 2~5 分钟 | DSH 会自动重新启动 |
| 5. 刷新 DSH 页面 → 再点「检测」 | 版本已是最新，顶部显示「上次更新完成」 |

> 如果更新失败，DSH 也会被重新启动（旧版本），页面里会显示失败原因与日志路径，
> 旧版本备份还在，可以用「回滚」按钮退回去。

## 🛠️ 本版改动（技术细节）

- `updater_core.py`：新增 5 个 `--json` 动作 —— `stage-source` / `update-source` /
  `update-status` / `cancel-staged` / `resume-staged`；暂存、清单、看护进程、
  替换/回滚、自动重启都在核心层实现，**桌面 GUI 行为不变**；
- 看护进程用 `DETACHED_PROCESS` + `pythonw` 启动（DSH 退出不会带走它），
  轮询端口确认 DSH 已关闭后才动手；完成后用原来的 argv / 工作目录重新拉起 DSH；
- `index.js`：新增 `/update-source`、`/update-status`、`/cancel-update`、
  `/resume-update` 四个路由；自动识别「目标目录就是当前运行 DSH 的根目录」——
  是则走暂存流程，否则直接更新；
- `lib/client.js`：检测面板新增「更新」按钮（两次确认）与待应用更新横幅
  （就绪 / 应用中 / 完成 / 失败 / 超时 / 取消，含取消与重试按钮），中英文案；
- 「更新」按钮不只出现在源码检出行：**运行时 profile 的 `@deepseek-ai/dsh` 若是指向
  源码检出的 junction，对应的 desktop / headless / web 行也会出现按钮**（点哪行都是
  更新同一个源码检出，检测结果里带 `update_target` 字段）；
- 测试 **155 → 179**（新增 24 条：暂存不碰目标目录、应用并保留 node_modules、
  构建失败回滚、目录被占用保留暂存可重试、取消/重试、看护脚本语法、
  junction 运行时解析、update_target 语义等）。

## ⚙️ 说明

- 需要本机 Python 3.10+（插件本来就用它做检测/回滚；没有 Python 时更新按钮不可用）；
- `pnpm install` 只在 `pnpm-lock.yaml` 变化时执行；
  `pnpm run build` 只在目标目录本来就有 `apps/cli/lib`（说明你用构建产物启动 DSH）时执行；
- 首次构建可能比较慢，请耐心等看护进程日志里的「已重新启动 DSH」。

## 📦 本版资产

| 文件 | 说明 |
|---|---|
| `DeepSeekHarnessUpdater.exe` | Windows 独立版桌面工具（无需 Python）。含 v0.8.1 的检测提速 |
| `dsh-updater-src-v0.10.0.zip` | Python 源码版：解压后双击 `启动更新器.bat`，或运行 `python updater_gui.pyw`（需 Python 3.10+，含 tkinter）；同时附带 DSH 插件文件 |
| `SHA256.txt` | EXE 的 SHA256 校验值 |

> 网页版插件不在这些资产里：从 npm（`dsh-updater-plugin`）或本仓库直接安装即可。

## ⚠️ 已知限制

- 在线更新针对源码检出（以及 junction 指向源码检出的运行时 profile）；
  纯 npm 安装的运行时 / npm 全局请用桌面版或手动处理
- 同一目录启动了多个 DSH 实例时，更新前需要把它们**全部关闭**
- 网页插件升级仍需「卸载 → 重新安装」并**重启 DSH**（DSH 插件页不支持自动更新）
- 断网时只显示本地结果，官方版本一栏会提示查询失败
- 回滚窗口最旧的一个备份若读不出 `package.json` 的版本，会显示「回到 备份版本」
- 「使用 GPU 加速」目前仅记录偏好：DSH 尚未提供 GPU 加速选项
