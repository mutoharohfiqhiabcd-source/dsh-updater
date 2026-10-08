v0.8.0 发布说明 —— **网页版插件格式**（不是软件更新）

> 本文件是「最新一版」的更新说明，发布新版本前请改成当版内容。
> GitHub Actions 在推送 `v*` tag 时会把这个文件的内容作为 Release 说明（`body_path`）。

## 🔗 相关链接

| 名称 | 链接 |
| --- | --- |
| **本仓库（桌面版 + DSH 插件本体）** | <https://github.com/mutoharohfiqhiabcd-source/dsh-updater> |
| **DSH 插件安装地址**（填进 DSH「插件 → 添加插件」） | `github:mutoharohfiqhiabcd-source/dsh-updater` |
| DSH 官方仓库（插件宿主） | <https://github.com/deepseek-ai/deepseek-harness> |
| 最新 Release 下载 | <https://github.com/mutoharohfiqhiabcd-source/dsh-updater/releases/latest> |
| 功能介绍推文 | <https://x.com/0ncv2l/status/2106351434749161735> |

一行安装（装完**重启 DSH**）：

```bat
dsh plugin --profile web add github:mutoharohfiqhiabcd-source/dsh-updater
```

## 🖼️ 长这样

![会话标题栏的三个按钮](https://raw.githubusercontent.com/mutoharohfiqhiabcd-source/dsh-updater/main/images/plugin-01-header-buttons.png)

| 回滚面板（点一次确认、再点一次才执行） | 插件管理页 |
| --- | --- |
| ![回滚面板](https://raw.githubusercontent.com/mutoharohfiqhiabcd-source/dsh-updater/main/images/plugin-02-rollback-panel.png) | ![插件管理页](https://raw.githubusercontent.com/mutoharohfiqhiabcd-source/dsh-updater/main/images/plugin-03-plugins-page.png) |

桌面版的样子见 [README](https://github.com/mutoharohfiqhiabcd-source/dsh-updater#界面预览)。

## ❗ 先说清楚：这一版的主角不是软件

v0.8.0 **没有对桌面程序做任何功能改动**。桌面 EXE / 源码版仍在，只是跟着版本号
重建了一份，功能与 v0.7.7 完全一致。

这一版发布的是 **DSH 网页版插件格式**：本仓库从 v0.7.7 起同时是一个 DSH 插件包，
v0.8.0 把它补完 —— 装进 DSH 后，**会话标题栏会多出「检测 / 回滚 / 版本」三个按钮**。

也就是说：

| 用法 | 形态 | 需要下载 EXE 吗 |
|---|---|---|
| 桌面小工具（一直有） | Windows 程序（EXE / Python） | 需要 |
| **在 DSH 网页界面里直接用（本版新增）** | **DSH 插件（网页版）** | **不需要** |

## 🧩 本版新增：会话标题栏的三个按钮

装好插件后，每个会话的标题栏（「1 个后台任务」那一排）会出现：

| 按钮 | 作用 |
|---|---|
| **↻ 检测** | 先本地秒开（0.45 秒，不发网络请求）列出本机所有 DSH 安装：源码检出 / npm 全局 / 运行时 profile，各自版本与参照版本；官方最新版本随后异步补上，查不到会明说，不会一直转圈 |
| **↩ 回滚** | 列出源码备份、npm 回滚点、profile 回滚点；**点一次变「确认回滚？」再点一次才执行**；执行前会先把当前目录也存成一份新备份，所以回滚本身可逆 |
| **ⓘ 版本** | 更新器自身版本、最新 Release、本机 Python、本地 EXE 与归档、各安装的版本 |

三个按钮**不是**在网页里重写逻辑，而是调用本仓库的 `updater_core.py`
（新增 `--json` 命令行模式），与桌面版**共用同一套代码**。

## 📥 怎么装这个网页版插件

**图形界面**：DSH 侧边栏 → **插件** → **添加插件** → 填
`github:mutoharohfiqhiabcd-source/dsh-updater` → 安装。

**命令行**：

```bat
dsh plugin --profile web add github:mutoharohfiqhiabcd-source/dsh-updater
```

装完**重启一次 DSH** 即可在每个会话标题栏看到三个按钮。

> ⚠️ 升级场景务必重启：磁盘上的文件换掉后，运行中的 DSH 仍持有旧的 Host 半边，
> 此时刷新页面按钮会出现、但一按就报 404。
>
> ⚠️ 插件运行在 DSH 主进程内、不受工作区沙箱限制；检测 / 回滚 / 下载 / 启动都会
> 真实读写磁盘。检测与回滚需要本机有 Python 3.10+，没装时界面会明确提示，
> 版本信息不受影响。

## ❗ 重要修复：之前的「源码版 zip」根本跑不起来

**现象**：下载 `dsh-updater-src-v*.zip`（README 里的正式安装方式之一）解压后，
双击 `启动更新器.bat` 或运行 `python updater_gui.pyw`，第一行就报错：

```
ModuleNotFoundError: No module named 'i18n'
```

**原因**：打包脚本 `pack_source.py` 的白名单只列了 7 个文件，**漏掉了全部
i18n 语言模块**（`i18n.py`、`i18n_data.py`、各语言包共 12 个）。而
`updater_core.py` 第 29 行就是 `from i18n import t`，所以解压出来必然起不来。
这个坑在 v0.7.7 及更早的版本里一直存在。

**修复**：语言包改为按 `i18n*.py` 通配自动打包（以后新增语言也不会再漏），
并新增测试 `test_source_zip_is_runnable` —— 它会把 zip 解压到临时目录、
**真的 `import updater_core` 跑一次**，而不是只看清单。

源码版 zip 现在有 26 个文件，同时带上插件文件，解压后「桌面版」和
「DSH 网页插件」两种用法都能直接用。**建议之前下过源码版的用户重新下载。**

## 🔧 顺手修掉的另一个问题

**带 BOM 的 `package.json` 会被误判成「不是有效的 DSH 源码检出」**

Windows 上的记事本与部分编辑器会给 UTF-8 文件写 BOM，而 `json.loads` 遇到 BOM
会直接抛错。结果是：明明是正确的检出目录，检测说它不是，回滚也被安全阀挡下来。
现在读取 JSON 一律用 `utf-8-sig`（没有 BOM 时行为不变）。

## ⚙️ 工程改进

- 测试 **132 → 140 项**，新增的守护都用真实踩过的坑写成：
  - 源码版 zip 解压后必须真的能 import（真实执行，不看清单）
  - `files` 白名单必须覆盖 `updater_core.py` 的全部运行时模块
    （漏一个 i18n 文件，用户在插件里就会 ImportError，本地开发完全复现不出来）
  - `package.json` 版本必须等于 GUI 的 `APP_VERSION`
  - 插件声明三件套（`dsh.client` / `./client` 导出 / 产物）必须对齐
  - 带 BOM 的检出目录仍能被识别
  - `--offline` 模式一个网络请求都不发
- 网页插件是**手写**的闭包工厂产物（`lib/client.js`），仓库里没有构建脚本 ——
  所以从 GitHub 直装不会触发 pnpm 的 `allowBuilds` 授权询问。

## 📦 本版资产

| 文件 | 说明 |
|---|---|
| `DeepSeekHarnessUpdater.exe` | Windows 独立版桌面工具（无需 Python）。**与 v0.7.7 功能一致**，仅版本号更新 |
| `dsh-updater-src-v0.8.0.zip` | Python 源码版：解压后双击 `启动更新器.bat`，或运行 `python updater_gui.pyw`（需 Python 3.10+，含 tkinter）。**本版起才真正可用**（此前漏打包语言模块）；同时附带 DSH 插件文件 |
| `SHA256.txt` | EXE 的 SHA256 校验值 |

> 网页版插件**不在**这些资产里：它直接从本仓库安装（见上），不需要下载 EXE。
> 本 Release 附带的 EXE 只是桌面版的例行重建。

## ⚠️ 已知限制

- 网页插件升级需要「卸载 → 重新安装」（DSH 的插件页明说不支持自动更新）
- 插件里的「检测」在断网时只显示本地结果，官方版本一栏会提示查询失败
- 回滚窗口最旧的一个备份若读不出 `package.json` 的版本，会显示「回到 备份版本」
- 切换语言后若个别文字仍显示为其它语言，点一次「🔄 重新检测」刷新即可
- 「使用 GPU 加速」目前仅记录偏好：DSH 尚未提供 GPU 加速选项
