# DeepSeek Harness 更新器（源码版）——自动更新与 GitHub 同步详细说明

> 适用版本：`dsh-updater` v0.7.6
> 目标程序：`updater_core.py` / `updater_gui.pyw`
> 说明范围：源码检出（source checkout）的检测、版本对比、自动更新、GitHub 同步与回滚。

---

## 一、这个更新器是做什么的

`dsh-updater` 是一个 Windows 桌面小工具，用来管理本机上的 **DeepSeek Harness**：

| 能力 | 说明 |
|---|---|
| 自动发现 | 扫描本机源码检出、npm 全局安装、`.dsh` 运行时 profile |
| 版本对比 | 源码检出对比 GitHub `master`；npm/profile 对比 npm `latest` |
| 一键更新 | 源码版：下载 GitHub 源码 zip → 备份 → 整目录替换 |
| 保留本地数据 | 替换时保留 `node_modules` 和 `.git` |
| 插件/技能检测 | 扫描已启用插件和 `.dsh\skills` 下的技能 |
| 技能同步 | 对带 `.git` 的技能目录执行 `git pull --ff-only` |
| 可回滚 | 更新前生成 `*.dsh-bak-时间戳` 备份，更新失败自动回滚 |

---

## 二、源码版（Source Checkout）的识别规则

更新器不会随便替换目录，只有满足以下条件的目录才会被识别为 **DSH 源码检出**：

1. 目录中有 `package.json`；
2. `package.json` 的 `name` 必须是：

```json
"@deepseek-ai/dsh-root"
```

3. 还必须满足以下任一形态：
   - 存在 `apps/cli/src/bin.ts`
   - 或存在 `apps/cli/package.json`

同时会排除本工具生成的备份目录：

```text
*.dsh-bak-*
```

检测范围包括：

- 所有固定盘根目录下，名称含 `harness` / `deepseek` 的目录（最多两层）
- 用户主目录
- `%DSH_HOME%` 所在目录

`DSH_HOME` 默认是：

```text
%USERPROFILE%\.dsh
```

可用环境变量覆盖：

```bat
set DSH_HOME=D:\some\path\.dsh
```

---

## 三、官方版本是如何从 GitHub 检测的

源码版对比的是 **GitHub master 源码**，不依赖本地 `git pull`。

核心地址定义在 `updater_core.py`：

```python
GITHUB_OWNER = "deepseek-ai"
GITHUB_REPO = "deepseek-harness"
GITHUB_BRANCH = "master"

RAW_PACKAGE_URL = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/package.json"
ZIP_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/archive/refs/heads/{GITHUB_BRANCH}.zip"
API_COMMIT_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/commits/{GITHUB_BRANCH}"
```

更新器会获取并展示：

| 数据 | 来源 | 用途 |
|---|---|---|
| 官方 master 版本号 | `raw.githubusercontent.com/.../master/package.json` | 与本地版本比较 |
| 最近一次提交 | GitHub API `commits/master` | 显示 commit SHA 和提交日期 |
| 官方近期提交 | GitHub API `commits?per_page=6` | 显示最近改了什么 |
| GitHub tags | GitHub API `tags?per_page=100` | 判断本地版本是否出现在官方 tag 中 |
| npm 发布版 | `registry.npmjs.org` | 只用于 npm 全局/profile 的对比 |

> 注意：源码版只以 GitHub `master` 为参照，不以 npm 发布版为参照。
> npm/profile 才以 npm `latest` 为参照。

---

## 四、源码版一键更新的完整流程

入口函数：

```python
update_source_from_zip(target_dir, run_pnpm_install=False, ...)
```

它做的事情和顺序如下：

### 1. 校验目标目录

- 目标目录必须存在；
- 必须通过 `@deepseek-ai/dsh-root` 源码检出识别；
- 否则直接报错，不会误替换。

### 2. 检查 DSH 是否正在运行

检测本机 `127.0.0.1:3080` 是否被占用：

```python
if _is_port_open(3080):
    raise RuntimeError("检测到 DeepSeek Harness 正在运行……请先关闭")
```

目的：避免更新到一半源文件正在被使用，导致文件占用或运行异常。

### 3. 记录旧版本并生成备份路径

```text
旧目录：<target_dir>
备份目录：<target_dir.parent>\<target_dir.name>.dsh-bak-YYYYMMDD-HHMMSS
```

备份放在**同一个盘**，所以目录改名是瞬时的，不会产生大量复制。

### 4. 下载官方源码 zip

下载地址：

```text
https://github.com/deepseek-ai/deepseek-harness/archive/refs/heads/master.zip
```

下载到临时目录：

```text
%TEMP%\dsh-update-xxxxx\deepseek-harness.zip
```

下载过程中 GUI 会显示：

- 已下载 / 总大小
- 剩余时间
- 百分比
- 下载速度

### 5. 解压并定位源码根目录

- 解压到临时目录 `extract`；
- 寻找包含 `@deepseek-ai/dsh-root` 的顶层目录；
- 读取新版本号 `new_version`。

### 6. 备份原目录

```python
shutil.move(target_dir, backup_dir)
```

此时原目录整体改名，不会丢失本地修改；备份目录保留在那里，除非用户手动清理。

### 7. 写入新源码

```python
shutil.move(new_root, target_dir)
```

也就是把官方最新源码整体移动到原来的目标路径。

### 8. 移回本地保留目录

从备份目录中把以下目录移回新源码目录：

```text
node_modules/
.git/
```

这样做的目的：

- 保留本地 Git 历史、分支、remote；
- 保留已安装依赖，减少后续 `pnpm install` 时间；
- 避免覆盖用户本地环境配置。

> 因此更新后的目录仍然是原来的 Git 仓库，只是源码文件换成了官方 master 快照。
> 它**不是** `git pull`，而是“源码快照整目录替换 + 保留 .git”。

### 9. 可选执行 pnpm install

如果在 GUI 确认框里勾选了“替换后自动运行 pnpm install”，更新器会：

```python
pnpm install
```

并实时把输出打印到日志区。

如果找不到 `pnpm`，更新器会提示：

> 已替换源码，但未安装依赖，请手动运行 pnpm install。

### 10. 失败自动回滚

如果在“新源码写入”或“移回 node_modules/.git”阶段出错：

1. 删除目标路径；
2. 把备份目录改回原路径；
3. 抛出“更新失败，已回滚”的错误。

### 11. 返回结果

成功时返回：

```json
{
  "ok": true,
  "old_version": "旧版本",
  "new_version": "新版本",
  "backup": "备份目录路径",
  "message": "更新完成：旧版本 → 新版本"
}
```

---

## 五、GitHub 同步说明（两个方向）

这里要区分两个“同步”：

### 方向 A：从 GitHub 同步官方 DSH 源码到本地

这是更新器的主要功能，流程就是上面的“源码版一键更新”：

```text
GitHub master
   → 下载 master.zip
   → 解压
   → 备份旧目录
   → 替换源码
   → 保留 node_modules / .git
```

特点：

- 不需要本地手动 `git pull`；
- 即使本地 `.git` 损坏或不是 git 仓库，也能更新；
- 更新后源码版本 = GitHub master 快照；
- 本地 `.git` 历史不会被覆盖，只是工作区文件被替换。

### 方向 B：把 `dsh-updater` 自身的源码同步到 GitHub

`dsh-updater` 本身是一个 Git 仓库：

```text
remote: https://github.com/mutoharohfiqhiabcd-source/dsh-updater.git
branch: main
```

如果修改了 `updater_core.py` / `updater_gui.pyw` / `README.md`，可以这样同步：

#### B-1 查看状态

```bat
cd /d D:\1231\dsh-updater
git status
git diff
```

#### B-2 提交修改

```bat
git add updater_core.py updater_gui.pyw README.md
git commit -m "更新说明：源码版自动更新与 GitHub 同步文档"
```

#### B-3 拉取远端最新（避免冲突）

```bat
git pull --rebase origin main
```

#### B-4 推送到 GitHub

```bat
git push origin main
```

#### B-5 发布新版本（可选，但推荐）

仓库已配置 GitHub Actions：

```text
.github/workflows/build-release.yml
```

触发方式：

```bat
git tag v0.6.8
git push origin main
git push origin v0.6.8
```

推送 `v*` 标签后，GitHub Actions 会自动：

1. 安装 Python 3.12；
2. 用 PyInstaller 构建 `DeepSeekHarnessUpdater.exe`；
3. 计算 SHA256；
4. 创建/更新 GitHub Release；
5. 把 EXE 和 `SHA256.txt` 上传到 Release。

> 所以“同步到 GitHub”通常 = `git add` → `git commit` → `git push`；
> 如果要发布 EXE，再打 tag 推送即可。

#### B-6 如果还没有配置 remote

```bat
git remote add origin https://github.com/mutoharohfiqhiabcd-source/dsh-updater.git
git branch -M main
git push -u origin main
```

首次推送需要 GitHub 登录：

- 推荐使用 Git Credential Manager 或 SSH；
- 不要在仓库 URL 里明文写 token；
- 如果之前换过 token，用 `git credential-manager github login` 重新登录。

---

## 六、技能目录的 GitHub 同步

技能目录是另一套逻辑：

- 技能目录：`%DSH_HOME%\skills`，可用 `DSH_SKILLS` 覆盖；
- 如果技能目录里有 `.git`，更新器可以用：

```python
git -C <skill_dir> pull --ff-only
```

来拉取该技能仓库的最新内容。

对应函数：

```python
check_skill_latest(skill_items)
update_skills_git(skill_items)
```

特点：

- 只对带 `.git` 的技能执行；
- 没有 `.git` 的本地拷贝会跳过，无法自动检测来源；
- 使用 `--ff-only`，不会自动合并分叉，避免覆盖本地提交。

---

## 七、备份与回滚规则

| 场景 | 结果 |
|---|---|
| 更新前 | 生成 `xxx.dsh-bak-时间戳` 备份 |
| 下载失败 | 原目录不变 |
| 解压失败 | 原目录不变 |
| 替换新源码失败 | 自动回滚到备份 |
| 移回 `node_modules/.git` 失败 | 自动回滚 |
| `pnpm install` 失败 | 源码已替换，保留备份，可手动处理依赖 |
| 更新成功 | 备份默认保留，除非手动删除 |

> 重要：更新 DSH 源码前，一定先关闭正在运行的 DeepSeek Harness（3080 端口）。

---

## 八、源码版 vs EXE 版的区别

| 项目 | 源码版 | EXE 版 |
|---|---|---|
| 启动方式 | `启动更新器.bat` / `python updater_gui.pyw` | 双击 `DeepSeekHarnessUpdater.exe` |
| 运行环境 | 需要 Python 3.10+（含 tkinter） | 不需要 Python |
| 修改代码 | 直接改 `updater_core.py` / `updater_gui.pyw` | 需要重新打包 |
| 调试 | 方便看日志、单步调试 | 不方便 |
| 分发 | 需要带源码 | 单文件直接发 |
| GitHub Actions | 用源码构建 EXE | Release 里下载现成 EXE |

---

## 九、常见问题

### Q1：为什么更新后 `.git` 还在？

因为更新器把备份目录里的 `.git` 移回了新源码目录。它只替换源码文件，不替换 Git 元数据。

### Q2：为什么更新后 `node_modules` 还在？

同理，更新器把 `node_modules` 移回了新目录，避免每次都重新安装依赖。

### Q3：更新后要不要重新 `pnpm install`？

建议要。虽然 `node_modules` 被保留，但官方 `package.json` 可能新增/升级依赖。GUI 确认框可勾选自动执行。

### Q4：怎么回退到更新前？

进入目标目录同级，找到：

```text
xxx.dsh-bak-20260909-140000
```

把它改回原目录名即可，原来的目录先改名或删除。

### Q5：更新会不会破坏本地修改？

会。它用官方 master 源码整体替换工作区，所以本地未提交的源码改动不会保留（`.git` 和 `node_modules` 除外）。更新前请先 commit 或备份。

### Q6：怎么确认本地版本是不是官方最新？

看主窗口顶部：

- **源码检出**对比 GitHub master；
- **npm 全局 / profile**对比 npm latest。

如果本地版本号等于官方版本，状态显示“最新”。

---

## 十、相关文件速查

| 文件 | 作用 |
|---|---|
| `updater_core.py` | 检测 / 版本对比 / 下载 / 更新 / 技能同步 |
| `updater_gui.pyw` | 图形界面 |
| `启动更新器.bat` | Windows 一键启动 |
| `DeepSeekHarnessUpdater.spec` | PyInstaller 打包配置 |
| `.github/workflows/build-release.yml` | tag 触发自动构建 EXE 并发布 Release |
| `.github/workflows/python-publish.yml` | release 触发 Python 构建流程 |
| `.github/workflows/python-package-conda.yml` | push 触发 conda/pytest 流程 |
| `README.md` | 面向用户的总说明 |

---

## 十一、一句话总结

- **自动更新**：从 GitHub `deepseek-ai/deepseek-harness` `master` 下载源码 zip，备份本地目录，替换源码，保留 `node_modules` 和 `.git`，可选执行 `pnpm install`。
- **同步到 GitHub**：
  - 官方 DSH 源码：更新器自动从 GitHub 拉取；
  - 本工具自身：`git add` → `git commit` → `git push origin main`；
  - 发布 EXE：推送 `v*` tag，GitHub Actions 自动构建并上传 Release。
