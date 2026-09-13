v0.7.1 更新说明（与 v0.7.0 相比）

> 本文件是「最新一版」的更新说明，发布新版本前请改成当版内容。
> GitHub Actions 在推送 `v*` tag 时会把这个文件的内容作为 Release 说明（`body_path`）。

## 🔧 修复

**更新 npm 全局安装前，先检查 DeepSeek Harness 是否在运行**

这是一个会造成实际损害的缺陷：DSH 运行时，原生模块（如
`sharp-win32-x64-*.node`）已被加载，Windows 不允许 npm 替换这些文件。
更新会以

```
EPERM: operation not permitted, unlink ...sharp-win32-x64-0.35.4.node
```

中断，并可能留下**缺少子模块文件的损坏安装树**（例如
`@opentelemetry/api/trace/status.js` 缺失），而界面上只显示一句 EPERM，
用户完全看不出原因。

现在：检测到 3080 端口被占用时会直接中止更新，并明确提示
「请先关闭 DeepSeek Harness」；另外检测到 node 进程时会在日志给出风险提示。
源码更新的端口检查保持不变。

> 如果你之前更新 npm 全局时遇到过 EPERM，建议重装一次以确保安装完整：
> `npm install -g @deepseek-ai/dsh@latest`

## ⚙️ 工程改进

- 测试环境固定：所有测试固定使用简体中文与临时目录作为本地信息目录。
  此前测试结果依赖运行环境的系统语言（CI 是英文、开发机是中文），
  本地全绿而 CI 全红且极难复现——现在已消除该环境依赖，CI 恢复全绿
- 测试从 115 项增至 117 项

## 📦 本版资产（两种版本）

| 文件 | 说明 |
|---|---|
| `DeepSeekHarnessUpdater.exe` | Windows 独立版（无需 Python），双击即用 |
| `dsh-updater-src-v0.7.1.zip` | Python 源码版：解压后双击 `启动更新器.bat`，或运行 `python updater_gui.pyw`（需 Python 3.10+，含 tkinter） |
| `SHA256.txt` | EXE 的 SHA256 校验值 |

上版本用户若已安装：直接覆盖 exe 即可，数据（CSV 导出）与本地设置不受影响。

## ⚠️ 已知限制

- 日志区中少量折行拼接的长消息尚未接入多语言，仍显示中文
- 切换语言后若个别文字仍显示为其它语言，点一次「🔄 重新检测」刷新即可
- **用更新器更新 DSH 源码后，需要重新构建**：整目录替换只保留
  `node_modules` 与 `.git`，若你的启动方式依赖构建产物
  （`apps/cli/lib/`），请重新执行 `pnpm install && pnpm run build`
- 「使用 GPU 加速」目前仅记录偏好：DSH 尚未提供 GPU 加速选项
