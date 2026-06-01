import {
  Activity,
  Bell,
  Check,
  ChevronRight,
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
  requiredAny?: string[]
  to: string
}

type NavigationChild = {
  end?: boolean
  icon?: LucideIcon
  label: string
  requiredAny?: string[]
  to: string
}

type PageTitleSegment = {
  label: string
  to?: string
}

const navigation: NavigationItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, end: true, requiredAny: ['view_workspace_metrics', 'view_workspace_admin', 'view_assigned_findings', 'view_owned_sources', 'view_workspace_audit', 'view_governance'] },
  {
    to: '/workspace/admin',
    label: 'Workspace admin',
    icon: ShieldCheck,
    requiredAny: ['view_workspace_admin'],
    children: [
      { to: '/workspace/admin/members', label: 'Members', icon: UsersRound, requiredAny: ['view_workspace_admin'] },
      { to: '/workspace/admin/groups', label: 'Group controls', icon: ShieldCheck, requiredAny: ['view_workspace_admin'] },
    ],
  },
  { to: '/sources', label: 'Sources', icon: Database, requiredAny: ['view_owned_sources', 'view_workspace_admin'] },
  { to: '/findings', label: 'Findings', icon: FileSearch, requiredAny: ['view_assigned_findings'] },
  { to: '/audit', label: 'Audit trail', icon: Activity, requiredAny: ['view_workspace_audit', 'view_workspace_admin'] },
  { to: '/evaluation', label: 'Evaluation', icon: Gauge, requiredAny: ['view_workspace_metrics', 'view_workspace_admin'] },
  { to: '/governance', label: 'Governance', icon: Settings2, requiredAny: ['view_governance', 'view_workspace_admin'] },
]

function getPageTitleSegments(pathname: string): PageTitleSegment[] {
  if (pathname.startsWith('/workspace/admin/members')) {
    return [
      { label: 'Workspace admin', to: '/workspace/admin' },
      { label: 'Members' },
    ]
  }

  if (pathname.startsWith('/workspace/admin/groups')) {
    return [
      { label: 'Workspace admin', to: '/workspace/admin' },
      { label: 'Group controls' },
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
    { label: navigation.find(({ to, end }) => (end ? pathname === to : pathname.startsWith(to)))?.label ?? utilityPageTitles[pathname] ?? 'lawdit' },
  ]
}

function workspaceInitialsFor(name: string | undefined) {
  return name
    ? name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
    : 'WS'
}

function membershipGroupLabel(groupId: string, groups: Array<{ groupId: string; name: string }>) {
  return groups.find((group) => group.groupId === groupId)?.name ?? groupId
}

export function AppShell() {
  const { t } = useI18n()
  const {
    acceptWorkspaceInvitation,
    switchWorkspace,
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
  const allowedWorkspaceActions = new Set(workspaceAdmin.permissionBoundary.allowedActions ?? [])
  const visibleNavigation = navigation.filter((item) => {
    if (!canAccessNavigationItem(item, allowedWorkspaceActions)) {
      return false
    }

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
  const currentGroupLabels = workspaceAdmin.currentMembership?.groupIds.map((groupId) => membershipGroupLabel(groupId, workspaceAdmin.groups)) ?? []
  const currentGroupsLabel = currentGroupLabels.length > 0 ? currentGroupLabels.join(' · ') : t('Invitation required')
  const currentGroupsPillLabel = currentGroupLabels.length > 1 ? `${currentGroupLabels[0]} +${currentGroupLabels.length - 1}` : currentGroupLabels[0]
  const currentRoles = workspaceAdmin.currentMembership?.groupIds.join(', ') ?? 'Invitation required'
  const routeNavigation = navigationEntryForPath(location.pathname)
  const routeDenied = Boolean(
    routeNavigation
    && !isWorkspaceInviteRoute
    && !canAccessNavigationEntry(routeNavigation, allowedWorkspaceActions),
  )

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

  async function selectWorkspace(workspaceId: string) {
    const switched = await switchWorkspace(workspaceId)
    if (switched) {
      closeWorkspaceSwitcher()
    }
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
              <span>{currentWorkspace ? (currentWorkspace.description ?? t('Privacy workspace')) : t('Invitation required')}</span>
            </span>
            {currentWorkspace && currentGroupsPillLabel ? <span className="workspace-plan" title={currentGroupsLabel}>{currentGroupsPillLabel}</span> : null}
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
                    onClick={() => {
                      void selectWorkspace(workspace.workspaceId)
                    }}
                    type="button"
                  >
                    <span className="workspace-option-avatar" aria-hidden="true">{workspaceInitialsFor(workspace.name)}</span>
                    <span>
                      <strong>{workspace.name}</strong>
                      <small>{workspace.description ?? t(currentRoles)}</small>
                    </span>
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
            const childNavigation = (children ?? [])
              .filter((child) => canAccessNavigationEntry(child, allowedWorkspaceActions))
              .filter((child) => !navQuery || t(child.label).toLowerCase().includes(navQuery.toLowerCase()) || t(label).toLowerCase().includes(navQuery.toLowerCase()))
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
                  {children?.length ? (
                    <ChevronRight aria-hidden="true" className="nav-expand-icon" size={15} strokeWidth={2} />
                  ) : null}
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
          {workspaceDirectory.workspaceRequired && !workspaceDirectory.currentWorkspaceId && !isWorkspaceInviteRoute ? (
            <WorkspaceAccessNotice />
          ) : routeDenied ? (
            <PermissionDeniedNotice label={routeNavigation?.label ?? 'This page'} />
          ) : (
            <Outlet />
          )}
        </main>
      </div>
    </div>
  )
}

function canAccessNavigationItem(item: NavigationItem, allowedActions: Set<string>) {
  return canAccessNavigationEntry(item, allowedActions)
}

function canAccessNavigationEntry(item: NavigationItem | NavigationChild, allowedActions: Set<string>) {
  return !item.requiredAny || item.requiredAny.some((action) => allowedActions.has(action))
}

function navigationEntryForPath(pathname: string): NavigationItem | NavigationChild | undefined {
  for (const item of navigation) {
    const child = item.children?.find((candidate) => routeMatches(candidate, pathname))
    if (child) {
      return child
    }

    if (routeMatches(item, pathname)) {
      return item
    }
  }

  return undefined
}

function routeMatches(item: NavigationItem | NavigationChild, pathname: string) {
  return item.end ? pathname === item.to : pathname === item.to || pathname.startsWith(`${item.to}/`)
}

function PermissionDeniedNotice({ label }: { label: string }) {
  return (
    <section className="route-denied">
      <p className="eyebrow">Permission boundary</p>
      <h1>{label} access denied</h1>
      <p>Your current Workspace groups do not include permission to open this page.</p>
    </section>
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
