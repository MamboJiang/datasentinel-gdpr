import {
  Activity,
  Bell,
  Check,
  ChevronsUpDown,
  Database,
  FileSearch,
  Gauge,
  LayoutDashboard,
  Menu,
  Plus,
  Search,
  Settings2,
  X,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useEffect, useState, type CSSProperties } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { AccountMenu } from './AccountMenu'
import {
  SIDEBAR_COLLAPSED_WIDTH,
  SIDEBAR_DEFAULT_WIDTH,
  SidebarResizeHandle,
} from './SidebarResizeHandle'
import { useData } from '../data/useData'
import { utilityPageTitles, workspaceSimulation } from '../data/sessionSimulation'
import { useI18n } from '../i18n'

const workspaces = [
  workspaceSimulation,
]

type NavigationItem = {
  end?: boolean
  icon: LucideIcon
  label: string
  to: string
}

const navigation: NavigationItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/sources', label: 'Sources', icon: Database },
  { to: '/findings', label: 'Findings', icon: FileSearch },
  { to: '/audit', label: 'Audit trail', icon: Activity },
  { to: '/evaluation', label: 'Evaluation', icon: Gauge },
  { to: '/governance', label: 'Governance', icon: Settings2 },
]

function getPageTitle(pathname: string) {
  if (pathname.startsWith('/findings/')) {
    return 'Finding Detail'
  }

  return navigation.find(({ to, end }) => (end ? pathname === to : pathname.startsWith(to)))?.label ?? utilityPageTitles[pathname] ?? 'DataSentinel'
}

export function AppShell() {
  const { t } = useI18n()
  const { notifications, dismissNotification, clearNotifications } = useData()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_DEFAULT_WIDTH)
  const [workspaceOpen, setWorkspaceOpen] = useState(false)
  const [workspaceQuery, setWorkspaceQuery] = useState('')
  const [accountOpen, setAccountOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [navQuery, setNavQuery] = useState('')
  const pageTitle = t(getPageTitle(location.pathname))
  const visibleWorkspaces = workspaces.filter(({ name }) => name.toLowerCase().includes(workspaceQuery.toLowerCase()))
  const visibleNavigation = navigation.filter(({ label }) => t(label).toLowerCase().includes(navQuery.toLowerCase()))
  const activeSidebarWidth = sidebarCollapsed ? SIDEBAR_COLLAPSED_WIDTH : sidebarWidth
  const shellStyle = { '--sidebar-width': `${activeSidebarWidth}px` } as CSSProperties
  const latestNotificationMessage = notifications[0]?.message ?? ''

  function closeWorkspaceSwitcher() {
    setWorkspaceOpen(false)
    setWorkspaceQuery('')
  }

  function closeAccountMenu() {
    setAccountOpen(false)
  }

  function closeNotifications() {
    setNotificationsOpen(false)
  }

  useEffect(() => {
    if (!workspaceOpen) {
      return
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setWorkspaceOpen(false)
        setWorkspaceQuery('')
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [workspaceOpen])

  useEffect(() => {
    if (!accountOpen) {
      return
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setAccountOpen(false)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [accountOpen])

  useEffect(() => {
    if (!notificationsOpen) {
      return
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setNotificationsOpen(false)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [notificationsOpen])

  return (
    <div className="app-shell" style={shellStyle}>
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''} ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <div className="workspace-header">
          <button
            aria-controls="workspace-switcher-panel"
            aria-expanded={workspaceOpen}
            aria-haspopup="dialog"
            className="workspace-trigger"
            onClick={() => {
              if (workspaceOpen) {
                closeWorkspaceSwitcher()
                return
              }

              closeAccountMenu()
              closeNotifications()
              setWorkspaceOpen(true)
            }}
            type="button"
          >
            <span className="workspace-avatar" aria-hidden="true">DS</span>
            <span className="workspace-trigger-copy">
              <strong>{workspaceSimulation.name}</strong>
              <span>{t('Privacy workspace')}</span>
            </span>
            <span className="workspace-plan">{workspaceSimulation.plan}</span>
            <ChevronsUpDown aria-hidden="true" size={16} />
          </button>
          <button className="sidebar-close" type="button" aria-label={t('Close navigation')} onClick={() => setMobileOpen(false)}>
            <X aria-hidden="true" size={18} />
          </button>
        </div>

        {workspaceOpen ? (
          <>
            <button className="workspace-backdrop" type="button" aria-label={t('Close workspace switcher')} onClick={closeWorkspaceSwitcher} />
            <section className="workspace-popover" id="workspace-switcher-panel" role="dialog" aria-label={t('Workspace switcher')}>
              <label className="workspace-search">
                <Search aria-hidden="true" size={15} />
                <span className="sr-only">{t('Find workspace')}</span>
                <input
                  aria-label={t('Find workspace')}
                  autoFocus
                  onChange={(event) => setWorkspaceQuery(event.target.value)}
                  placeholder={t('Find workspace...')}
                  type="search"
                  value={workspaceQuery}
                />
                <kbd>Esc</kbd>
              </label>

              <div className="workspace-list" role="group" aria-label={t('Available workspaces')}>
                {visibleWorkspaces.map((workspace) => (
                  <button className="workspace-option workspace-option-active" key={workspace.id} onClick={closeWorkspaceSwitcher} type="button">
                    <span className="workspace-option-avatar" aria-hidden="true">DS</span>
                    <span>
                      <strong>{workspace.name}</strong>
                      <small>{t(workspace.description)}</small>
                    </span>
                    <span className="workspace-plan">{workspace.plan}</span>
                    <Check aria-hidden="true" size={15} />
                  </button>
                ))}
                {visibleWorkspaces.length === 0 ? <span className="workspace-no-results">{t('No workspace matches')}</span> : null}
              </div>

              <button className="workspace-create" type="button" onClick={closeWorkspaceSwitcher}>
                <Plus aria-hidden="true" size={17} />
                <span>
                  <strong>{t('Create workspace')}</strong>
                  <small>{t('Collaborate with reviewers')}</small>
                </span>
              </button>
            </section>
          </>
        ) : null}

        <label className="sidebar-search">
          <Search aria-hidden="true" size={16} />
          <span className="sr-only">{t('Quick search')}</span>
          <input aria-label={t('Quick search')} onChange={(event) => setNavQuery(event.target.value)} placeholder={t('Quick search...')} type="search" value={navQuery} />
          <kbd>⌘K</kbd>
        </label>

        <nav aria-label={t('Primary navigation')}>
          {visibleNavigation.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
              end={end}
              key={to}
              onClick={() => setMobileOpen(false)}
              to={to}
            >
              <Icon aria-hidden="true" size={18} strokeWidth={2} />
              <span>{t(label)}</span>
            </NavLink>
          ))}
          {visibleNavigation.length === 0 ? <span className="nav-empty">{t('No navigation matches')}</span> : null}
        </nav>

        <AccountMenu
          accountOpen={accountOpen}
          onClose={closeAccountMenu}
          onCloseWorkspace={closeWorkspaceSwitcher}
          onToggle={() => {
            closeWorkspaceSwitcher()
            closeNotifications()
            setAccountOpen((isOpen) => !isOpen)
          }}
          onToggleSidebar={() => {
            closeWorkspaceSwitcher()
            closeAccountMenu()
            closeNotifications()
            setSidebarCollapsed((isCollapsed) => !isCollapsed)
          }}
          sidebarCollapsed={sidebarCollapsed}
        />
        <SidebarResizeHandle
          collapsed={sidebarCollapsed}
          onInteractionStart={() => {
            closeWorkspaceSwitcher()
            closeAccountMenu()
          }}
          onResize={({ collapsed, width }) => {
            setSidebarCollapsed(collapsed)

            if (!collapsed) {
              setSidebarWidth(width)
            }
          }}
          width={sidebarWidth}
        />
      </aside>

      <div className="content-shell">
        <header className="topbar">
          <button className="mobile-menu" type="button" aria-label={t('Open navigation')} onClick={() => setMobileOpen(true)}>
            <Menu aria-hidden="true" size={20} />
          </button>
          <strong className="topbar-title">{pageTitle}</strong>
          <button
            aria-controls="notification-panel"
            aria-expanded={notificationsOpen}
            aria-haspopup="dialog"
            className={`topbar-notification ${notificationsOpen ? 'topbar-notification-active' : ''}`}
            onClick={() => {
              closeWorkspaceSwitcher()
              closeAccountMenu()
              setNotificationsOpen((isOpen) => !isOpen)
            }}
            type="button"
            aria-label={t('Notifications')}
          >
            <Bell aria-hidden="true" size={18} />
            {notifications.length > 0 ? <span className="notification-dot" aria-hidden="true" /> : null}
          </button>
          <span className="sr-only" role="status" aria-live="polite" aria-atomic="true">
            {latestNotificationMessage}
          </span>
          {notificationsOpen ? (
            <>
              <button className="notification-backdrop" type="button" aria-label={t('Close notifications')} onClick={closeNotifications} />
              <section className="notification-popover" id="notification-panel" role="dialog" aria-label={t('Notifications')}>
                <div className="notification-header">
                  <strong>{t('Notifications')}</strong>
                  <button type="button" onClick={clearNotifications} disabled={notifications.length === 0}>
                    {t('Clear all')}
                  </button>
                </div>

                {notifications.length > 0 ? (
                  <ol className="notification-list">
                    {notifications.map((notification) => (
                      <li className="notification-item" key={notification.id}>
                        <span>{notification.message}</span>
                        <time dateTime={notification.createdAt}>{formatNotificationTime(notification.createdAt)}</time>
                        <button
                          type="button"
                          aria-label={t('Dismiss notification')}
                          onClick={() => dismissNotification(notification.id)}
                        >
                          <X aria-hidden="true" size={15} />
                        </button>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="notification-empty">{t('No notifications yet')}</p>
                )}
              </section>
            </>
          ) : null}
        </header>

        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

function formatNotificationTime(value: string) {
  const parsed = new Date(value)

  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(parsed)
}
