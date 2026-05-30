import {
  Activity,
  Bell,
  BookOpen,
  Check,
  ChevronsUpDown,
  Database,
  FileSearch,
  Gauge,
  Home,
  LayoutDashboard,
  LifeBuoy,
  LogOut,
  Menu,
  Monitor,
  Moon,
  MoreHorizontal,
  PanelLeftClose,
  PanelLeftOpen,
  PencilLine,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  SmilePlus,
  Sun,
  X,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useData } from '../data/useData'

const accountName = 'Anna Schneider'
const accountEmail = 'anna.schneider@example.com'
const workspaceName = 'DataSentinel GDPR'

const workspaces = [
  {
    id: 'datasentinel-gdpr',
    name: workspaceName,
    description: 'Privacy operations workspace',
    plan: 'Demo',
  },
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

const accountLinks = [
  { label: 'Feedback', icon: SmilePlus },
  { label: 'Home Page', icon: Home },
  { label: 'Changelog', icon: PencilLine },
  { label: 'Help', icon: LifeBuoy },
  { label: 'Docs', icon: BookOpen },
  { label: 'Log Out', icon: LogOut },
]

function getPageTitle(pathname: string) {
  if (pathname.startsWith('/findings/')) {
    return 'Finding Detail'
  }

  return navigation.find(({ to, end }) => (end ? pathname === to : pathname.startsWith(to)))?.label ?? 'DataSentinel'
}

export function AppShell() {
  const { toast, clearToast } = useData()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [workspaceOpen, setWorkspaceOpen] = useState(false)
  const [workspaceQuery, setWorkspaceQuery] = useState('')
  const [accountOpen, setAccountOpen] = useState(false)
  const [navQuery, setNavQuery] = useState('')
  const pageTitle = getPageTitle(location.pathname)
  const visibleWorkspaces = workspaces.filter(({ name }) => name.toLowerCase().includes(workspaceQuery.toLowerCase()))
  const visibleNavigation = navigation.filter(({ label }) => label.toLowerCase().includes(navQuery.toLowerCase()))

  function closeWorkspaceSwitcher() {
    setWorkspaceOpen(false)
    setWorkspaceQuery('')
  }

  function closeAccountMenu() {
    setAccountOpen(false)
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

  return (
    <div className="app-shell">
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
              setWorkspaceOpen(true)
            }}
            type="button"
          >
            <span className="workspace-avatar" aria-hidden="true">DS</span>
            <span className="workspace-trigger-copy">
              <strong>{workspaceName}</strong>
              <span>Privacy workspace</span>
            </span>
            <span className="workspace-plan">Demo</span>
            <ChevronsUpDown aria-hidden="true" size={16} />
          </button>
          <button className="sidebar-close" type="button" aria-label="Close navigation" onClick={() => setMobileOpen(false)}>
            <X aria-hidden="true" size={18} />
          </button>
        </div>

        {workspaceOpen ? (
          <>
            <button className="workspace-backdrop" type="button" aria-label="Close workspace switcher" onClick={closeWorkspaceSwitcher} />
            <section className="workspace-popover" id="workspace-switcher-panel" role="dialog" aria-label="Workspace switcher">
              <label className="workspace-search">
                <Search aria-hidden="true" size={15} />
                <span className="sr-only">Find workspace</span>
                <input
                  aria-label="Find workspace"
                  autoFocus
                  onChange={(event) => setWorkspaceQuery(event.target.value)}
                  placeholder="Find workspace..."
                  type="search"
                  value={workspaceQuery}
                />
                <kbd>Esc</kbd>
              </label>

              <div className="workspace-list" role="group" aria-label="Available workspaces">
                {visibleWorkspaces.map((workspace) => (
                  <button className="workspace-option workspace-option-active" key={workspace.id} onClick={closeWorkspaceSwitcher} type="button">
                    <span className="workspace-option-avatar" aria-hidden="true">DS</span>
                    <span>
                      <strong>{workspace.name}</strong>
                      <small>{workspace.description}</small>
                    </span>
                    <span className="workspace-plan">{workspace.plan}</span>
                    <Check aria-hidden="true" size={15} />
                  </button>
                ))}
                {visibleWorkspaces.length === 0 ? <span className="workspace-no-results">No workspace matches</span> : null}
              </div>

              <button className="workspace-create" type="button" onClick={closeWorkspaceSwitcher}>
                <Plus aria-hidden="true" size={17} />
                <span>
                  <strong>Create workspace</strong>
                  <small>Collaborate with reviewers</small>
                </span>
              </button>
            </section>
          </>
        ) : null}

        <label className="sidebar-search">
          <Search aria-hidden="true" size={16} />
          <span className="sr-only">Quick search</span>
          <input aria-label="Quick search" onChange={(event) => setNavQuery(event.target.value)} placeholder="Quick search..." type="search" value={navQuery} />
          <kbd>⌘K</kbd>
        </label>

        <nav aria-label="Primary navigation">
          {visibleNavigation.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
              end={end}
              key={to}
              onClick={() => setMobileOpen(false)}
              to={to}
            >
              <Icon aria-hidden="true" size={18} strokeWidth={2} />
              <span>{label}</span>
            </NavLink>
          ))}
          {visibleNavigation.length === 0 ? <span className="nav-empty">No navigation matches</span> : null}
        </nav>

        <div className="account-dock">
          {accountOpen ? (
            <>
              <button className="account-backdrop" type="button" aria-label="Close account menu" onClick={closeAccountMenu} />
              <section className="account-popover" id="account-menu-panel" role="dialog" aria-label="Account menu">
                <div className="account-popover-header">
                  <div>
                    <strong>{accountName}</strong>
                    <span>{accountEmail}</span>
                  </div>
                  <button className="account-settings" type="button" aria-label="Account settings">
                    <Settings2 aria-hidden="true" size={20} />
                  </button>
                </div>

                <div className="account-menu-list">
                  <button className="account-menu-row" type="button">
                    <span>Theme</span>
                    <span className="theme-control" aria-label="Theme options">
                      <Monitor aria-hidden="true" size={18} />
                      <Sun aria-hidden="true" size={18} />
                      <Moon aria-hidden="true" size={18} />
                    </span>
                  </button>
                  {accountLinks.map(({ label, icon: Icon }) => (
                    <button className="account-menu-row" key={label} type="button">
                      <span>{label}</span>
                      <Icon aria-hidden="true" size={19} />
                    </button>
                  ))}
                </div>

                <button className="upgrade-button" type="button">Upgrade to Pro</button>

                <div className="platform-status">
                  <span>Platform Status</span>
                  <strong>All systems normal.</strong>
                  <i aria-hidden="true" />
                </div>
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
                closeWorkspaceSwitcher()
                setAccountOpen((isOpen) => !isOpen)
              }}
              type="button"
            >
              <span className="account-avatar" aria-hidden="true">AS</span>
              <span>
                <strong>{accountName}</strong>
                <small>{accountEmail}</small>
              </span>
            </button>
            <button
              className="account-icon-button"
              type="button"
              aria-label="Open account menu"
              onClick={() => {
                closeWorkspaceSwitcher()
                setAccountOpen((isOpen) => !isOpen)
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
                closeWorkspaceSwitcher()
                closeAccountMenu()
                setSidebarCollapsed((isCollapsed) => !isCollapsed)
              }}
            >
              {sidebarCollapsed ? <PanelLeftOpen aria-hidden="true" size={18} /> : <PanelLeftClose aria-hidden="true" size={18} />}
            </button>
          </div>
        </div>
      </aside>

      <div className={`content-shell ${sidebarCollapsed ? 'content-shell-collapsed' : ''}`}>
        <header className="topbar">
          <button className="mobile-menu" type="button" aria-label="Open navigation" onClick={() => setMobileOpen(true)}>
            <Menu aria-hidden="true" size={20} />
          </button>
          <strong className="topbar-title">{pageTitle}</strong>
          <button className="topbar-notification" type="button" aria-label="Notifications">
            <Bell aria-hidden="true" size={18} />
            <span aria-hidden="true" />
          </button>
        </header>

        <main className="main-content">
          <Outlet />
        </main>
      </div>

      {toast ? (
        <div className="toast" role="status">
          <ShieldCheck aria-hidden="true" size={18} />
          <span>{toast}</span>
          <button type="button" aria-label="Dismiss notification" onClick={clearToast}>
            <X aria-hidden="true" size={16} />
          </button>
        </div>
      ) : null}
    </div>
  )
}
