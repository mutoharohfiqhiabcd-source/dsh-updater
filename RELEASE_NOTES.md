v0.7.7 更新说明（与 v0.7.6 相比）

> 本文件是「最新一版」的更新说明，发布新版本前请改成当版内容。
> GitHub Actions 在推送 `v*` tag 时会把这个文件的内容作为 Release 说明（`body_path`）。

## 🔧 修复

**回滚窗口顶部提示文案后面的黑色矩形**

「勾选要回滚的项（可多选，跨类别也可以一起选），再点「回滚所选」。」这句话
后面有一块突兀的黑色背景，与窗口底色明显不搭（深色模式下尤其显眼）。

根因不是配色，而是这个样式**被使用却从未定义**：

    ttk.Label(win, text=..., style="Hint.TLabel")   # _setup_style 里没有 Hint.TLabel

ttk 拿到一个未配置的样式名不会回退到 `TLabel`，而是渲染成一块黑底。
现已在 `_setup_style` 里补上定义，背景跟窗口底色（`bg`）而非面板色（`panel`）。

**顺带排查了同类问题**：扫描源码里所有 `style="X"` 用法，与 `_setup_style`
里 `configure` / `map` 过的样式名逐一比对——只有 `Hint.TLabel` 这一处漏定义，
其余都正常。并新增测试 `test_all_used_ttk_styles_are_defined` 自动守住这条线。

## 📦 本版资产（两种版本）

| 文件 | 说明 |
|---|---|
| `DeepSeekHarnessUpdater.exe` | Windows 独立版（无需 Python），双击即用 |
| `dsh-updater-src-v0.7.7.zip` | Python 源码版：解压后双击 `启动更新器.bat`，或运行 `python updater_gui.pyw`（需 Python 3.10+，含 tkinter） |
| `SHA256.txt` | EXE 的 SHA256 校验值 |

上版本用户若已安装：直接覆盖 exe 即可，数据（CSV 导出）与本地设置不受影响。

## ⚠️ 已知限制

- 回滚窗口最旧的一个备份若读不出 package.json 的版本，会显示「回到 备份版本」
- 下拉框展开后的列表使用 Tk option 数据库上色，未能在开发机上回读验证
- 切换语言后若个别文字仍显示为其它语言，点一次「🔄 重新检测」刷新即可
- 「使用 GPU 加速」目前仅记录偏好：DSH 尚未提供 GPU 加速选项
