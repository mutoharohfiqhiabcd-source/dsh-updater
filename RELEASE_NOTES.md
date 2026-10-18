v0.8.1 发布说明 —— **检测提速：90 秒 → 半秒**

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

## ⚡ 这一版只干一件事：把「检测更新」从 90 秒压到半秒

之前点一次「检测」，在中国大陆的网络下经常要等 **一分半** 才有结果；现在：

| 场景 | 旧版 | v0.8.1（实测） |
|---|---|---|
| 5 分钟内重复检测（命中缓存） | 93.6 秒 | **0.52 秒** |
| 冷启动（真的联网查一次） | 93.6 秒 | **1.7 ~ 6 秒**（取决于网络；网络好 1.7s，差时 5~9s） |
| 只查本机安装（离线模式） | 0.35 秒 | 0.43 秒 |

> 测法：真实调用正在运行的 DSH 插件接口 `/dsh-updater/api/detect`，并直接跑
> `python updater_core.py --json detect`。桌面版与网页插件共用同一套检测代码，
> 所以**两边同时变快**。

## 🔍 为什么原来那么慢（逐项实测，不是猜）

1. 旧实现**串行**发 7 个网络请求，每个超时 20~25 秒；
2. 最拖后腿的是 `npm view versions` 子进程 —— 实测 **32.8 秒**；
3. GitHub 的接口在国内网络下 **TLS 握手会被随机卡住**：同一个 URL 一次 2.6 秒成功、
   一次 25 秒超时。7 个请求串起来，最坏要等 7 次超时 —— 实测整次 **93.6 秒**；
4. 其实本地扫描只要 0.32 秒，**根本不是瓶颈**。

## 🔧 怎么改的

- **多源并发赛跑**：每类数据同时发多个候选（GitHub 官方源 + jsDelivr 镜像 +
  npm 官方源 + npmmirror 镜像 + 并发重试），谁先成功用谁；单个请求 5 秒超时，
  整轮最多等 8 秒；
- **npm 元数据改用 HTTP 接口**（`application/vnd.npm.install-v1+json`，
  一次拿回 dist-tags + 全部版本 + engines），彻底去掉 33 秒的 `npm view` 子进程，
  也不再要求本机装过 npm；
- **必需项到手就收工**：只要拿到「GitHub master 版本」和「任一 npm 版本通道」，
  就立即返回判断结果，不再为「最近提交 / tags 清单」这类展示细节白等 5 秒；
- **本地缓存**：`%APPDATA%\dsh-updater\official-cache.json`，完整结果缓存 5 分钟；
  抓取不完整时只缓存 30 秒（防止一次网络失败把之后 5 分钟都锁死在错误结果上）；
- 「更新器自身最新版本」检查也缓存 5 分钟；本机 Node 版本只查询一次；
- 网页插件请求 GitHub Release 增加 **8 秒超时**（原先网络卡住时「版本」面板会一直转圈）。

**诚实说明**：所有源都失败时，界面会如实显示「官方版本获取失败」，
**不会拿旧版本假装「已是最新」**；jsDelivr 兜底最坏只会让我们晚一个版本发现更新，
不会误报「可更新」。

## 🖼️ 长这样

![会话标题栏的三个按钮](https://raw.githubusercontent.com/mutoharohfiqhiabcd-source/dsh-updater/main/images/plugin-01-header-buttons.png)

| 回滚面板（点一次确认、再点一次才执行） | 插件管理页 |
| --- | --- |
| ![回滚面板](https://raw.githubusercontent.com/mutoharohfiqhiabcd-source/dsh-updater/main/images/plugin-02-rollback-panel.png) | ![插件管理页](https://raw.githubusercontent.com/mutoharohfiqhiabcd-source/dsh-updater/main/images/plugin-03-plugins-page.png) |

桌面版的样子见 [README](https://github.com/mutoharohfiqhiabcd-source/dsh-updater#界面预览)。

## 📥 怎么升级

| 你用的是 | 怎么升 |
|---|---|
| **桌面 EXE**（旧版不会自动变快） | 下载本页的 `DeepSeekHarnessUpdater.exe` 覆盖旧的即可 |
| **源码版 / Python 版** | 下载 `dsh-updater-src-v0.8.1.zip` 解压替换 |
| **DSH 网页插件** | DSH 侧边栏 → 插件 → 卸载 → 添加插件填 `github:mutoharohfiqhiabcd-source/dsh-updater` → **重启 DSH** |

> ⚠️ 网页插件升级必须重启 DSH：磁盘文件换掉后，运行中的 DSH 仍持有旧的 Host 半边。
>
> ⚠️ 插件运行在 DSH 主进程内、不受工作区沙箱限制；检测 / 回滚 / 下载 / 启动都会
> 真实读写磁盘。检测与回滚需要本机有 Python 3.10+，没装时界面会明确提示。

## ⚙️ 工程改进

- 测试 **140 → 154 项**，新增的 14 条全部围绕这次的提速逻辑，防它以后悄悄退化：
  - 缓存命中必须**零网络**直接返回（并返回副本，调用方改不坏缓存）；
  - 不完整结果只缓存 30 秒；完整结果 5 分钟内有效；
  - 抓取失败时可以沿用旧的 tags / 版本清单，但 **latest 版本绝不能用旧值冒充**；
  - 多源请求必须真并发（3 个 0.25s 请求总耗时 < 0.6s，串行要 0.75s）；
  - 必需项到齐必须立即返回，不为可选项干等超时；
  - jsDelivr 的 tags 是字典、api.github.com 的 tags 是列表，两种格式都要能解析；
  - `--fresh` 参数必须能强制绕过缓存（发版验证用）。
- 网页插件仍是**手写**的闭包工厂产物（`lib/client.js`），从 GitHub 直装不会触发
  pnpm 的 `allowBuilds` 授权询问。

## 📦 本版资产

| 文件 | 说明 |
|---|---|
| `DeepSeekHarnessUpdater.exe` | Windows 独立版桌面工具（无需 Python）。**本版已含检测提速** |
| `dsh-updater-src-v0.8.1.zip` | Python 源码版：解压后双击 `启动更新器.bat`，或运行 `python updater_gui.pyw`（需 Python 3.10+，含 tkinter）；同时附带 DSH 插件文件 |
| `SHA256.txt` | EXE 的 SHA256 校验值 |

> 网页版插件**不在**这些资产里：它直接从本仓库安装（见上），不需要下载 EXE。

## ⚠️ 已知限制

- 网页插件升级需要「卸载 → 重新安装」（DSH 的插件页明说不支持自动更新）
- 断网时只显示本地结果，官方版本一栏会提示查询失败
- 回滚窗口最旧的一个备份若读不出 `package.json` 的版本，会显示「回到 备份版本」
- 切换语言后若个别文字仍显示为其它语言，点一次「🔄 重新检测」刷新即可
- 「使用 GPU 加速」目前仅记录偏好：DSH 尚未提供 GPU 加速选项
