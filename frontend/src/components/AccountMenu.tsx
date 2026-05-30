import { Monitor, Moon, MoreHorizontal, PanelLeftClose, PanelLeftOpen, Settings2, Sun } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { accountSimulation, utilityRoutes } from '../data/sessionSimulation'
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
  const [themeMode, setThemeMode] = useState<ThemeMode>(getStoredThemeMode)

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
          <button className="account-backdrop" type="button" aria-label="Close account menu" onClick={onClose} />
          <section className="account-popover" id="account-menu-panel" role="dialog" aria-label="Account menu">
            <div className="account-popover-header">
              <div>
                <strong>{accountSimulation.name}</strong>
                <span>{accountSimulation.email}</span>
              </div>
              {settingsRoute ? (
                <Link className="account-settings" to={settingsRoute.path} aria-label={settingsRoute.label} onClick={onClose}>
                  <Settings2 aria-hidden="true" size={20} />
                </Link>
              ) : null}
            </div>

            <div className="account-menu-list">
              <div className="account-menu-row account-theme-row">
                <span>Theme</span>
                <span className="theme-control" role="group" aria-label="Theme options">
                  {themeOptions.map(({ icon: Icon, label, mode }) => (
                    <button
                      aria-label={label}
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

              {menuRoutes.map(({ label, path, icon: Icon }) => (
                <Link className="account-menu-row" key={path} to={path} onClick={onClose}>
                  <span>{label}</span>
                  <Icon aria-hidden="true" size={19} />
                </Link>
              ))}
            </div>

            {planRoute ? (
              <Link className="upgrade-button" to={planRoute.path} onClick={onClose}>
                {planRoute.label}
              </Link>
            ) : null}

            {statusRoute ? (
              <Link className="platform-status" to={statusRoute.path} onClick={onClose}>
                <span>Platform Status</span>
                <strong>All systems normal.</strong>
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
          <span className="account-avatar" aria-hidden="true">AS</span>
          <span>
            <strong>{accountSimulation.name}</strong>
            <small>{accountSimulation.email}</small>
          </span>
        </button>
        <button
          className="account-icon-button"
          type="button"
          aria-label="Open account menu"
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
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
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
