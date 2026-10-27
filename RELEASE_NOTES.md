v1.0.5 发布说明 —— **修复「等待关闭 DSH 超时 → 无法继续更新」**

> 本文件是「最新一版」的更新说明，发布新版本前请改成当版内容。
> GitHub Actions 在推送 `v*` tag 时会把这个文件的内容作为 Release 说明（`body_path`）。

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

## 🐛 本版修复

### 1. 自动关闭 DSH 找不到进程（导致「等待关闭 DSH 超时」）

**现象**：点更新并勾了「自动关闭 DSH」，结果看护进程一直等不到 DSH 关闭，
30 分钟后报「等待关闭 DSH 超时，这次更新已放弃」。

**根因**：核心是以 `python -X utf8` 启动的，而 `processes_on_port` 用
`subprocess.run(["netstat", "-ano"], text=True)` 读进程列表；中文 Windows 的
netstat 输出是 GBK，UTF-8 解码在 Python 的 reader 线程里抛
`UnicodeDecodeError`，函数吞掉异常后返回空列表 → 看护进程以为「DSH 没在运行」，
于是不会执行自动关闭，只能干等到超时。

**修复**：控制台命令一律先收**字节**、再按控制台代码页解码（Windows 优先
`mbcs`，即 cp936），netstat / tasklist / taskkill 不再解码失败；`pnpm` 实时日志
也改成跟随系统代码页，避免中文输出乱码。

### 2. 超时后红条常驻、界面像「再也不能更新」

**现象**：超时后更新器里一直挂着「等待关闭 DSH 超时，这次更新已放弃」，而且所有
行都是「未检测」、没有「更新」按钮。

**修复**：

- `expired` / `canceled` 的旧任务不再返回给界面（顺手清掉清单），红条消失；
- 官方版本查询失败时，用缓存里的 tags / versions **兜底算出参照版本**，行状态
  不再全是「未检测」；
- 客户端：`unknown` 状态（且上游查询已结束）也会显示「更新」按钮——
  网络再差也有更新入口，不会被锁死。

### 3. 顺带保留 v1.0.4 的改动

下载总时长上限仍是 **10 小时**（慢网络可以挂着慢慢下，随时可取消）。

## 🛠️ 技术细节

- `updater_core.py`：新增 `_decode_console_output()` / `_run_console()`；
  `processes_on_port` / `close_dsh` / `running_node_count` 全部改走字节+代码页解码；
  `_run_pnpm_step` 的编码跟随 `locale.getpreferredencoding()`；
  新增 `_best_known_ref()`，`detect_all` 在官方版本抓取失败时用缓存清单兜底；
  `pending_update_status` 隐藏 expired/canceled 并清理清单
- `lib/client.js`：`DetectRows` 允许 unknown 状态（上游查询结束后）显示更新按钮
- 测试 188 → **195**（GBK netstat/tasklist/taskkill 回归、自动关 DSH 找到进程、
  缓存兜底参照、过期/取消状态隐藏）

## 📦 本版资产

| 文件 | 说明 |
|---|---|
| `DeepSeekHarnessUpdater.exe` | Windows 独立版桌面工具（无需 Python）。版本号同步 1.0.5 |
| `dsh-updater-src-v1.0.5.zip` | Python 源码版：解压后双击 `启动更新器.bat`，或运行 `python updater_gui.pyw`（需 Python 3.10+，含 tkinter）；同时附带 DSH 插件文件 |
| `SHA256.txt` | EXE 的 SHA256 校验值 |

> 网页版插件不在这些资产里：从 npm（`dsh-updater-plugin`）或本仓库直接安装即可。

## ⚠️ 注意

- 网页插件升级仍需「卸载 → 重新安装」并**重启 DSH**（Host 半边不会热替换）
- 更新下载需要能访问 GitHub；网络差时现在可以挂着慢慢下，也可以取消
- 自动关闭模式会让当前 DSH 会话短暂断开（会话记录不受影响），重启后页面自动刷新
- 桌面更新器 / Python 源码版 / DSH 插件三条线版本号统一为 **1.0.5**
