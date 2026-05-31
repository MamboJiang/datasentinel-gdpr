import {
  Activity,
  Bell,
  Check,
  ChevronsUpDown,
  Database,
  FileSearch,
  Gauge,
  LayoutDashboard,
  Link2,
  Menu,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  UsersRound,
  X,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useEffect, useState, type CSSProperties } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { AccountMenu } from './AccountMenu'
import {
  SIDEBAR_COLLAPSED_WIDTH,
  SIDEBAR_DEFAULT_WIDTH,
  SidebarResizeHandle,
} from './SidebarResizeHandle'
import { WorkspaceAccessNotice } from './WorkspaceAccessNotice'
import { WorkspaceCreateForm } from './WorkspaceCreateForm'
import { useData } from '../data/useData'
import { utilityPageTitles } from '../data/sessionSimulation'
import { useI18n } from '../i18n'

const NOTIFICATION_PREVIEW_DURATION_MS = 4200

type NavigationItem = {
  children?: NavigationChild[]
  end?: boolean
  icon: LucideIcon
  label: string
  to: string
}

type NavigationChild = {
  end?: boolean
  icon?: LucideIcon
  label: string
  to: string
}

type PageTitleSegment = {
  label: string
  to?: string
}

const navigation: NavigationItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, end: true },
  {
    to: '/workspace/admin',
    label: 'Workspace admin',
    icon: ShieldCheck,
    children: [
      { to: '/workspace/admin/members', label: 'Members', icon: UsersRound },
    ],
  },
  { to: '/sources', label: 'Sources', icon: Database },
  { to: '/findings', label: 'Findings', icon: FileSearch },
  { to: '/audit', label: 'Audit trail', icon: Activity },
  { to: '/evaluation', label: 'Evaluation', icon: Gauge },
  { to: '/governance', label: 'Governance', icon: Settings2 },
]

function getPageTitleSegments(pathname: string): PageTitleSegment[] {
  if (pathname.startsWith('/workspace/admin/members')) {
    return [
      { label: 'Workspace admin', to: '/workspace/admin' },
      { label: 'Members' },
    ]
  }

  if (pathname.startsWith('/findings/')) {
    return [
      { label: 'Findings', to: '/findings' },
      { label: 'Finding Detail' },
    ]
  }

  if (pathname.startsWith('/workspace/invitations/')) {
    return [
      { label: 'Workspace invitation' },
    ]
  }

  return [
    { label: navigation.find(({ to, end }) => (end ? pathname === to : pathname.startsWith(to)))?.label ?? utilityPageTitles[pathname] ?? 'DataSentinel' },
  ]
}

function workspaceInitialsFor(name: string | undefined) {
  return name
    ? name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
    : 'WS'
}

export function AppShell() {
  const { t } = useI18n()
  const {
    acceptWorkspaceInvitation,
    notifications,
    dismissNotification,
    clearNotifications,
    workspaceAdmin,
    workspaceDirectory,
  } = useData()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_DEFAULT_WIDTH)
  const [workspaceOpen, setWorkspaceOpen] = useState(false)
  const [workspaceCreateOpen, setWorkspaceCreateOpen] = useState(false)
  const [workspaceQuery, setWorkspaceQuery] = useState('')
  const [accountOpen, setAccountOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [notificationPreviewId, setNotificationPreviewId] = useState<string | null>(null)
  const [navQuery, setNavQuery] = useState('')
  const pageTitleSegments = getPageTitleSegments(location.pathname)
  const pageTitle = pageTitleSegments.map(({ label }) => t(label)).join(' / ')
  const visibleWorkspaces = workspaceDirectory.workspaces.filter(({ name }) => name.toLowerCase().includes(workspaceQuery.toLowerCase()))
  const visibleNavigation = navigation.filter((item) => {
    const query = navQuery.toLowerCase()
    return t(item.label).toLowerCase().includes(query)
      || item.children?.some((child) => t(child.label).toLowerCase().includes(query))
  })
  const activeSidebarWidth = sidebarCollapsed ? SIDEBAR_COLLAPSED_WIDTH : sidebarWidth
  const shellStyle = { '--sidebar-width': `${activeSidebarWidth}px` } as CSSProperties
  const latestNotification = notifications[0]
  const latestNotificationId = latestNotification?.id
  const latestNotificationMessage = latestNotification?.message ?? ''
  const notificationPreview = notificationPreviewId ? notifications.find(({ id }) => id === notificationPreviewId) : undefined
  const isWorkspaceInviteRoute = location.pathname.startsWith('/workspace/invitations/')
  const currentWorkspace = visibleWorkspaces.find((workspace) => workspace.workspaceId === workspaceDirectory.currentWorkspaceId)
    ?? workspaceDirectory.workspaces.find((workspace) => workspace.workspaceId === workspaceDirectory.currentWorkspaceId)
    ?? workspaceAdmin.workspace
  const workspaceInitials = workspaceInitialsFor(currentWorkspace?.name)
  const currentRoles = workspaceAdmin.currentMembership?.groupIds.join(', ') ?? 'Invitation required'

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

  function openWorkspaceCreateDialog() {
    closeWorkspaceSwitcher()
    closeAccountMenu()
    closeNotifications()
    setWorkspaceCreateOpen(true)
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

  useEffect(() => {
    if (!latestNotificationId) {
      return
    }

    const showPreviewTimer = window.setTimeout(() => {
      setNotificationPreviewId(latestNotificationId)
    }, 0)
    const previewTimer = window.setTimeout(() => {
      setNotificationPreviewId((currentId) => currentId === latestNotificationId ? null : currentId)
    }, NOTIFICATION_PREVIEW_DURATION_MS)

    return () => {
      window.clearTimeout(showPreviewTimer)
      window.clearTimeout(previewTimer)
    }
  }, [latestNotificationId])

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
            <span className="workspace-avatar" aria-hidden="true">{workspaceInitials}</span>
            <span className="workspace-trigger-copy">
              <strong>{currentWorkspace?.name ?? t('No workspace')}</strong>
              <span>{currentWorkspace ? t('Privacy workspace') : t('Invitation required')}</span>
            </span>
            <span className="workspace-plan">{currentWorkspace?.plan ?? t('None')}</span>
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
                  <button
                    className={`workspace-option ${workspace.workspaceId === workspaceDirectory.currentWorkspaceId ? 'workspace-option-active' : ''}`}
                    key={workspace.workspaceId}
                    onClick={closeWorkspaceSwitcher}
                    type="button"
                  >
                    <span className="workspace-option-avatar" aria-hidden="true">{workspaceInitialsFor(workspace.name)}</span>
                    <span>
                      <strong>{workspace.name}</strong>
                      <small>{t(workspace.description ?? currentRoles)}</small>
                    </span>
                    <span className="workspace-plan">{workspace.plan}</span>
                    {workspace.workspaceId === workspaceDirectory.currentWorkspaceId ? <Check aria-hidden="true" size={15} /> : null}
                  </button>
                ))}
                {visibleWorkspaces.length === 0 ? <span className="workspace-no-results">{t('No workspace matches')}</span> : null}
              </div>

              {workspaceDirectory.pendingInvitations.length > 0 ? (
                <div className="workspace-invite-list" role="group" aria-label={t('Pending invitations')}>
                  {workspaceDirectory.pendingInvitations.map((invitation) => (
                    <button
                      className="workspace-invite-option"
                      key={invitation.invitationId}
                      onClick={() => {
                        void acceptWorkspaceInvitation(invitation.invitationId)
                        closeWorkspaceSwitcher()
                      }}
                      type="button"
                    >
                      <Link2 aria-hidden="true" size={16} />
                      <span>
                        <strong>{t('Accept invitation')}</strong>
                        <small>{invitation.invitePath ?? invitation.invitationId}</small>
                      </span>
                    </button>
                  ))}
                </div>
              ) : null}

              <button className="workspace-create" type="button" onClick={openWorkspaceCreateDialog}>
                <Plus aria-hidden="true" size={17} />
                <span>
                  <strong>{t('Create workspace')}</strong>
                  <small>{t('Collaborate with reviewers')}</small>
                </span>
              </button>
            </section>
          </>
        ) : null}

        <WorkspaceCreateForm onClose={() => setWorkspaceCreateOpen(false)} open={workspaceCreateOpen} />

        <label className="sidebar-search">
          <Search aria-hidden="true" size={16} />
          <span className="sr-only">{t('Quick search')}</span>
          <input aria-label={t('Quick search')} onChange={(event) => setNavQuery(event.target.value)} placeholder={t('Quick search...')} type="search" value={navQuery} />
          <kbd>⌘K</kbd>
        </label>

        <nav aria-label={t('Primary navigation')}>
          {visibleNavigation.map(({ to, label, icon: Icon, end, children }) => {
            const childNavigation = (children ?? []).filter((child) => !navQuery || t(child.label).toLowerCase().includes(navQuery.toLowerCase()) || t(label).toLowerCase().includes(navQuery.toLowerCase()))
            const expanded = childNavigation.length > 0 && (location.pathname.startsWith(to) || Boolean(navQuery))

            return (
              <div className={`nav-group ${expanded ? 'nav-group-expanded' : ''}`} key={to}>
                <NavLink
                  className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
                  end={end}
                  onClick={() => setMobileOpen(false)}
                  to={to}
                >
                  <Icon aria-hidden="true" size={18} strokeWidth={2} />
                  <span>{t(label)}</span>
                </NavLink>
                {expanded ? (
                  <div className="nav-subtree">
                    {childNavigation.map((child) => {
                      const ChildIcon = child.icon
                      return (
                        <NavLink
                          className={({ isActive }) => `nav-sublink ${isActive ? 'nav-sublink-active' : ''}`}
                          end={child.end}
                          key={child.to}
                          onClick={() => setMobileOpen(false)}
                          to={child.to}
                        >
                          {ChildIcon ? <ChildIcon aria-hidden="true" size={15} strokeWidth={2} /> : null}
                          <span>{t(child.label)}</span>
                        </NavLink>
                      )
                    })}
                  </div>
                ) : null}
              </div>
            )
          })}
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
          <nav aria-label={t('Page hierarchy')} className="topbar-title topbar-breadcrumbs" title={pageTitle}>
            {pageTitleSegments.map((segment, index) => {
              const isCurrent = index === pageTitleSegments.length - 1
              const label = t(segment.label)

              return (
                <span className="topbar-breadcrumb-item" key={`${segment.label}-${index}`}>
                  {index > 0 ? <span aria-hidden="true" className="topbar-breadcrumb-separator">/</span> : null}
                  {segment.to && !isCurrent ? (
                    <Link className="topbar-breadcrumb-link" to={segment.to}>{label}</Link>
                  ) : (
                    <span aria-current={isCurrent ? 'page' : undefined} className="topbar-breadcrumb-current">{label}</span>
                  )}
                </span>
              )
            })}
          </nav>
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
          {notificationPreview && !notificationsOpen ? (
            <section className="notification-preview">
              <Bell aria-hidden="true" size={17} />
              <span className="notification-preview-copy">
                <strong>{t('Notifications')}</strong>
                <span className="notification-preview-message">{notificationPreview.message}</span>
                <time dateTime={notificationPreview.createdAt}>{formatNotificationTime(notificationPreview.createdAt)}</time>
              </span>
              <button type="button" aria-label={t('Dismiss notification')} onClick={() => setNotificationPreviewId(null)}>
                <X aria-hidden="true" size={14} />
              </button>
            </section>
          ) : null}
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
          {workspaceDirectory.workspaceRequired && !workspaceDirectory.currentWorkspaceId && !isWorkspaceInviteRoute ? <WorkspaceAccessNotice /> : <Outlet />}
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
