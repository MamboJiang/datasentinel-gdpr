import { Languages, Monitor, Moon, MoreHorizontal, PanelLeftClose, PanelLeftOpen, Settings2, Sun } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../data/AuthContext'
import { utilityRoutes } from '../data/sessionSimulation'
import { isLanguagePreferenceCode, languagePreferenceOptions, useI18n } from '../i18n'
import './AccountMenu.css'

type ThemeMode = 'system' | 'light' | 'dark'

const themeOptions: Array<{ icon: LucideIcon; label: string; mode: ThemeMode }> = [
  { icon: Monitor, label: 'Use system theme', mode: 'system' },
  { icon: Sun, label: 'Use light theme', mode: 'light' },
  { icon: Moon, label: 'Use dark theme', mode: 'dark' },
]

const menuRoutes = utilityRoutes.filter(({ path }) => ['/feedback', '/', '/changelog', '/help', '/docs', '/session'].includes(path))
const settingsRoute = utilityRoutes.find(({ path }) => path === '/account')
const statusRoute = utilityRoutes.find(({ path }) => path === '/status')
const planRoute = utilityRoutes.find(({ path }) => path === '/plan')

function getStoredThemeMode(): ThemeMode {
  if (typeof window === 'undefined') {
    return 'system'
  }

  const storedTheme = window.localStorage.getItem('datasentinel-theme-mode')
  return storedTheme === 'light' || storedTheme === 'dark' || storedTheme === 'system' ? storedTheme : 'system'
}

export function AccountMenu({
  accountOpen,
  onClose,
  onCloseWorkspace,
  onToggle,
  onToggleSidebar,
  sidebarCollapsed,
}: {
  accountOpen: boolean
  onClose: () => void
  onCloseWorkspace: () => void
  onToggle: () => void
  onToggleSidebar: () => void
  sidebarCollapsed: boolean
}) {
  const { language, setLanguage, t } = useI18n()
  const { session } = useAuth()
  const [themeMode, setThemeMode] = useState<ThemeMode>(getStoredThemeMode)
  const selectedLanguage = languagePreferenceOptions.find(({ code }) => code === language) ?? languagePreferenceOptions[0]
  const account = session.user ?? {
    displayName: 'Not signed in',
    email: null,
    provider: 'google',
    userId: '',
  }
  const accountInitials = getInitials(account.displayName)

  useEffect(() => {
    const root = document.documentElement
    const systemMatcher = window.matchMedia('(prefers-color-scheme: dark)')

    function applyTheme() {
      const resolvedTheme = themeMode === 'system' ? (systemMatcher.matches ? 'dark' : 'light') : themeMode
      root.dataset.theme = resolvedTheme
      root.dataset.themeMode = themeMode
      window.localStorage.setItem('datasentinel-theme-mode', themeMode)
    }

    applyTheme()
    systemMatcher.addEventListener('change', applyTheme)
    return () => systemMatcher.removeEventListener('change', applyTheme)
  }, [themeMode])

  return (
    <div className="account-dock">
      {accountOpen ? (
        <>
          <button className="account-backdrop" type="button" aria-label={t('Close account menu')} onClick={onClose} />
          <section className="account-popover" id="account-menu-panel" role="dialog" aria-label={t('Account menu')}>
            <div className="account-popover-header">
              <div>
                <strong>{account.displayName}</strong>
                <span>{account.email ?? t('Email unavailable')}</span>
              </div>
              {settingsRoute ? (
                <Link className="account-settings" to={settingsRoute.path} aria-label={t(settingsRoute.label)} onClick={onClose}>
                  <Settings2 aria-hidden="true" size={20} />
                </Link>
              ) : null}
            </div>

            <div className="account-menu-list">
              <div className="account-menu-row account-theme-row">
                <span>{t('Theme')}</span>
                <span className="theme-control" role="group" aria-label={t('Theme options')}>
                  {themeOptions.map(({ icon: Icon, label, mode }) => (
                    <button
                      aria-label={t(label)}
                      aria-pressed={themeMode === mode}
                      className="theme-option"
                      key={mode}
                      onClick={() => setThemeMode(mode)}
                      type="button"
                    >
                      <Icon aria-hidden="true" size={18} />
                    </button>
                  ))}
                </span>
              </div>

              <div className="account-menu-row account-language-row">
                <span className="language-copy">
                  <span className="language-title">
                    <Languages aria-hidden="true" size={15} />
                    <span>{t('Language')}</span>
                  </span>
                  <small>{t('{{language}} selected', { language: selectedLanguage.nativeLabel })}</small>
                </span>
                <select
                  aria-label={t('Language preference')}
                  className="language-select"
                  onChange={(event) => {
                    const nextLanguage = event.target.value

                    if (isLanguagePreferenceCode(nextLanguage)) {
                      setLanguage(nextLanguage)
                    }
                  }}
                  value={language}
                >
                  {languagePreferenceOptions.map(({ code, nativeLabel }) => (
                    <option key={code} value={code}>{nativeLabel} ({code})</option>
                  ))}
                </select>
              </div>

              {menuRoutes.map(({ label, path, icon: Icon }) => (
                <Link className="account-menu-row" key={path} to={path} onClick={onClose} reloadDocument={path === '/docs'}>
                  <span>{t(label)}</span>
                  <Icon aria-hidden="true" size={19} />
                </Link>
              ))}
            </div>

            {planRoute ? (
              <Link className="upgrade-button" to={planRoute.path} onClick={onClose}>
                {t(planRoute.label)}
              </Link>
            ) : null}

            {statusRoute ? (
              <Link className="platform-status" to={statusRoute.path} onClick={onClose}>
                <span>{t('Platform Status')}</span>
                <strong>{t('All systems normal.')}</strong>
                <i aria-hidden="true" />
              </Link>
            ) : null}
          </section>
        </>
      ) : null}

      <div className="account-footer">
        <button
          aria-controls="account-menu-panel"
          aria-expanded={accountOpen}
          aria-haspopup="dialog"
          className="account-trigger"
          onClick={() => {
            onCloseWorkspace()
            onToggle()
          }}
          type="button"
        >
          <span className="account-avatar" aria-hidden="true">{accountInitials}</span>
          <span>
            <strong>{account.displayName}</strong>
            <small>{account.email ?? t('Email unavailable')}</small>
          </span>
        </button>
        <button
          className="account-icon-button"
          type="button"
          aria-label={t('Open account menu')}
          onClick={() => {
            onCloseWorkspace()
            onToggle()
          }}
        >
          <MoreHorizontal aria-hidden="true" size={18} />
        </button>
        <button
          className="account-icon-button sidebar-toggle-button"
          type="button"
          aria-label={sidebarCollapsed ? t('Expand sidebar') : t('Collapse sidebar')}
          aria-pressed={sidebarCollapsed}
          onClick={() => {
            onCloseWorkspace()
            onClose()
            onToggleSidebar()
          }}
        >
          {sidebarCollapsed ? <PanelLeftOpen aria-hidden="true" size={18} /> : <PanelLeftClose aria-hidden="true" size={18} />}
        </button>
      </div>
    </div>
  )
}

function getInitials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('') || 'DS'
}
