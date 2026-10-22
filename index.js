// ============================================================================
// dsh-updater —— DSH 里的「自动更新器」插件（Host 半边）
// ----------------------------------------------------------------------------
// 1) 模型工具 `dsh_updater`：status / latest / notes / download / launch
// 2) 浏览器按钮用的 HTTP 路由 `/dsh-updater/api/*`：
//      检测         GET  /detect[?offline=1]
//      回滚目标     GET  /rollback-targets
//      执行回滚     POST /rollback-source | /rollback-npm
//      快速版本     GET  /quick
//      打开更新器   POST /launch-updater  （对话框里的「改用桌面更新器」：启动 EXE 窗口）
//      更新 DSH     POST /update-source   （正在运行时：后台 worker 下载暂存 + 进度文件，立即返回）
//      更新进度     GET  /update-progress（读 update-progress.json：百分比/速度/剩余时间）
//      更新状态     GET  /update-status
//      取消更新     POST /cancel-update   （下载中可取消后台 worker）
//      重试应用     POST /resume-update   （目录被占用等原因失败后，重新挂上看护进程）
//    前三个交给本仓库的 updater_core.py（`--json` 模式）执行，逻辑与桌面版完全一致；
//    没装 Python 时 /detect、/rollback-* 会返回友好错误，其余功能不受影响。
//
// 配置（profile 的 cordis.patch.yml 里覆盖 row 的 config）：
//   repo / asset / downloadDir / updaterPath / searchDirs / python / route
//
// 注意：插件在 Host 进程内运行，不受工作区沙箱限制；download / launch / rollback
// 都会真实落盘、真实启动进程。
// ============================================================================

import { spawn } from 'node:child_process'
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { mkdir, writeFile } from 'node:fs/promises'
import { homedir } from 'node:os'
import { join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { defineTool } from '@deepseek-ai/dsh-tools'

export const name = 'dsh-updater-plugin'
export const inject = ['tools']

const DEFAULT_REPO = 'mutoharohfiqhiabcd-source/dsh-updater'
const DEFAULT_ASSET = 'DeepSeekHarnessUpdater.exe'
const DEFAULT_ROUTE = '/dsh-updater/api'
const USER_AGENT = 'dsh-updater-plugin'

/** 本包所在目录：index.js / updater_core.py / package.json 都在这儿。 */
const PACKAGE_DIR = fileURLToPath(new URL('.', import.meta.url))
const CORE_SCRIPT = join(PACKAGE_DIR, 'updater_core.py')
const PACKAGE_JSON = join(PACKAGE_DIR, 'package.json')

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))

/** 把 fetch 的 `TypeError: fetch failed` 展开成真正的原因（DNS/超时/证书…）。 */
function describeError(error) {
  if (!(error instanceof Error)) return String(error)
  const cause = error.cause
  if (cause instanceof Error) {
    const code = typeof cause.code === 'string' ? ` (${cause.code})` : ''
    return `${error.message}: ${cause.message}${code}`
  }
  return error.message
}

/** 本插件自己的版本（读 package.json，不写死）。 */
function selfVersion() {
  try {
    return String(JSON.parse(readFileSync(PACKAGE_JSON, 'utf8')).version ?? '')
  } catch {
    return ''
  }
}

/** 常见安装位置（Windows 下的 EXE 与源码版各一个）。 */
function defaultCandidates() {
  const home = homedir()
  return [
    join(home, 'Downloads', DEFAULT_ASSET),
    join(home, 'Desktop', DEFAULT_ASSET),
    join(home, 'Downloads', 'dsh-updater', DEFAULT_ASSET),
  ]
}

/** 列出目录里的 *.exe（按修改时间倒序），最多 max 条。 */
function listExecutables(dir, max = 10) {
  const found = []
  if (!dir || !existsSync(dir)) return found
  let entries
  try { entries = readdirSync(dir) } catch { return found }
  for (const entry of entries) {
    if (!entry.toLowerCase().endsWith('.exe')) continue
    const full = join(dir, entry)
    try {
      const info = statSync(full)
      found.push({ path: full, size: info.size, mtime: info.mtime.toISOString() })
    } catch { /* 读不到就跳过 */ }
  }
  return found.sort((a, b) => b.mtime.localeCompare(a.mtime)).slice(0, max)
}

function findLocalUpdater(configured) {
  if (configured) return existsSync(configured) ? configured : null
  for (const candidate of defaultCandidates()) {
    if (existsSync(candidate)) return candidate
  }
  return null
}

/**
 * 找到本机「最新」的更新器 EXE。
 *
 * 桌面更新器会随版本更新，而 profile 里配置的 updaterPath 可能指向很旧的构建
 * （本机就指着一个 0.8.0 的 dist EXE）。所以这里把「配置路径 + searchDirs 里的
 * EXE」全部收集起来，优先名字带 updater 的、再按修改时间取最新，避免弹出旧版本。
 * 「更新」按钮就是用它弹出桌面更新器窗口——桌面版有完整的关 DSH / 备份 / 回滚流程。
 */
function resolveUpdaterExe(options) {
  const candidates = []
  const configured = findLocalUpdater(options.updaterPath)
  if (configured) {
    try {
      candidates.push({ path: configured, mtime: statSync(configured).mtime.toISOString() })
    } catch { /* 读不到就跳过 */ }
  }
  const dirs = options.searchDirs.length > 0 ? options.searchDirs : [options.downloadDir]
  for (const dir of dirs) {
    for (const item of listExecutables(dir, 20)) candidates.push(item)
  }
  candidates.sort((a, b) => b.mtime.localeCompare(a.mtime))
  // 更新器的文件名可能是 DeepSeekHarnessUpdater.exe，也可能是归档名 dsh（x-EXE）.exe；
  // 两者都认，取其中最新的一个（避免弹出 profile 配置里那个很旧的 dist 构建）。
  const likely = candidates.filter(item => /(updater|dsh)/i.test(item.path))
  const pool = likely.length > 0 ? likely : candidates
  return pool[0]?.path ?? null
}

/** 脱离 DSH 进程启动桌面更新器窗口（GUI），返回 { path, pid }。 */
function launchUpdater(options) {
  const target = resolveUpdaterExe(options)
  if (!target) {
    throw new Error('没找到本机更新器 EXE；请先下载更新器（或用 updaterPath 指定路径）')
  }
  const lower = target.toLowerCase()
  const child = lower.endsWith('.pyw') || lower.endsWith('.py')
    ? spawn('pythonw', [target], { detached: true, stdio: 'ignore' })
    : spawn(target, [], { detached: true, stdio: 'ignore' })
  child.unref()
  return { path: target, pid: child.pid ?? 0 }
}

/** GitHub API 取最新 Release；网络抖动时重试一次。 */
async function githubLatest(repo, signal) {
  let lastError
  for (let attempt = 0; attempt < 2; attempt += 1) {
    if (attempt > 0) await sleep(900)
    // 单个请求最多等 8 秒：api.github.com 在部分网络下会一直卡着不返回，
    // 没有超时的话「版本」面板会一直转圈（fetch 默认继承系统 TCP 超时，可能几分钟）。
    const timeout = AbortSignal.timeout(8_000)
    const combined = signal ? AbortSignal.any([signal, timeout]) : timeout
    try {
      const response = await fetch(`https://api.github.com/repos/${repo}/releases/latest`, {
        headers: { accept: 'application/vnd.github+json', 'user-agent': USER_AGENT },
        signal: combined,
      })
      if (!response.ok) {
        const body = await response.text().catch(() => '')
        throw new Error(`GitHub API ${response.status} ${response.statusText}${body ? ` — ${body.slice(0, 200)}` : ''}`)
      }
      return await response.json()
    } catch (error) {
      if (signal?.aborted) throw error
      lastError = error
    }
  }
  throw new Error(describeError(lastError))
}

// ---------------------------------------------------------------------------
// 「在插件里更新 DSH 自己」用的路径/进程判断
// ---------------------------------------------------------------------------

/** 当前运行中的 DSH 的根目录；从 argv[1] 的 apps/cli/(lib|src)/bin.(js|ts) 反推。 */
function runningDshRoot() {
  const entry = process.argv[1] ? resolve(String(process.argv[1])) : ''
  if (!/[\\/]apps[\\/]cli[\\/](?:lib|src)[\\/]bin\.(?:js|ts)$/.test(entry)) return ''
  return resolve(entry, '..', '..', '..', '..')
}

/** 两个路径是否指向同一个目录（Windows 路径不区分大小写）。 */
function samePath(a, b) {
  try {
    return resolve(String(a)).toLowerCase() === resolve(String(b)).toLowerCase()
  } catch {
    return false
  }
}

/** 更新完成后自动重启 DSH 需要的信息；判断不出来（如 Electron 桌面端）时返回 null。 */
function restartSpec() {
  if (process.versions?.electron) return null
  if (!runningDshRoot()) return null
  return { execPath: process.execPath, args: process.argv.slice(1), cwd: process.cwd() }
}

/** 本次 HTTP 请求使用的端口（取 Host 头），看护进程靠它判断 DSH 是否已关闭。 */
function requestPort(req) {
  const host = String(req.headers.host ?? '')
  const idx = host.lastIndexOf(':')
  const port = idx >= 0 ? Number(host.slice(idx + 1)) : NaN
  return Number.isFinite(port) && port > 0 && port < 65536 ? port : 3080
}

function formatBytes(size) {
  if (typeof size !== 'number' || !Number.isFinite(size)) return '—'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = size
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit += 1 }
  return `${value.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`
}

function describeRelease(release) {
  const lines = [
    `版本: ${release.tag_name ?? '(无 tag)'}${release.name && release.name !== release.tag_name ? `  (${release.name})` : ''}`,
    `发布: ${release.published_at ?? '—'}`,
    `预发布: ${release.prerelease ? '是' : '否'}`,
    `页面: ${release.html_url ?? '—'}`,
    '资产:',
  ]
  const assets = Array.isArray(release.assets) ? release.assets : []
  if (assets.length === 0) lines.push('  (无)')
  for (const asset of assets) {
    lines.push(`  - ${asset.name}  ${formatBytes(asset.size)}  ${asset.browser_download_url}`)
  }
  return lines.join('\n')
}

function normalizeConfig(config = {}) {
  return {
    repo: typeof config.repo === 'string' && config.repo.trim() ? config.repo.trim() : DEFAULT_REPO,
    asset: typeof config.asset === 'string' && config.asset.trim() ? config.asset.trim() : DEFAULT_ASSET,
    downloadDir: typeof config.downloadDir === 'string' && config.downloadDir.trim()
      ? config.downloadDir.trim()
      : join(homedir(), 'Downloads'),
    updaterPath: typeof config.updaterPath === 'string' && config.updaterPath.trim() ? config.updaterPath.trim() : null,
    searchDirs: Array.isArray(config.searchDirs)
      ? config.searchDirs.filter(dir => typeof dir === 'string' && dir.trim()).map(dir => dir.trim())
      : [],
    python: typeof config.python === 'string' && config.python.trim() ? config.python.trim() : null,
    route: typeof config.route === 'string' && config.route.trim() ? config.route.trim() : DEFAULT_ROUTE,
    coreTimeoutMs: Number.isFinite(config.coreTimeoutMs) ? config.coreTimeoutMs : 180_000,
  }
}

// ---------------------------------------------------------------------------
// updater_core.py 桥
// ---------------------------------------------------------------------------

/** 起一个子进程收完整 stdout/stderr，带超时；返回 { code, stdout, stderr }。 */
function spawnCollect(command, args, timeoutMs, signal) {
  return new Promise((resolve, reject) => {
    let child
    try {
      child = spawn(command, args, { windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] })
    } catch (error) {
      reject(error)
      return
    }
    let stdout = ''
    let stderr = ''
    let settled = false
    const timer = setTimeout(() => {
      if (settled) return
      settled = true
      try { child.kill() } catch { /* 已经退出 */ }
      reject(new Error(`执行超时（${Math.round(timeoutMs / 1000)} 秒）：${command} ${args.join(' ')}`))
    }, timeoutMs)
    const onAbort = () => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      try { child.kill() } catch { /* 已经退出 */ }
      reject(new Error('已取消'))
    }
    signal?.addEventListener('abort', onAbort, { once: true })
    child.stdout.on('data', chunk => { stdout += String(chunk) })
    child.stderr.on('data', chunk => { stderr += String(chunk) })
    child.on('error', (error) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      signal?.removeEventListener('abort', onAbort)
      reject(error)
    })
    child.on('close', (code) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      signal?.removeEventListener('abort', onAbort)
      resolve({ code, stdout, stderr })
    })
  })
}

/** Python 解释器候选：显式配置优先，其次 Windows 上的 py/python，最后 POSIX 的 python3。 */
function pythonCandidates(configured) {
  if (configured) return [configured]
  return process.platform === 'win32'
    ? ['python', 'py', 'python3']
    : ['python3', 'python']
}

/** 更新进度文件路径：与 updater_core.py 的 _settings_dir() 保持一致。 */
function updateProgressFile() {
  const custom = process.env.DSH_UPDATER_SETTINGS_DIR
  const dir = custom
    ? custom
    : process.env.APPDATA
      ? join(process.env.APPDATA, 'dsh-updater')
      : join(homedir(), '.config', 'dsh-updater')
  return join(dir, 'update-progress.json')
}

/** 挑一个 Python 解释器（后台 worker 用；绝对路径要求存在，否则交给 PATH）。 */
function pickPython(options) {
  for (const exe of pythonCandidates(options.python)) {
    if (exe.includes('/') || exe.includes('\\')) {
      if (existsSync(exe)) return exe
      continue
    }
    return exe
  }
  return 'python'
}

/**
 * 后台（detached）跑一次 updater_core.py：暂存下载动辄几分钟，不能卡住 HTTP 请求。
 * 进度写进 update-progress.json，界面轮询 /update-progress 显示进度条。
 */
function spawnCoreDetached(options, args) {
  const exe = pickPython(options)
  const child = spawn(exe, ['-X', 'utf8', CORE_SCRIPT, '--json', ...args], {
    detached: true,
    stdio: 'ignore',
    windowsHide: true,
  })
  child.unref()
  return child.pid ?? 0
}

/**
 * 调 updater_core.py 的 `--json` 模式并把结果解出来。
 * @returns core 返回的 envelope：{ ok, action, data, error, log }
 */
async function runCore(options, args, signal, timeoutMs) {
  if (!existsSync(CORE_SCRIPT)) {
    throw new Error(`找不到 updater_core.py（期望在 ${CORE_SCRIPT}）`)
  }
  const attemptErrors = []
  for (const exe of pythonCandidates(options.python)) {
    let result
    try {
      result = await spawnCollect(exe, ['-X', 'utf8', CORE_SCRIPT, '--json', ...args],
        timeoutMs ?? options.coreTimeoutMs, signal)
    } catch (error) {
      if (error?.code === 'ENOENT') { attemptErrors.push(`${exe}: 未安装`); continue }
      throw error
    }
    const text = result.stdout.trim()
    if (!text) {
      attemptErrors.push(`${exe}: 无输出（${result.stderr.trim().slice(0, 300) || `退出码 ${result.code}`}）`)
      continue
    }
    try {
      const envelope = JSON.parse(text.slice(text.indexOf('{')))
      if (envelope.error === null && result.code !== 0) {
        envelope.error = `updater_core.py 退出码 ${result.code}`
      }
      if (envelope.error === null && envelope.data === null) {
        attemptErrors.push(`${exe}: 空结果`)
        continue
      }
      return envelope
    } catch {
      attemptErrors.push(`${exe}: 输出不是 JSON（${text.slice(0, 200)}）`)
    }
  }
  throw new Error(`调用 updater_core.py 失败 —— ${attemptErrors.join('；')}。`
    + '检测/回滚需要本机有 Python 3.10+（源码版更新器的运行环境）。')
}

// ---------------------------------------------------------------------------
// 模型工具用的动作
// ---------------------------------------------------------------------------

async function runStatus(options, signal) {
  const lines = [`仓库: https://github.com/${options.repo}`, `资产: ${options.asset}`]
  const local = findLocalUpdater(options.updaterPath)
  if (local) {
    const info = statSync(local)
    lines.push(`本地更新器: ${local}`, `  大小: ${formatBytes(info.size)}  修改: ${info.mtime.toISOString()}`)
  } else {
    lines.push('本地更新器: 未找到（可用 download 下载，或用 updaterPath 指定路径）')
  }
  try {
    const release = await githubLatest(options.repo, signal)
    lines.push('', '最新 Release:', describeRelease(release))
  } catch (error) {
    lines.push('', `最新 Release: 查询失败 — ${error instanceof Error ? error.message : String(error)}`)
  }
  const scanned = options.searchDirs.length > 0 ? options.searchDirs : [options.downloadDir]
  for (const dir of scanned) {
    const files = listExecutables(dir)
    if (files.length === 0) continue
    lines.push('', `${dir} 里的 EXE:`)
    for (const item of files) lines.push(`  - ${item.path}  ${formatBytes(item.size)}  ${item.mtime}`)
  }
  return lines.join('\n')
}

async function runDownload(options, signal, log) {
  const { repo, asset, downloadDir } = options
  const release = await githubLatest(repo, signal)
  const assets = Array.isArray(release.assets) ? release.assets : []
  const target = assets.find(item => item.name === asset)
    ?? assets.find(item => item.name?.toLowerCase().endsWith('.exe'))
  if (!target) {
    throw new Error(`Release ${release.tag_name} 里没有 ${asset}；可用资产：${assets.map(item => item.name).join(', ') || '(无)'}`)
  }
  await mkdir(downloadDir, { recursive: true })
  const safeTag = String(release.tag_name ?? 'latest').replace(/[^A-Za-z0-9._-]/g, '_')
  const destination = join(downloadDir, `${safeTag}-${target.name}`)
  log(`下载 ${target.browser_download_url} → ${destination}`)
  const response = await fetch(target.browser_download_url, {
    headers: { 'user-agent': USER_AGENT },
    redirect: 'follow',
    signal,
  })
  if (!response.ok) throw new Error(`下载失败 ${response.status} ${response.statusText}`)
  const buffer = Buffer.from(await response.arrayBuffer())
  await writeFile(destination, buffer)
  return [
    `已下载: ${destination}`,
    `版本: ${release.tag_name ?? '—'}`,
    `大小: ${formatBytes(buffer.byteLength)}（Release 声明 ${formatBytes(target.size)}）`,
    `来源: ${target.browser_download_url}`,
  ].join('\n')
}

async function runLaunch(options) {
  const { path: target, pid } = launchUpdater(options)
  return `已启动: ${target}（pid ${pid || '未知'}）`
}

// ---------------------------------------------------------------------------
// 浏览器按钮用的 HTTP 接口
// ---------------------------------------------------------------------------

function sendJson(res, status, payload) {
  const body = JSON.stringify(payload)
  res.statusCode = status
  res.setHeader('content-type', 'application/json; charset=utf-8')
  res.setHeader('cache-control', 'no-store')
  res.end(body)
}

/** 只服务本机页面：Host 头必须是回环地址（服务器本身也只绑回环）。 */
function isLocalRequest(req) {
  const host = String(req.headers.host ?? '')
  const name = host.startsWith('[') ? host.slice(0, host.indexOf(']') + 1) : host.split(':')[0]
  return name === '127.0.0.1' || name === 'localhost' || name === '[::1]' || name === '::1'
}

function readJsonBody(req, limit = 64 * 1024) {
  return new Promise((resolve, reject) => {
    let size = 0
    const chunks = []
    req.on('data', (chunk) => {
      size += chunk.length
      if (size > limit) {
        reject(new Error('请求体过大'))
        req.destroy()
        return
      }
      chunks.push(chunk)
    })
    req.on('end', () => {
      const text = Buffer.concat(chunks).toString('utf8').trim()
      if (!text) { resolve({}); return }
      try { resolve(JSON.parse(text)) } catch { reject(new Error('请求体不是合法 JSON')) }
    })
    req.on('error', reject)
  })
}

/** 生成路由处理器。所有动作都返回 { ok, data } 或 { ok:false, error }。 */
function createApiHandler(options) {
  return async (req, res) => {
    if (!isLocalRequest(req)) { sendJson(res, 403, { ok: false, error: '仅允许本机访问' }); return }
    let url
    try { url = new URL(String(req.url), 'http://localhost') } catch { sendJson(res, 400, { ok: false, error: '非法 URL' }); return }
    const action = url.pathname.slice(options.route.length).replace(/^\//, '')
    const method = String(req.method ?? 'GET').toUpperCase()
    const wantsPost = action === 'rollback-source' || action === 'rollback-npm'
      || action === 'update-source' || action === 'cancel-update'
      || action === 'resume-update' || action === 'launch-updater'
    if (wantsPost ? method !== 'POST' : method !== 'GET') {
      sendJson(res, 405, { ok: false, error: `不支持的方法 ${method}` })
      return
    }
    try {
      switch (action) {
        case 'quick': {
          sendJson(res, 200, { ok: true, data: await quickInfo(options) })
          return
        }
        case 'detect': {
          const offline = url.searchParams.get('offline') === '1'
          const envelope = await runCore(options, ['detect', ...offline ? ['--offline'] : []])
          sendJson(res, envelope.ok ? 200 : 502, envelope.ok
            ? { ok: true, data: envelope.data }
            : { ok: false, error: envelope.error })
          return
        }
        case 'rollback-targets': {
          const envelope = await runCore(options, ['rollback-targets'])
          sendJson(res, envelope.ok ? 200 : 502, envelope.ok
            ? { ok: true, data: envelope.data }
            : { ok: false, error: envelope.error })
          return
        }
        case 'rollback-source': {
          const body = await readJsonBody(req)
          const target = String(body.target ?? '').trim()
          const backup = String(body.backup ?? '').trim()
          if (!target || !backup) { sendJson(res, 400, { ok: false, error: '缺少 target 或 backup' }); return }
          const envelope = await runCore(options, ['rollback-source', target, backup])
          sendJson(res, envelope.ok ? 200 : 502, envelope.ok
            ? { ok: true, data: envelope.data, log: envelope.log }
            : { ok: false, error: envelope.error, log: envelope.log })
          return
        }
        case 'rollback-npm': {
          const body = await readJsonBody(req)
          const version = String(body.version ?? '').trim()
          if (!version) { sendJson(res, 400, { ok: false, error: '缺少 version' }); return }
          const envelope = await runCore(options, ['rollback-npm', version])
          sendJson(res, envelope.ok ? 200 : 502, envelope.ok
            ? { ok: true, data: envelope.data, log: envelope.log }
            : { ok: false, error: envelope.error, log: envelope.log })
          return
        }
        case 'update-source': {
          const body = await readJsonBody(req)
          const rawTarget = String(body.target ?? '').trim()
          if (!rawTarget) { sendJson(res, 400, { ok: false, error: '缺少 target' }); return }
          const target = resolve(rawTarget)
          if (!existsSync(target)) {
            sendJson(res, 400, { ok: false, error: `目录不存在：${target}` })
            return
          }
          // 插件更新对话框的选项：自动关闭 DSH / 强制 pnpm install / 强制 build
          const flags = []
          const autoClose = body.autoClose === true
          if (autoClose) flags.push('--auto-close')
          if (body.runInstall === true) flags.push('--install')
          else if (body.runInstall === false) flags.push('--no-install')
          if (body.runBuild === true) flags.push('--build')
          else if (body.runBuild === false) flags.push('--no-build')
          const root = runningDshRoot()
          const inUse = root !== '' && samePath(root, target)
          const port = requestPort(req)
          if (inUse) {
            // 目标就是正在运行的 DSH：下载/暂存可能好几分钟，绝不能卡住 HTTP 请求。
            // 后台（detached）跑 stage-source，进度写 update-progress.json，
            // 界面轮询 /update-progress 显示进度条；暂存完成后看护进程按 autoClose 行事。
            const spec = restartSpec()
            const encoded = spec ? Buffer.from(JSON.stringify(spec), 'utf8').toString('base64') : ''
            const workerPid = spawnCoreDetached(options,
              ['stage-source', target, encoded, '--port', String(port), ...flags])
            sendJson(res, 200, {
              ok: true,
              data: {
                started: true, inUse: true, autoClose, restart: Boolean(spec),
                workerPid, progressFile: updateProgressFile(),
              },
            })
            return
          }
          const envelope = await runCore(options,
            ['update-source', target, '--port', String(port), ...flags],
            undefined, 30 * 60_000)
          sendJson(res, envelope.ok ? 200 : 502, envelope.ok
            ? { ok: true, data: { ...envelope.data, inUse: false, restart: false },
              log: envelope.log }
            : { ok: false, error: envelope.error, log: envelope.log })
          return
        }
        case 'update-progress': {
          // 直接读文件（不启动 Python），给界面做高频轮询用
          let data = { present: false }
          try {
            const raw = readFileSync(updateProgressFile(), 'utf8')
            data = { present: true, ...JSON.parse(raw) }
          } catch { /* 没有进度文件 */ }
          sendJson(res, 200, { ok: true, data })
          return
        }
        case 'update-status': {
          const envelope = await runCore(options, ['update-status'])
          sendJson(res, envelope.ok ? 200 : 502, envelope.ok
            ? { ok: true, data: envelope.data }
            : { ok: false, error: envelope.error })
          return
        }
        case 'cancel-update': {
          const envelope = await runCore(options, ['cancel-staged'], undefined, 30_000)
          sendJson(res, envelope.ok ? 200 : 502, envelope.ok
            ? { ok: true, data: envelope.data, log: envelope.log }
            : { ok: false, error: envelope.error, log: envelope.log })
          return
        }
        case 'launch-updater': {
          // 「更新」按钮的第一选择：直接弹出桌面更新器窗口（EXE 里有关 DSH / 备份 / 回滚全套流程）
          // ?dry=1 只解析出要启动的 EXE 路径（排障用，不真的开窗口）
          const dry = url.searchParams.get('dry') === '1'
          try {
            if (dry) {
              const exe = resolveUpdaterExe(options)
              sendJson(res, exe ? 200 : 502, exe
                ? { ok: true, data: { path: exe, pid: 0, dry: true } }
                : { ok: false, error: '没找到本机更新器 EXE' })
              return
            }
            const launched = launchUpdater(options)
            sendJson(res, 200, { ok: true, data: launched })
          } catch (launchError) {
            sendJson(res, 502, { ok: false, error: describeError(launchError) })
          }
          return
        }
        case 'resume-update': {
          const envelope = await runCore(options, ['resume-staged'], undefined, 60_000)
          sendJson(res, envelope.ok ? 200 : 502, envelope.ok
            ? { ok: true, data: envelope.data, log: envelope.log }
            : { ok: false, error: envelope.error, log: envelope.log })
          return
        }
        default:
          sendJson(res, 404, { ok: false, error: `未知接口 ${action || '(空)'}` })
      }
    } catch (error) {
      sendJson(res, 500, { ok: false, error: describeError(error) })
    }
  }
}

/** 不依赖 Python、不扫盘的快速信息：更新器自身版本 + 最新 Release + 本地 EXE。 */
async function quickInfo(options) {
  const data = {
    version: selfVersion(),
    repo: options.repo,
    asset: options.asset,
    python: null,
    updaterPath: findLocalUpdater(options.updaterPath),
    release: null,
    releaseError: null,
    exes: [],
  }
  try {
    const release = await githubLatest(options.repo, undefined)
    data.release = {
      tag: release.tag_name ?? '',
      name: release.name ?? '',
      date: release.published_at ?? '',
      url: release.html_url ?? '',
      assets: (Array.isArray(release.assets) ? release.assets : []).map(a => ({
        name: a.name, size: a.size, url: a.browser_download_url,
      })),
    }
  } catch (error) {
    data.releaseError = describeError(error)
  }
  data.python = await detectPython(options)
  const dirs = options.searchDirs.length > 0 ? options.searchDirs : [options.downloadDir]
  for (const dir of dirs) {
    for (const item of listExecutables(dir, 20)) data.exes.push({ ...item, dir })
  }
  return data
}

/** 探测可用的 Python 解释器（只为在界面上告诉用户能不能用检测/回滚）。 */
async function detectPython(options) {
  for (const exe of pythonCandidates(options.python)) {
    try {
      const result = await spawnCollect(exe, ['--version'], 8_000, undefined)
      const text = `${result.stdout}${result.stderr}`.trim()
      if (result.code === 0 && text) return { command: exe, version: text }
    } catch { /* 换下一个 */ }
  }
  return null
}

export function apply(ctx, config) {
  const options = normalizeConfig(config)
  const log = message => {
    try { ctx.logger?.info?.(`[dsh-updater] ${message}`) } catch { /* 日志失败不影响功能 */ }
  }
  log(`已加载（repo=${options.repo}）`)

  ctx.tools.register(defineTool({
    name: 'dsh_updater',
    description:
      '查询、下载或启动 DSH 自动更新器（dsh-updater），默认仓库 '
      + `${DEFAULT_REPO}。`
      + 'action=status 汇总本地情况与最新版本；latest 看最新 Release；notes 看更新说明；'
      + 'download 下载 EXE 到本地；launch 启动本地更新器。',
    parameters: {
      action: {
        type: 'string',
        enum: ['status', 'latest', 'notes', 'download', 'launch'],
        required: true,
        description: '要执行的动作',
      },
    },
    output: {
      schema: { type: 'string' },
      render: (_args, value) => [{ type: 'text', text: value }],
    },
    async execute(args, exec) {
      switch (args.action) {
        case 'status':
          return await runStatus(options, exec.signal)
        case 'latest': {
          const release = await githubLatest(options.repo, exec.signal)
          return [`仓库: https://github.com/${options.repo}`, describeRelease(release)].join('\n')
        }
        case 'notes': {
          const release = await githubLatest(options.repo, exec.signal)
          const body = typeof release.body === 'string' && release.body.trim() ? release.body : '(该 Release 没有说明)'
          return [`# ${release.tag_name ?? ''} ${release.name ?? ''}`.trim(), '', body].join('\n')
        }
        case 'download':
          return await runDownload(options, exec.signal, log)
        case 'launch':
          return await runLaunch(options)
        default:
          throw new Error(`未知动作: ${String(args.action)}`)
      }
    },
  }))

  // 浏览器半边只在有 Web 服务器的组合里注册（headless profile 没有，不报错）。
  ctx.inject(['webServer'], (webCtx) => {
    webCtx.effect(
      () => webCtx.webServer.register({
        kind: 'prefix',
        path: options.route,
        handler: createApiHandler(options),
      }),
      `dsh-updater: ${options.route}`,
    )
    log(`已注册界面接口 ${options.route}`)
  })
}
