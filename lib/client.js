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
  id: 'dsh-updater-plugin',
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
        detect: '更新器', rollback: '回滚', version: '版本',
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
        githubRef: 'GitHub', npmRef: 'npm', noPython: '未找到（更新/回滚不可用）',
        doUpdate: '更新', confirmUpdate: '确认更新？', updating: '处理中…（下载可能要几分钟）',
        updaterLaunched: '已打开桌面更新器窗口',
        updaterLaunchedHint: '在窗口里点「更新」即可：它会先关掉 DSH、备份旧目录、替换并构建，完成后重新启动 DSH',
        updateStaged: '更新包已就绪', updateApplied: '更新完成',
        updateCloseHint: '现在关闭 DSH：关闭后将自动替换、构建并重新启动（约 2~5 分钟）。如果同一目录开了多个 DSH 实例，请都关掉。',
        updateCloseHintManual: '现在关闭 DSH：关闭后会自动替换并构建；完成后请手动启动 DSH。',
        updateApplying: '正在应用更新…', updateApplyingHint: '完成前请不要启动 DSH。',
        updateDoneLast: '上次更新完成', updateFailedLast: '上次更新失败',
        updateExpired: '等待关闭 DSH 超时，这次更新已放弃', updateCanceled: '这次更新已取消',
        updateLogHint: '日志', refreshPage: '刷新本页即可看到新版本。',
        cancelUpdate: '取消更新',
        retryApply: '重试应用',
        updateOccupied: '更新被占用阻塞：先把所有从该目录启动的 DSH 都关掉，再点「重试应用」。',
        updateDialogTitle: '更新 DSH',
        updateDialogFrom: '当前', updateDialogTo: '最新',
        updateOptionAutoClose: '更新时自动关闭 DSH（完成后自动重启，复刻桌面版体验）',
        updateOptionInstall: '替换后自动运行 pnpm install（推荐）',
        updateOptionBuild: '替换后自动运行 pnpm run build（源码版启动必需）',
        startUpdate: '开始更新',
        useDesktopUpdater: '改用桌面更新器',
        updateStaging: '正在下载官方源码并暂存…（可能要几分钟，请勿关闭页面）',
        updateAutoCloseApplying: '正在关闭 DSH 并应用更新',
        updateAutoCloseHint: 'DSH 会短暂断开；完成后会自动重启，本页也会自动刷新。',
        waitingRestart: '正在等待 DSH 重启…',
        cancelStaging: '取消更新',
        phasePreparing: '正在准备…', phaseDownloading: '正在下载官方源码…',
        phaseExtracting: '正在解压官方源码…', phaseStaging: '正在暂存新源码…',
        updateProgressHint: '下载期间可以取消；暂存完成后看护进程会自动关闭 DSH 并更新',
        title: 'DSH 自动更新器',
      },
      en: {
        detect: 'Updater', rollback: 'Roll back', version: 'Version',
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
        doUpdate: 'Update', confirmUpdate: 'Confirm?', updating: 'Working… (download may take minutes)',
        updaterLaunched: 'Updater window opened',
        updaterLaunchedHint: 'Click Update in that window: it closes DSH, backs up the old folder, replaces and rebuilds, then restarts DSH',
        updateStaged: 'Update staged', updateApplied: 'Update complete',
        updateCloseHint: 'Close DSH now: it will be replaced, rebuilt and restarted automatically (~2–5 min). Close every DSH instance started from that folder.',
        updateCloseHintManual: 'Close DSH now: it will be replaced and rebuilt; start DSH manually afterwards.',
        updateApplying: 'Applying update…', updateApplyingHint: 'Do not start DSH before it finishes.',
        updateDoneLast: 'Last update completed', updateFailedLast: 'Last update failed',
        updateExpired: 'Timed out waiting for DSH to close; update abandoned', updateCanceled: 'Update cancelled',
        updateLogHint: 'Log', refreshPage: 'Refresh this page to see the new version.',
        cancelUpdate: 'Cancel update',
        retryApply: 'Retry',
        updateOccupied: 'Update blocked by a busy folder: close every DSH instance started from that folder, then click Retry.',
        updateDialogTitle: 'Update DSH',
        updateDialogFrom: 'current', updateDialogTo: 'latest',
        updateOptionAutoClose: 'Close DSH automatically during the update (restart when done)',
        updateOptionInstall: 'Run pnpm install after replacing (recommended)',
        updateOptionBuild: 'Run pnpm run build after replacing (required for source builds)',
        startUpdate: 'Start update',
        useDesktopUpdater: 'Use desktop updater',
        updateStaging: 'Downloading and staging the official source… (may take minutes; keep the page open)',
        updateAutoCloseApplying: 'Closing DSH and applying the update',
        updateAutoCloseHint: 'DSH disconnects briefly; it restarts automatically and this page reloads itself.',
        waitingRestart: 'Waiting for DSH to restart…',
        cancelStaging: 'Cancel update',
        phasePreparing: 'Preparing…', phaseDownloading: 'Downloading official source…',
        phaseExtracting: 'Extracting…', phaseStaging: 'Staging new source…',
        updateProgressHint: 'You can cancel while downloading; once staged the watcher closes DSH and updates automatically',
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
.dshu-banner { margin: 6px 0 4px; padding: 6px 8px; border-radius: var(--dsw-radius-xs, 6px); background: var(--dsw-alias-interactive-bg-hover, rgba(0,0,0,.05)); }
.dshu-banner[data-tone="ok"] { background: var(--dsw-alias-state-success-tertiary, rgba(22,163,74,.14)); }
.dshu-banner[data-tone="err"] { background: var(--dsw-alias-state-error-tertiary, rgba(220,38,38,.12)); }
.dshu-banner-main { font-weight: 600; }
.dshu-banner-sub { color: var(--dsw-alias-label-caption, #9ca3af); font-size: 11px; margin-top: 2px; word-break: break-word; }
.dshu-banner-actions { display: flex; gap: 6px; margin-top: 6px; }
.dshu-act:disabled { opacity: .55; cursor: default; }
.dshu-dialog { margin: 8px 0 4px; padding: 10px; border: 1px solid var(--dsw-alias-border-l2, rgba(0,0,0,.12)); border-radius: var(--dsw-radius-s, 8px); background: var(--dsw-alias-bg-l1, rgba(0,0,0,.03)); }
.dshu-dialog-title { font-weight: 600; font-size: 12px; margin-bottom: 2px; }
.dshu-dialog-path { color: var(--dsw-alias-label-caption, #9ca3af); font-size: 11px; word-break: break-all; }
.dshu-dialog-vers { font-size: 11px; margin: 4px 0 6px; }
.dshu-check { display: flex; align-items: flex-start; gap: 6px; font-size: 11px; padding: 3px 0; cursor: pointer; }
.dshu-check input { margin: 1px 0 0 0; flex: none; }
.dshu-dialog-actions { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
.dshu-act-primary { color: var(--dsw-alias-button-primary-label, #fff); background: var(--dsw-alias-button-primary-fill, #2563eb); border-color: transparent; }
.dshu-act-primary:hover { background: var(--dsw-alias-button-primary-fill-hover, #1d4ed8); }
.dshu-progress { margin-top: 8px; }
.dshu-progress-track { height: 6px; border-radius: 999px; background: var(--dsw-alias-interactive-bg-hover, rgba(0,0,0,.1)); overflow: hidden; }
.dshu-progress-fill { height: 100%; border-radius: 999px; background: var(--dsw-alias-button-primary-fill, #2563eb); transition: width .3s ease; }
.dshu-progress-text { margin-top: 3px; color: var(--dsw-alias-label-caption, #9ca3af); font-size: 11px; word-break: break-word; }
.dshu-spacer { flex: 1; }
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
    function UpdateBanner({ pending, busy, onCancel, onRetry }) {
      if (!pending?.present) return null
      const status = pending.status
      const versions = `${pending.old_version || '—'} → ${pending.new_version || '—'}`
      const stuck = Boolean(pending.error) && (status === 'waiting' || status === 'failed')
      const showRetry = Boolean(pending.can_retry) && stuck
      let main = ''
      let sub = ''
      let tone = 'hint'
      if (stuck) {
        main = `${t('updateStaged')}：${versions}`
        sub = `${t('updateOccupied')}${pending.error ? ' · ' + pending.error : ''}`
        tone = 'err'
      } else if (status === 'waiting') {
        main = `${t('updateStaged')}：${versions}`
        sub = pending.restart ? t('updateCloseHint') : t('updateCloseHintManual')
      } else if (status === 'applying') {
        main = t('updateApplying')
        sub = t('updateApplyingHint')
      } else if (status === 'done') {
        main = `${t('updateDoneLast')}：${versions}`
        sub = t('refreshPage')
        tone = 'ok'
      } else if (status === 'failed') {
        main = `${t('updateFailedLast')}：${versions}`
        sub = `${pending.error || ''}${pending.log_file ? ' · ' + t('updateLogHint') + ': ' + pending.log_file : ''}`
        tone = 'err'
      } else if (status === 'expired') {
        main = t('updateExpired')
        tone = 'err'
      } else if (status === 'canceled') {
        main = t('updateCanceled')
      } else {
        return null
      }
      const actions = []
      if (showRetry) {
        actions.push(h('button', {
          type: 'button', className: 'dshu-act', disabled: Boolean(busy),
          onClick: () => onRetry(),
        }, t('retryApply')))
      }
      if (status === 'waiting' || status === 'failed') {
        actions.push(h('button', {
          type: 'button', className: 'dshu-act', disabled: Boolean(busy),
          onClick: () => onCancel(),
        }, t('cancelUpdate')))
      }
      return h('div', { className: 'dshu-banner', 'data-tone': tone },
        h('div', { className: 'dshu-banner-main' }, main),
        sub ? h('div', { className: 'dshu-banner-sub' }, sub) : null,
        actions.length ? h('div', { className: 'dshu-banner-actions' }, actions) : null,
      )
    }

    function DetectRows({ data, upstreamError, upstreamPending, pending, busy,
                          updatingPath, onUpdate, onCancel, onRetry }) {
      const installs = data?.installs ?? []
      if (installs.length === 0) {
        return h('div', null,
          h(UpdateBanner, { pending, busy, onCancel, onRetry }),
          h('div', { className: 'dshu-hint' }, t('noInstalls')))
      }
      return h('div', null,
        h(UpdateBanner, { pending, busy, onCancel, onRetry }),
        installs.map((row, index) => {
          const canUpdate = row.updateable && row.status === 'update-available'
          const updating = updatingPath === row.path
          return h('div', { className: 'dshu-row', key: row.path + index },
            h('span', { className: 'dshu-main' },
              h('span', { className: 'dshu-name', title: row.path }, baseName(row.path)),
              h('span', { className: 'dshu-sub', title: row.path },
                kindLabel(row.kind)
                + ' · ' + (row.version || '—')
                + (row.ref_version ? ` → ${row.ref_kind === 'github' ? t('githubRef') : t('npmRef')} ${row.ref_version}` : '')),
            ),
            h('span', { className: 'dshu-tag', 'data-kind': row.status }, statusLabel(row.status)),
            canUpdate
              ? h('button', {
                type: 'button', className: 'dshu-act',
                disabled: Boolean(busy) || Boolean(updatingPath),
                onClick: () => onUpdate(row),
              }, updating ? t('updating') : t('doUpdate'))
              : null,
          )
        }),
        upstreamPending ? h('div', { className: 'dshu-hint' }, t('localOnly')) : null,
        upstreamError ? h('div', { className: 'dshu-err' }, `${t('officialFailed')}：${upstreamError}`) : null,
      )
    }

    const fmtBytes = value => {
      const n = Number(value) || 0
      if (n >= 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + ' MB'
      if (n >= 1024) return (n / 1024).toFixed(0) + ' KB'
      return Math.round(n) + ' B'
    }
    const fmtSpeed = value => {
      const n = Number(value) || 0
      if (n >= 1024 * 1024) return (n / 1024 / 1024).toFixed(2) + ' MB/s'
      if (n >= 1024) return (n / 1024).toFixed(0) + ' KB/s'
      return Math.round(n) + ' B/s'
    }
    const fmtEta = seconds => {
      const s = Math.max(0, Math.round(Number(seconds) || 0))
      if (s < 60) return s + 's'
      return Math.floor(s / 60) + 'm ' + (s % 60) + 's'
    }
    function phaseLabel(phase) {
      if (phase === 'preparing') return t('phasePreparing')
      if (phase === 'downloading') return t('phaseDownloading')
      if (phase === 'extracting') return t('phaseExtracting')
      if (phase === 'staging') return t('phaseStaging')
      return ''
    }
    /** 进度一句话：`正在下载官方源码… 37% · 12.3 MB / 33.1 MB · 1.2 MB/s · 18s` */
    function progressLine(progress) {
      if (!progress || !progress.phase) return ''
      const pct = Math.max(0, Math.min(100, Number(progress.percent) || 0))
      const pieces = []
      if (progress.total) pieces.push(`${fmtBytes(progress.done)} / ${fmtBytes(progress.total)}`)
      if (progress.speed) pieces.push(fmtSpeed(progress.speed))
      if (progress.eta) pieces.push(fmtEta(progress.eta))
      return `${phaseLabel(progress.phase)} ${pct.toFixed(0)}%${pieces.length ? ' · ' + pieces.join(' · ') : ''}`
    }

    /** 插件内「复刻桌面 EXE」的更新对话框：目标/版本 + 三个选项 + 进度条 + 开始更新。 */
    function UpdateDialog({ row, autoClose, install, build, busy, staging, progress,
                            onToggleAutoClose, onToggleInstall, onToggleBuild,
                            onStart, onClose, onDesktop, onCancelStaging }) {
      const locked = Boolean(busy) || Boolean(staging)
      const checkbox = (checked, label, onToggle) => h('label', { className: 'dshu-check' },
        h('input', {
          type: 'checkbox', checked: Boolean(checked), disabled: locked,
          onChange: onToggle,
        }),
        h('span', null, label))
      const pct = Math.max(0, Math.min(100, Number(progress?.percent) || 0))
      return h('div', { className: 'dshu-dialog' },
        h('div', { className: 'dshu-dialog-title' }, t('updateDialogTitle')),
        h('div', { className: 'dshu-dialog-path', title: row.update_target || row.path },
          row.update_target || row.path),
        h('div', { className: 'dshu-dialog-vers' },
          `${t('updateDialogFrom')} ${row.version || '—'}  →  ${t('updateDialogTo')} ${row.ref_version || '—'}`),
        checkbox(autoClose, t('updateOptionAutoClose'), onToggleAutoClose),
        checkbox(install, t('updateOptionInstall'), onToggleInstall),
        checkbox(build, t('updateOptionBuild'), onToggleBuild),
        staging
          ? h('div', { className: 'dshu-progress' },
            h('div', { className: 'dshu-progress-track' },
              h('div', { className: 'dshu-progress-fill', style: { width: `${pct}%` } })),
            h('div', { className: 'dshu-progress-text' }, progressLine(progress) || t('updateStaging')),
            h('div', { className: 'dshu-banner-sub' }, t('updateProgressHint')))
          : (busy ? h('div', { className: 'dshu-hint' }, t('updateStaging')) : null),
        h('div', { className: 'dshu-dialog-actions' },
          staging
            ? h('button', {
              type: 'button', className: 'dshu-act', onClick: onCancelStaging,
            }, t('cancelStaging'))
            : h('button', {
              type: 'button', className: 'dshu-act dshu-act-primary',
              disabled: locked, onClick: onStart,
            }, t('startUpdate')),
          h('button', {
            type: 'button', className: 'dshu-act', disabled: locked, onClick: onClose,
          }, t('close')),
          h('button', {
            type: 'button', className: 'dshu-act', disabled: locked, onClick: onDesktop,
          }, t('useDesktopUpdater')),
        ),
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
      const [pending, setPending] = useState(null)
      const [updatingPath, setUpdatingPath] = useState(null)
      const [updateNotice, setUpdateNotice] = useState(null)
      const [updateError, setUpdateError] = useState(null)
      const [dialogRow, setDialogRow] = useState(null)
      const [dialogAutoClose, setDialogAutoClose] = useState(true)
      const [dialogInstall, setDialogInstall] = useState(false)
      const [dialogBuild, setDialogBuild] = useState(false)
      const [dialogBusy, setDialogBusy] = useState(false)
      const [applyPhase, setApplyPhase] = useState(null)
      const [staging, setStaging] = useState(false)
      const [stagingAutoClose, setStagingAutoClose] = useState(true)
      const [progress, setProgress] = useState(null)
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

      // 自动关闭模式：DSH 会先断开，轮询到它重新监听端口后自动刷新页面
      useEffect(() => {
        if (applyPhase !== 'waiting-restart') return undefined
        let stopped = false
        let attempts = 0
        let sawDown = false
        const startedAt = Date.now()
        let timer = null
        const tick = async () => {
          if (stopped) return
          attempts += 1
          try {
            await api('/quick')
            // 正常情况：先看到断开、再看到恢复，说明「新 DSH 已经起来了」，刷新才安全。
            // 兜底：如果没观察到断开（进度轮询慢/页面晚到），12 秒后也刷新，
            // 避免 DSH 已经重启完成、页面却一直停在「正在等待 DSH 重启」。
            if (sawDown || Date.now() - startedAt > 12000) { location.reload(); return }
          } catch {
            sawDown = true
          }
          if (attempts > 240) { setApplyPhase(null); return }
          timer = setTimeout(tick, 2000)
        }
        timer = setTimeout(tick, 1500)
        return () => { stopped = true; if (timer) clearTimeout(timer) }
      }, [applyPhase])

      // 下载/暂存阶段：轮询 update-progress.json 显示进度条（暂存在后台 worker 里跑）
      useEffect(() => {
        if (!staging) return undefined
        let stopped = false
        let timer = null
        const tick = async () => {
          if (stopped) return
          try {
            const data = await api('/update-progress')
            if (stopped) return
            if (data && data.phase) setProgress(data)
            if (data?.phase === 'failed') {
              setStaging(false)
              setDialogBusy(false)
              setUpdateError(data.message || t('updateFailedLast'))
              return
            }
            if (data?.phase === 'staged' || data?.phase === 'canceled') {
              setStaging(false)
              setDialogBusy(false)
              setDialogRow(null)
              if (data.phase === 'canceled') {
                setUpdateNotice(t('updateCanceled'))
              } else if (stagingAutoClose) {
                setApplyPhase('waiting-restart')
                void loadPending()
              } else {
                setUpdateNotice(t('updateStaged'))
                void loadPending()
              }
              return
            }
          } catch { /* DSH 忙 / 暂时读不到，继续轮询 */ }
          timer = setTimeout(tick, 1200)
        }
        timer = setTimeout(tick, 700)
        return () => { stopped = true; if (timer) clearTimeout(timer) }
      }, [staging, stagingAutoClose])

      const loadPending = useCallback(async () => {
        try {
          setPending(await api('/update-status'))
        } catch {
          /* 旧版 Host 没有这个接口时，待应用更新一栏留空即可 */
        }
      }, [])

      const loadDetect = useCallback(async () => {
        setBusy(true); setError(null); setUpstreamError(null)
        setUpdateError(null); setUpdateNotice(null)
        void loadPending()
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

      // 「更新」按钮：打开插件内更新对话框（复刻桌面 EXE 的体验），
      // 也可以从对话框里改用桌面更新器窗口（EXE）。
      const doUpdate = (row) => {
        setDialogRow(row)
        setDialogAutoClose(true)
        setDialogInstall(false)
        setDialogBuild(false)
        setUpdateError(null)
        setUpdateNotice(null)
      }

      const doLaunchDesktopUpdater = async () => {
        setDialogBusy(true)
        setUpdateError(null)
        try {
          const launched = await post('/launch-updater', {})
          setDialogRow(null)
          setUpdateNotice(`${t('updaterLaunched')}：${launched?.path || ''} · ${t('updaterLaunchedHint')}`)
        } catch (failure) {
          setUpdateError(failure.message ?? String(failure))
        } finally {
          setDialogBusy(false)
        }
      }

      const doStartUpdate = async () => {
        if (dialogRow === null) return
        const row = dialogRow
        setDialogBusy(true)
        setUpdateError(null)
        setUpdateNotice(null)
        setProgress(null)
        try {
          const target = row.update_target || row.path
          const payload = await post('/update-source', {
            target,
            autoClose: dialogAutoClose,
            runInstall: dialogInstall,
            runBuild: dialogBuild,
          })
          if (payload?.started === true) {
            // 后台 worker 开始下载/暂存；对话框保持打开，轮询进度条
            setStagingAutoClose(payload.autoClose !== false)
            setStaging(true)
            return
          }
          setDialogRow(null)
          if (payload?.applied === true && payload.inUse === false) {
            setUpdateNotice(`${t('updateApplied')}：${payload.old_version || '—'} → ${payload.new_version || '—'}`)
            try { setDetect(await api('/detect?offline=1')) } catch { /* 刷新失败不影响结果 */ }
          } else if (payload?.auto_close === true) {
            setApplyPhase('waiting-restart')
            await loadPending()
          } else if (payload?.staged === true) {
            setUpdateNotice(t('updateStaged'))
            await loadPending()
          }
        } catch (failure) {
          setUpdateError(failure.message ?? String(failure))
        } finally {
          setDialogBusy(false)
        }
      }

      const doCancelStaging = async () => {
        setUpdateError(null)
        try {
          await api('/cancel-update', {
            method: 'POST',
            headers: { accept: 'application/json' },
          })
          // 下一轮进度轮询会看到 canceled 并把对话框关掉
        } catch (failure) {
          setUpdateError(failure.message ?? String(failure))
        }
      }

      const doCancelUpdate = async () => {
        setUpdatingPath('__cancel__')
        setUpdateError(null)
        try {
          await api('/cancel-update', {
            method: 'POST',
            headers: { accept: 'application/json' },
          })
          await loadPending()
        } catch (failure) {
          setUpdateError(failure.message ?? String(failure))
        } finally {
          setUpdatingPath(null)
        }
      }

      const doResumeUpdate = async () => {
        setUpdatingPath('__resume__')
        setUpdateError(null)
        try {
          await post('/resume-update', {})
          await loadPending()
        } catch (failure) {
          setUpdateError(failure.message ?? String(failure))
        } finally {
          setUpdatingPath(null)
        }
      }

      const button = (id, label, icon) => h('button', {
        type: 'button',
        className: 'dshu-btn',
        'data-open': view === id ? '1' : '0',
        'data-busy': busy && view === id ? '1' : '0',
        title: `${t('title')}${id === 'detect' ? '' : ' · ' + label}`,
        onClick: () => { press(id) },
      }, icon ? h('span', { 'aria-hidden': 'true' }, icon) : null, h('span', null, label))

      return h('div', { className: 'dshu-root', ref: rootRef },
        button('detect', t('detect'), '↻'),
        button('rollback', t('rollback'), '↩'),
        button('version', t('version'), 'ⓘ'),
        view === null ? null : h('div', { className: 'dshu-panel', role: 'dialog', 'aria-label': t('title') },
          h('div', { className: 'dshu-head' },
            h('span', { className: 'dshu-title' },
              t('title') + (view === 'detect' ? '' : ' · ' + (view === 'rollback' ? t('rollback') : t('version')))),
            h('button', { type: 'button', className: 'dshu-x', 'aria-label': t('close'), onClick: () => { setView(null) } }, '✕'),
          ),
          busy && (view !== 'detect' || detect === null) ? h(Spinner) : null,
          error ? h('div', { className: 'dshu-err' }, error) : null,
          updateNotice ? h('div', { className: 'dshu-ok' }, updateNotice) : null,
          updateError ? h('div', { className: 'dshu-err' }, updateError) : null,
          view === 'detect' && applyPhase === 'waiting-restart'
            ? h('div', { className: 'dshu-banner', 'data-tone': 'ok' },
              h('div', { className: 'dshu-banner-main' }, t('updateAutoCloseApplying')),
              h('div', { className: 'dshu-banner-sub' },
                t('updateAutoCloseHint') + ' · ' + t('waitingRestart')))
            : null,
          view === 'detect' && dialogRow !== null
            ? h(UpdateDialog, {
              row: dialogRow,
              autoClose: dialogAutoClose,
              install: dialogInstall,
              build: dialogBuild,
              busy: dialogBusy,
              staging,
              progress,
              onToggleAutoClose: () => setDialogAutoClose(value => !value),
              onToggleInstall: () => setDialogInstall(value => !value),
              onToggleBuild: () => setDialogBuild(value => !value),
              onStart: () => { void doStartUpdate() },
              onClose: () => { setDialogRow(null) },
              onDesktop: () => { void doLaunchDesktopUpdater() },
              onCancelStaging: () => { void doCancelStaging() },
            })
            : null,
          view === 'detect' && detect !== null
            ? h(DetectRows, {
              data: detect,
              upstreamError,
              upstreamPending,
              pending,
              busy: Boolean(updatingPath) || dialogBusy || Boolean(dialogRow),
              updatingPath,
              onUpdate: row => { void doUpdate(row) },
              onCancel: () => { void doCancelUpdate() },
              onRetry: () => { void doResumeUpdate() },
            })
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
