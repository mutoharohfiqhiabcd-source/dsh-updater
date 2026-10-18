v0.9.0 发布说明 —— **上架 npm + 插件包名迁移（安装地址不变）**

> 本文件是「最新一版」的更新说明，发布新版本前请改成当版内容。
> GitHub Actions 在推送 `v*` tag 时会把这个文件的内容作为 Release 说明（`body_path`）。

## 🔗 相关链接

| 名称 | 链接 |
| --- | --- |
| **本仓库（桌面版 + DSH 插件本体）** | <https://github.com/mutoharohfiqhiabcd-source/dsh-updater> |
| **npm 包页（v0.9.0 起）** | <https://www.npmjs.com/package/dsh-updater-plugin> |
| DSH 官方仓库（插件宿主） | <https://github.com/deepseek-ai/deepseek-harness> |
| 最新 Release 下载 | <https://github.com/mutoharohfiqhiabcd-source/dsh-updater/releases/latest> |
| 功能介绍推文 | <https://x.com/0ncv2l/status/2106351434749161735> |

## 📦 这一版：插件上了 npm，包名改成 `dsh-updater-plugin`

npm 上的 `dsh-updater` 这个名字**已经被别人的同名插件占用**（不是本仓库），
所以本版把包名改成 **`dsh-updater-plugin`** 并正式发布到 npm。

**GitHub 安装地址完全没变**（仓库名还是 `dsh-updater`），只是包的内部名字变了：

| 项目 | 之前 | 现在 |
|---|---|---|
| GitHub 安装 spec | `github:mutoharohfiqhiabcd-source/dsh-updater` | **不变** |
| npm 安装 spec | （没有） | **`dsh-updater-plugin`** |
| 插件在 DSH 里显示的名字 | `dsh-updater` | `dsh-updater-plugin` |
| 桌面 EXE / 源码版 zip | 不变 | 不变（版本号跟着升到 0.9.0） |

**已经在用旧版插件的**：卸载旧插件 → 按下面任一方式重装 → **重启 DSH**。
（DSH 的插件升级本来就必须重启，「旧名 + 新名」也不建议同时装。）

## 📥 安装 / 升级

### DSH 网页插件（两种方式任选）

```bat
:: 方式 A：从 npm 安装（v0.9.0 起可用）
dsh plugin --profile web add dsh-updater-plugin

:: 方式 B：从 GitHub 安装（一直可用，安装地址没变）
dsh plugin --profile web add github:mutoharohfiqhiabcd-source/dsh-updater
```

图形界面：DSH 侧边栏 → **插件** → **添加插件** → 填 `dsh-updater-plugin`
或 `github:mutoharohfiqhiabcd-source/dsh-updater` → 安装 → **重启 DSH**。

### 桌面版

| 你用的是 | 怎么升 |
|---|---|
| **桌面 EXE** | 下载本页的 `DeepSeekHarnessUpdater.exe` 覆盖旧的 |
| **源码版 / Python 版** | 下载 `dsh-updater-src-v0.9.0.zip` 解压替换 |

> ⚠️ 插件运行在 DSH 主进程内、不受工作区沙箱限制；检测 / 回滚 / 下载 / 启动都会
> 真实读写磁盘。检测与回滚需要本机有 Python 3.10+，没装时界面会明确提示。

## ⚡ 顺带回顾：检测已经变快了（v0.8.1 起）

| 场景 | 旧版 | 现在 |
|---|---|---|
| 5 分钟内重复检测（命中缓存） | 93.6 秒 | **0.52 秒** |
| 冷启动（真的联网查一次） | 93.6 秒 | **1.7 ~ 6 秒**（取决于网络） |
| 只查本机安装（离线模式） | 0.35 秒 | 0.43 秒 |

原理：多源并发赛跑（GitHub 官方源 + jsDelivr 镜像 + npm 官方源 + npmmirror 镜像 +
并发重试）、npm 元数据改走 HTTP 接口（去掉 33 秒的 `npm view` 子进程）、
必需项到手立即返回、结果本地缓存 5 分钟。详见 v0.8.1 的 Release 说明。

## 🖼️ 长这样

![会话标题栏的三个按钮](https://raw.githubusercontent.com/mutoharohfiqhiabcd-source/dsh-updater/main/images/plugin-01-header-buttons.png)

| 回滚面板（点一次确认、再点一次才执行） | 插件管理页 |
| --- | --- |
| ![回滚面板](https://raw.githubusercontent.com/mutoharohfiqhiabcd-source/dsh-updater/main/images/plugin-02-rollback-panel.png) | ![插件管理页](https://raw.githubusercontent.com/mutoharohfiqhiabcd-source/dsh-updater/main/images/plugin-03-plugins-page.png) |

桌面版的样子见 [README](https://github.com/mutoharohfiqhiabcd-source/dsh-updater#界面预览)。

## 🔧 本版改了什么

- `package.json` 包名：`dsh-updater` → **`dsh-updater-plugin`**（npm 发布用）；
- `cordis.patch.yml` 里 bundle 行引用的模块名同步改成新包名；
- 网页客户端产物 `lib/client.js` 的模块注册 id 同步改新包名
  （DSH 的模块系统要求注册 id 等于包名，测试里有断言防漏改）；
- Host 半边插件名同步改新包名；
- README / Release 说明补上 npm 安装方式；
- 新增测试守护：bundle patch 里的模块名必须等于 `package.json` 的包名。

> 接口路由 `/dsh-updater/api/*`、会话标题栏的三个按钮、工具名 `dsh_updater`
> 都**没有变**，行为与 v0.8.1 完全一致。

## ⚙️ 工程改进

- 测试 **154 → 155 项**（新增「包名与 bundle patch 一致性」守护）；
- CI 继续在 Ubuntu + Windows、Python 3.10 / 3.12 四组矩阵上跑冒烟测试；
- 打包源码版 zip 时会自动带上新包名与新文档。

## 📦 本版资产

| 文件 | 说明 |
|---|---|
| `DeepSeekHarnessUpdater.exe` | Windows 独立版桌面工具（无需 Python）。含 v0.8.1 的检测提速 |
| `dsh-updater-src-v0.9.0.zip` | Python 源码版：解压后双击 `启动更新器.bat`，或运行 `python updater_gui.pyw`（需 Python 3.10+，含 tkinter）；同时附带 DSH 插件文件 |
| `SHA256.txt` | EXE 的 SHA256 校验值 |

> 网页版插件不在这些资产里：从 npm（`dsh-updater-plugin`）或本仓库直接安装即可。

## ⚠️ 已知限制

- 网页插件升级需要「卸载 → 重新安装」并**重启 DSH**（DSH 的插件页明说不支持自动更新）
- 断网时只显示本地结果，官方版本一栏会提示查询失败
- 回滚窗口最旧的一个备份若读不出 `package.json` 的版本，会显示「回到 备份版本」
- 切换语言后若个别文字仍显示为其它语言，点一次「🔄 重新检测」刷新即可
- 「使用 GPU 加速」目前仅记录偏好：DSH 尚未提供 GPU 加速选项
