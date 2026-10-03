// ============================================================================
// dsh-updater —— DSH 里的「自动更新器」插件
// ----------------------------------------------------------------------------
// 注册一个模型可调用的工具 `dsh_updater`，五个动作：
//   status   本地更新器在哪、最新版本是多少、有哪些归档
//   latest   最新 Release 的完整信息（版本 / 时间 / 资产 / 下载地址）
//   notes    Release 更新说明正文
//   download 把 Release 里的 EXE 下载到本地（默认 Downloads）
//   launch   启动本地的更新器（EXE 或 Python 源码版）
//
// 配置（在 profile 的 cordis.patch.yml 里覆盖 row 的 config）：
//   repo         GitHub 仓库        默认 mutoharohfiqhiabcd-source/dsh-updater
//   asset        Release 资产名     默认 DeepSeekHarnessUpdater.exe
//   downloadDir  下载目录          默认 用户 Downloads
//   updaterPath  本地更新器绝对路径 默认自动探测
//   searchDirs   额外扫描目录       默认 []
//
// 注意：插件在 Host 进程内运行，不受工作区沙箱限制；download / launch 会真实
// 落盘并启动进程。
// ============================================================================

import { spawn } from 'node:child_process'
import { existsSync, readdirSync, statSync } from 'node:fs'
import { mkdir, writeFile } from 'node:fs/promises'
import { homedir } from 'node:os'
import { join } from 'node:path'

import { defineTool } from '@deepseek-ai/dsh-tools'

export const name = 'dsh-updater'
export const inject = ['tools']

const DEFAULT_REPO = 'mutoharohfiqhiabcd-source/dsh-updater'
const DEFAULT_ASSET = 'DeepSeekHarnessUpdater.exe'
const USER_AGENT = 'dsh-updater-plugin'

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

/** GitHub API 取最新 Release；网络抖动时重试一次。 */
async function githubLatest(repo, signal) {
  let lastError
  for (let attempt = 0; attempt < 2; attempt += 1) {
    if (attempt > 0) await sleep(900)
    try {
      const response = await fetch(`https://api.github.com/repos/${repo}/releases/latest`, {
        headers: { accept: 'application/vnd.github+json', 'user-agent': USER_AGENT },
        signal,
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
  }
}

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
  const target = findLocalUpdater(options.updaterPath)
  if (!target) {
    throw new Error('找不到本地更新器；先 download，或用 updaterPath 指定绝对路径')
  }
  const lower = target.toLowerCase()
  const child = lower.endsWith('.pyw') || lower.endsWith('.py')
    ? spawn('pythonw', [target], { detached: true, stdio: 'ignore' })
    : spawn(target, [], { detached: true, stdio: 'ignore' })
  child.unref()
  return `已启动: ${target}（pid ${child.pid ?? '未知'}）`
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
}
