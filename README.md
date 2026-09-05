# DeepSeek Harness 自动检测与更新器

一个带图形界面的桌面小工具，用于：

1. **自动检测电脑内的 DeepSeek Harness 安装**并读取各自版本；
2. **对比官方开源最新版本**（GitHub `deepseek-ai/deepseek-harness` master 源码 + npm 发布版）；
3. **一键更新**：本地版本与官方不同时，自动下载官方源码 zip → 备份原目录 → 整目录替换（自动保留 `node_modules` / `.git`）；
4. **插件检测**：扫描 DeepSeek Harness 运行时中已启用 / 内置的插件（显示 **名称、大小、版本号**）；
5. **技能检测**：扫描 `.dsh\skills` 下的技能（显示 **名称、大小、版本号**）。

---

## 运行方式

- 双击 **`启动更新器.bat`**（推荐，无控制台窗口），或
- 双击 **`updater_gui.pyw`**（需已关联 pythonw），或
- 命令行 `python updater_gui.pyw`

> 依赖：Python 3.10+（含 tkinter，Windows 官方安装包自带）。无需安装任何第三方库。

---

## 界面说明

### 主窗口
| 区域 | 说明 |
| --- | --- |
| 顶部条 | 实时显示 **官方 GitHub master** 与 **npm 发布版** 版本号 |
| 安装列表 | 自动发现本机的 DSH：源码检出、npm 全局安装、`.dsh` 运行时 profile；显示 类型 / 位置 / 当前版本 / 官方参考版本 / 状态 |
| 按钮 | **重新检测**、**更新所选安装**、**插件检测**、**技能检测**、**导出 CSV**、**数据目录** |
| 日志区 | 检测、下载、更新过程全量日志 |

双击列表行可在资源管理器中打开对应位置。

### 更新流程（源码检出）
1. 选中一行「源码检出」，点击 **更新所选安装**；
2. 弹出确认框（可勾选「替换后自动运行 pnpm install」）；
3. 程序将：
   - 下载 `deepseek-harness/archive/refs/heads/master.zip`
   - 将原目录整体**改名备份**（`xxx.dsh-bak-时间戳`，同盘瞬时完成）
   - 把 `node_modules` / `.git` 移回新目录，再放入官方最新源码
   - 可选运行 `pnpm install` 同步依赖
4. 更新前若检测到 DSH Web（127.0.0.1:3080）正在运行，会**中止更新**，请先关闭再重试。

### npm 全局安装
列表里若发现 npm 全局 `@deepseek-ai/dsh`，更新会直接执行 `npm install -g @deepseek-ai/dsh@latest`。

### 插件 / 技能窗口
点击对应按钮会弹出独立表格窗口（**名称 / 版本 / 大小**），支持双击打开所在路径、滚轮/滚动条浏览。

### 导出 CSV
点击 **导出 CSV** 会重新扫描并写出：
- `dsh_plugins.csv`（含启用状态与来源）
- `dsh_skills.csv`

两份文件均保存在本程序所在目录（UTF-8 带 BOM，Excel 可直接打开）。

---

## 检测范围与配置

| 项 | 位置 |
| --- | --- |
| DSH 数据目录 | 环境变量 `DSH_HOME`（默认 `%USERPROFILE%\.dsh`） |
| 技能目录 | 环境变量 `DSH_SKILLS`（默认 `%DSH_HOME%\skills`） |
| 源码检出 | 自动扫描各固定盘根目录下名称含 `harness`/`deepseek` 的目录（两层内），也扫描 `%USERPROFILE%` 等常见位置 |
| 官方源码 | `https://github.com/deepseek-ai/deepseek-harness` `master` 分支 |
| 官方发布版 | npm registry `@deepseek-ai/dsh` `latest` |

如需指定其它技能目录，可设置 `DSH_SKILLS` 环境变量后再启动程序。

---

## 版本号对比规则

支持语义化版本（含预发布后缀），例如：
`0.1.0-rc.5 < 0.1.2-rc.1 < 0.1.3-alpha.1`（先比主版本数字）。

源码检出以 **GitHub master** 为官方参照；npm 全局 / profile 以 **npm 发布版** 为官方参照。

---

## 文件清单

| 文件 | 说明 |
| --- | --- |
| `updater_gui.pyw` | 图形界面主程序 |
| `updater_core.py` | 纯逻辑层：检测 / 网络 / 插件 / 技能 / 更新 |
| `启动更新器.bat` | 一键启动器 |
| `updater_core.py --selftest` | 命令行自测：`python updater_core.py --selftest` |

## 安全提示

- 更新前会备份原目录；备份不删除（除非手动清理），随时可回退。
- 整目录替换**只针对**被识别为 `@deepseek-ai/dsh-root` 的源码检出，不会误伤其它目录。
- 请勿在 DeepSeek Harness 运行时执行源码更新。
