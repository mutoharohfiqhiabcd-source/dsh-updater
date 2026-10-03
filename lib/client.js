// ============================================================================
// dsh-updater —— DSH 会话标题栏按钮（浏览器半边）
// ----------------------------------------------------------------------------
// 在「1 个后台任务」同一排（conversation.session.header.actions）加三个按钮：
//   检测   本机所有 DSH 安装 + 官方最新版本（先本地秒开，再异步补官方）
//   回滚   源码备份 / npm / profile 三类可回滚项，点一次确认再执行
//   版本   更新器自身版本、最新 Release、本机安装版本、Python 与本地 EXE
//
// 数据来自 Host 半边的 /dsh-updater/api/*（Host 半边再调 updater_core.py）。
// 本文件是「闭包工厂」格式的产物：__ModuleLoader__.load({id, factory})，
// 依赖通过工厂参数 require 从 DSH 模块表取（react 属于基线模块）。
// 手写、无需打包，所以仓库里没有构建脚本，git 直装也不会触发 pnpm 的
// allowBuilds 询问。
// ============================================================================

window.__ModuleLoader__.load({
  id: 'dsh-updater',
  factory: function (require) {
    'use strict'
    var module = { exports: {} }
    var exports = module.exports

    const React = require('react')
    const h = React.createElement
    const { useCallback, useEffect, useRef, useState } = React

    /** locale 服务（apply 时注入）；语言判断见 isZh()。 */
    let LOCALE = null

    const API = '/dsh-updater/api'
    const STYLE_ID = 'dsh-updater/client.css'
    const ARM_MS = 4000

    const ZH = { value: null }
    /**
     * 当前界面语言。优先问 DSH 的 locale 服务（apply 时注入），
     * 退回到 <html lang>（locale 运行时会同步这个属性）。
     * 必须在「渲染时」求值：模块加载时 <html lang> 还是模板初值，会误判成英文。
     */
    function isZh() {
      try {
        const active = LOCALE?.getSnapshot?.()?.active
        if (typeof active === 'string' && active) return active.toLowerCase().startsWith('zh')
      } catch { /* 服务不可用就用 DOM */ }
      return (document.documentElement.lang || '').toLowerCase().startsWith('zh')
    }
    const TEXT = {
      zh: {
        detect: '检测', rollback: '回滚', version: '版本',
        detecting: '检测中…', loading: '读取中…', retry: '重试', close: '关闭',
        localOnly: '本机结果（官方版本查询中…）',
        officialFailed: '官方版本查询失败',
        noInstalls: '没有检测到 DSH 安装',
        noBackups: '没有可回滚的备份',
        source: '源码检出', npm: 'npm 全局', profile: '运行时 profile',
        sourceBackups: '源码备份', npmBackups: 'npm 回滚点', profileBackups: 'profile 回滚点',
        doRollback: '回滚', confirmRollback: '确认回滚？', rolling: '回滚中…',
        rollbackOk: '回滚完成', rollbackFailed: '回滚失败',
        installs: '本机安装', official: '官方最新', updater: '更新器', python: 'Python', exes: '本地 EXE',
        latest: '最新', updateAvailable: '可更新', upToDate: '已是最新', unknown: '未检测',
        githubRef: 'GitHub', npmRef: 'npm', noPython: '未找到（检测/回滚不可用）',
        title: 'DSH 自动更新器',
      },
      en: {
        detect: 'Check', rollback: 'Roll back', version: 'Version',
        detecting: 'Checking…', loading: 'Loading…', retry: 'Retry', close: 'Close',
        localOnly: 'Local results (checking upstream…)',
        officialFailed: 'Upstream check failed',
        noInstalls: 'No DSH installation found',
        noBackups: 'Nothing to roll back',
        source: 'Source checkout', npm: 'npm global', profile: 'Runtime profile',
        sourceBackups: 'Source backups', npmBackups: 'npm restore points', profileBackups: 'Profile restore points',
        doRollback: 'Roll back', confirmRollback: 'Confirm?', rolling: 'Rolling back…',
        rollbackOk: 'Rolled back', rollbackFailed: 'Rollback failed',
        installs: 'Installations', official: 'Upstream latest', updater: 'Updater', python: 'Python', exes: 'Local EXE',
        latest: 'latest', updateAvailable: 'Update available', upToDate: 'Up to date', unknown: 'Unknown',
        githubRef: 'GitHub', npmRef: 'npm', noPython: 'not found (check/rollback unavailable)',
        title: 'DSH updater',
      },
    }
    const t = key => (isZh() ? TEXT.zh : TEXT.en)[key]

    // ---------------------------------------------------------------------
    // 样式：一次性注入，颜色全部走主题 token，浅色/深色自动跟随
    // ---------------------------------------------------------------------
    const CSS = `
.dshu-root { position: relative; display: inline-flex; align-items: center; gap: 2px; }
.dshu-btn {
  display: inline-flex; align-items: center; gap: 4px;
  font: inherit; font-size: 12px; line-height: 16px;
  color: var(--dsw-alias-label-secondary, #6b7280);
  background: transparent; border: 0; border-radius: var(--dsw-radius-sm, 8px);
  padding: 3px 7px; cursor: pointer; white-space: nowrap;
}
.dshu-btn:hover { background: var(--dsw-alias-interactive-bg-hover, rgba(38,49,72,.06)); color: var(--dsw-alias-label-primary, #111827); }
.dshu-btn[data-open="1"] { background: var(--dsw-alias-interactive-bg-active, rgba(38,49,72,.1)); color: var(--dsw-alias-label-primary, #111827); }
.dshu-btn[data-busy="1"] { opacity: .6; cursor: default; }
.dshu-panel {
  position: absolute; top: calc(100% + 6px); right: 0; z-index: 40;
  width: 430px; max-width: min(430px, 86vw); max-height: 60vh; overflow: auto;
  padding: 10px 12px 12px;
  background: var(--dsw-specific-menu, var(--dsw-alias-bg-overlay, #fff));
  backdrop-filter: var(--dsw-menu-backdrop-filter, none);
  border: 1px solid var(--dsw-alias-border-l2, rgba(0,0,0,.08));
  border-radius: var(--dsw-radius-md, 12px);
  box-shadow: var(--dsw-elevation-stroke, 0 0 0 .5px rgba(0,0,0,.06)), 0 8px 28px rgba(0,0,0,.16);
  color: var(--dsw-alias-label-primary, #111827); font-size: 12px; line-height: 18px;
  text-align: left;
}
.dshu-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 6px; }
.dshu-title { font-weight: 600; font-size: 12px; }
.dshu-x { border: 0; background: transparent; cursor: pointer; color: var(--dsw-alias-label-caption, #9ca3af); font-size: 14px; line-height: 14px; padding: 0 3px; }
.dshu-x:hover { color: var(--dsw-alias-label-primary, #111827); }
.dshu-hint { color: var(--dsw-alias-label-caption, #9ca3af); margin: 6px 0 2px; }
.dshu-err { color: var(--dsw-alias-state-error-primary, #dc2626); margin: 6px 0 0; word-break: break-word; }
.dshu-ok { color: var(--dsw-alias-state-success-primary, #16a34a); margin: 6px 0 0; }
.dshu-sec { margin-top: 8px; color: var(--dsw-alias-label-caption, #9ca3af); font-size: 11px; }
.dshu-row { display: flex; align-items: center; gap: 8px; padding: 5px 0; border-top: 1px solid var(--dsw-alias-border-l1, rgba(0,0,0,.05)); }
.dshu-row:first-of-type { border-top: 0; }
.dshu-main { flex: 1; min-width: 0; }
.dshu-name { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dshu-sub { display: block; color: var(--dsw-alias-label-caption, #9ca3af); font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dshu-tag { flex: none; font-size: 11px; padding: 1px 6px; border-radius: 999px; border: 1px solid transparent; }
.dshu-tag[data-kind="update-available"] { color: var(--dsw-alias-state-warn-label, #b45309); background: var(--dsw-alias-state-warn-tertiary, rgba(245,158,11,.14)); }
.dshu-tag[data-kind="latest"] { color: var(--dsw-alias-state-success-primary, #16a34a); background: var(--dsw-alias-state-success-tertiary, rgba(22,163,74,.14)); }
.dshu-tag[data-kind="unknown"] { color: var(--dsw-alias-label-caption, #9ca3af); background: var(--dsw-alias-interactive-bg-hover, rgba(0,0,0,.05)); }
.dshu-act {
  flex: none; font: inherit; font-size: 11px; padding: 2px 8px; cursor: pointer;
  color: var(--dsw-alias-label-primary, #111827);
  background: var(--dsw-alias-button-floating-fill, rgba(0,0,0,.04));
  border: 1px solid var(--dsw-alias-border-l2, rgba(0,0,0,.1)); border-radius: var(--dsw-radius-xs, 4px);
}
.dshu-act:hover { background: var(--dsw-alias-interactive-bg-hover, rgba(0,0,0,.08)); }
.dshu-act[data-armed="1"] { color: var(--dsw-alias-state-error-primary, #dc2626); border-color: currentColor; }
.dshu-kv { display: flex; gap: 10px; padding: 3px 0; }
.dshu-k { flex: none; width: 88px; color: var(--dsw-alias-label-caption, #9ca3af); }
.dshu-v { flex: 1; min-width: 0; word-break: break-all; }
`
    function injectStyle() {
      if (typeof document === 'undefined') return
      if (document.querySelector('style[data-plugin-css="' + STYLE_ID + '"]') !== null) return
      const tag = document.createElement('style')
      tag.dataset.plugin = 'dsh-updater'
      tag.dataset.pluginCss = STYLE_ID
      tag.textContent = CSS
      document.head.appendChild(tag)
    }

    // ---------------------------------------------------------------------
    // Host 接口
    // ---------------------------------------------------------------------
    async function api(path, init) {
      const response = await fetch(API + path, {
        headers: { accept: 'application/json' },
        ...init,
      })
      let payload = null
      try { payload = await response.json() } catch { payload = null }
      if (payload === null) throw new Error('HTTP ' + response.status)
      if (payload.ok === false || !response.ok) throw new Error(payload.error || ('HTTP ' + response.status))
      return payload.data
    }

    const post = (path, body) => api(path, {
      method: 'POST',
      headers: { accept: 'application/json', 'content-type': 'application/json' },
      body: JSON.stringify(body),
    })

    function kindLabel(kind) {
      if (kind === 'source') return t('source')
      if (kind === 'npm') return t('npm')
      if (kind === 'profile') return t('profile')
      return String(kind || '')
    }

    function statusLabel(status) {
      if (status === 'update-available') return t('updateAvailable')
      if (status === 'latest') return t('upToDate')
      return t('unknown')
    }

    function stampText(stamp) {
      const m = /^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})$/.exec(String(stamp || ''))
      return m ? `${m[1]}-${m[2]}-${m[3]} ${m[4]}:${m[5]}` : String(stamp || '')
    }

    const baseName = value => String(value || '').replace(/[\\/]+$/, '').split(/[\\/]/).pop() || String(value || '')

    function Spinner() {
      return h('div', { className: 'dshu-hint' }, t('loading'))
    }

    // ---------------------------------------------------------------------
    // 面板内容
    // ---------------------------------------------------------------------
    function DetectRows({ data, upstreamError, upstreamPending }) {
      const installs = data?.installs ?? []
      if (installs.length === 0) return h('div', { className: 'dshu-hint' }, t('noInstalls'))
      return h('div', null,
        installs.map((row, index) => h('div', { className: 'dshu-row', key: row.path + index },
          h('span', { className: 'dshu-main' },
            h('span', { className: 'dshu-name', title: row.path }, baseName(row.path)),
            h('span', { className: 'dshu-sub', title: row.path },
              kindLabel(row.kind)
              + ' · ' + (row.version || '—')
              + (row.ref_version ? ` → ${row.ref_kind === 'github' ? t('githubRef') : t('npmRef')} ${row.ref_version}` : '')),
          ),
          h('span', { className: 'dshu-tag', 'data-kind': row.status }, statusLabel(row.status)),
        )),
        upstreamPending ? h('div', { className: 'dshu-hint' }, t('localOnly')) : null,
        upstreamError ? h('div', { className: 'dshu-err' }, `${t('officialFailed')}：${upstreamError}`) : null,
      )
    }

    function RollbackRows({ data, onRollback, busyKey, result, error }) {
      const groups = [
        ['sourceBackups', data?.source ?? [], item => ({
          key: item.target + '|' + item.backup,
          title: `${baseName(item.target)}  ←  ${stampText(item.stamp)}`,
          sub: `${item.from_version || '—'} → ${item.to_version || '—'}`,
          payload: { target: item.target, backup: item.backup },
        })],
        ['npmBackups', data?.npm ?? [], item => ({
          key: 'npm|' + item.version,
          title: `npm  ${item.to_version || item.version}`,
          sub: `${item.from_version || '—'} → ${item.to_version || '—'}`,
          payload: { version: item.version, kind: 'npm' },
        })],
        ['profileBackups', data?.profile ?? [], item => ({
          key: 'profile|' + item.target + '|' + item.version,
          title: `${baseName(item.target)}  ${item.to_version || item.version}`,
          sub: `${item.from_version || '—'} → ${item.to_version || '—'}`,
          payload: { version: item.version, kind: 'profile', target: item.target },
        })],
      ]
      const total = groups.reduce((sum, [, rows]) => sum + rows.length, 0)
      if (total === 0) return h('div', { className: 'dshu-hint' }, t('noBackups'))
      return h('div', null,
        groups.map(([label, rows, map]) => rows.length === 0 ? null : h('div', { key: label },
          h('div', { className: 'dshu-sec' }, t(label)),
          rows.map((item) => {
            const row = map(item)
            const armed = busyKey === row.key
            return h('div', { className: 'dshu-row', key: row.key },
              h('span', { className: 'dshu-main' },
                h('span', { className: 'dshu-name' }, row.title),
                h('span', { className: 'dshu-sub' }, row.sub),
              ),
              h('button', {
                type: 'button',
                className: 'dshu-act',
                'data-armed': armed ? '1' : '0',
                onClick: () => onRollback(row),
              }, armed ? t('confirmRollback') : t('doRollback')),
            )
          }),
        )),
        result ? h('div', { className: 'dshu-ok' }, `${t('rollbackOk')}：${result}`) : null,
        error ? h('div', { className: 'dshu-err' }, `${t('rollbackFailed')}：${error}`) : null,
      )
    }

    function VersionView({ quick, local, quickError }) {
      const rows = []
      if (quickError) rows.push(['', quickError, true])
      if (quick) {
        rows.push([t('updater'), quick.version || '—'])
        rows.push([t('official'), quick.release ? `${quick.release.tag}  (${(quick.release.date || '').slice(0, 10)})`
          : (quick.releaseError ? `${t('officialFailed')}：${quick.releaseError}` : '—')])
        rows.push([t('python'), quick.python ? `${quick.python.version}  (${quick.python.command})` : t('noPython')])
        if (quick.updaterPath) rows.push([t('exes'), quick.updaterPath])
        for (const exe of quick.exes ?? []) rows.push(['', `${baseName(exe.path)}`])
      }
      for (const inst of local?.installs ?? []) {
        rows.push([kindLabel(inst.kind), `${baseName(inst.path)}  ${inst.version || '—'}`])
      }
      if (rows.length === 0) return h(Spinner)
      return h('div', null, rows.map(([key, value, isError], index) => h('div', { className: 'dshu-kv', key: key + index },
        h('span', { className: 'dshu-k' }, key),
        h('span', { className: isError ? 'dshu-err' : 'dshu-v' }, value),
      )))
    }

    // ---------------------------------------------------------------------
    // 标题栏按钮
    // ---------------------------------------------------------------------
    function UpdaterBar() {
      const [view, setView] = useState(null)
      const [busy, setBusy] = useState(false)
      const [error, setError] = useState(null)
      const [detect, setDetect] = useState(null)
      const [upstreamPending, setUpstreamPending] = useState(false)
      const [upstreamError, setUpstreamError] = useState(null)
      const [targets, setTargets] = useState(null)
      const [armedKey, setArmedKey] = useState(null)
      const [rollbackResult, setRollbackResult] = useState(null)
      const [rollbackError, setRollbackError] = useState(null)
      const [quick, setQuick] = useState(null)
      const [quickError, setQuickError] = useState(null)
      const rootRef = useRef(null)

      useEffect(() => { injectStyle() }, [])

      // 点空白处 / Esc 关面板
      useEffect(() => {
        if (view === null) return undefined
        const onPointer = (event) => {
          if (rootRef.current && !rootRef.current.contains(event.target)) setView(null)
        }
        const onKey = (event) => { if (event.key === 'Escape') setView(null) }
        document.addEventListener('pointerdown', onPointer, true)
        document.addEventListener('keydown', onKey)
        return () => {
          document.removeEventListener('pointerdown', onPointer, true)
          document.removeEventListener('keydown', onKey)
        }
      }, [view])

      // 确认态超时自动撤销
      useEffect(() => {
        if (armedKey === null) return undefined
        const timer = setTimeout(() => { setArmedKey(null) }, ARM_MS)
        return () => { clearTimeout(timer) }
      }, [armedKey])

      const loadDetect = useCallback(async () => {
        setBusy(true); setError(null); setUpstreamError(null)
        try {
          // 先本地秒开（不发任何网络请求），再异步补官方版本
          const local = await api('/detect?offline=1')
          setDetect(local)
          setUpstreamPending(true)
          setBusy(false)
          try {
            const full = await api('/detect')
            setDetect(full)
          } catch (upstreamFailure) {
            setUpstreamError(upstreamFailure.message ?? String(upstreamFailure))
          } finally {
            setUpstreamPending(false)
          }
        } catch (failure) {
          setError(failure.message ?? String(failure))
          setBusy(false)
        }
      }, [])

      const loadRollback = useCallback(async () => {
        setBusy(true); setError(null); setRollbackResult(null); setRollbackError(null)
        try {
          setTargets(await api('/rollback-targets'))
        } catch (failure) {
          setError(failure.message ?? String(failure))
        } finally {
          setBusy(false)
        }
      }, [])

      const loadVersion = useCallback(async () => {
        setBusy(true); setQuickError(null)
        try {
          const [fast, local] = await Promise.all([
            api('/quick').catch((failure) => { setQuickError(failure.message ?? String(failure)); return null }),
            api('/detect?offline=1').catch(() => null),
          ])
          if (fast) setQuick(fast)
          if (local) setDetect(current => current ?? local)
        } finally {
          setBusy(false)
        }
      }, [])

      const press = (next) => {
        if (view === next) { setView(null); return }
        setView(next)
        setError(null)
        if (next === 'detect') { void loadDetect(); return }
        if (next === 'rollback') { void loadRollback(); return }
        void loadVersion()
      }

      const doRollback = async (row) => {
        if (armedKey !== row.key) { setArmedKey(row.key); return }
        setArmedKey(null); setBusy(true); setRollbackError(null); setRollbackResult(null)
        try {
          const payload = row.payload.kind === 'npm'
            ? await post('/rollback-npm', { version: row.payload.version })
            : await post('/rollback-source', { target: row.payload.target, backup: row.payload.backup })
          setRollbackResult(payload?.version || row.title)
          setTargets(await api('/rollback-targets'))
        } catch (failure) {
          setRollbackError(failure.message ?? String(failure))
        } finally {
          setBusy(false)
        }
      }

      const button = (id, label, icon) => h('button', {
        type: 'button',
        className: 'dshu-btn',
        'data-open': view === id ? '1' : '0',
        'data-busy': busy && view === id ? '1' : '0',
        title: `${t('title')} · ${label}`,
        onClick: () => { press(id) },
      }, icon ? h('span', { 'aria-hidden': 'true' }, icon) : null, h('span', null, label))

      return h('div', { className: 'dshu-root', ref: rootRef },
        button('detect', t('detect'), '↻'),
        button('rollback', t('rollback'), '↩'),
        button('version', t('version'), 'ⓘ'),
        view === null ? null : h('div', { className: 'dshu-panel', role: 'dialog', 'aria-label': t('title') },
          h('div', { className: 'dshu-head' },
            h('span', { className: 'dshu-title' },
              t('title') + ' · ' + (view === 'detect' ? t('detect') : view === 'rollback' ? t('rollback') : t('version'))),
            h('button', { type: 'button', className: 'dshu-x', 'aria-label': t('close'), onClick: () => { setView(null) } }, '✕'),
          ),
          busy && (view !== 'detect' || detect === null) ? h(Spinner) : null,
          error ? h('div', { className: 'dshu-err' }, error) : null,
          view === 'detect' && detect !== null
            ? h(DetectRows, { data: detect, upstreamError, upstreamPending })
            : null,
          view === 'rollback' && targets !== null
            ? h(RollbackRows, {
              data: targets,
              onRollback: row => { void doRollback(row) },
              busyKey: armedKey ?? (busy ? '__busy' : null),
              result: rollbackResult,
              error: rollbackError,
            })
            : null,
          view === 'version'
            ? h(VersionView, { quick, local: detect, quickError })
            : null,
        ),
      )
    }

    module.exports = {
      name: 'dsh-updater',
      inject: ['slots', 'locale'],
      apply(ctx) {
        LOCALE = ctx.locale ?? null
        injectStyle()
        ctx.slots.inject('conversation.session.header.actions', () => ctx.slots.register({
          name: 'conversation.session.header.actions',
          id: 'dsh-updater',
          // 排在「后台任务」后面（ui-jobs 是 20）
          order: 30,
        }, UpdaterBar))
      },
    }

    return module.exports
  },
})
