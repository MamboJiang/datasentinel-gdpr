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
  ShieldCheck,
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
  const { toast, clearToast } = useData()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_DEFAULT_WIDTH)
  const [workspaceOpen, setWorkspaceOpen] = useState(false)
  const [workspaceQuery, setWorkspaceQuery] = useState('')
  const [accountOpen, setAccountOpen] = useState(false)
  const [navQuery, setNavQuery] = useState('')
  const pageTitle = getPageTitle(location.pathname)
  const visibleWorkspaces = workspaces.filter(({ name }) => name.toLowerCase().includes(workspaceQuery.toLowerCase()))
  const visibleNavigation = navigation.filter(({ label }) => label.toLowerCase().includes(navQuery.toLowerCase()))
  const activeSidebarWidth = sidebarCollapsed ? SIDEBAR_COLLAPSED_WIDTH : sidebarWidth
  const shellStyle = { '--sidebar-width': `${activeSidebarWidth}px` } as CSSProperties

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
              setWorkspaceOpen(true)
            }}
            type="button"
          >
            <span className="workspace-avatar" aria-hidden="true">DS</span>
            <span className="workspace-trigger-copy">
              <strong>{workspaceSimulation.name}</strong>
              <span>Privacy workspace</span>
            </span>
            <span className="workspace-plan">{workspaceSimulation.plan}</span>
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

        <AccountMenu
          accountOpen={accountOpen}
          onClose={closeAccountMenu}
          onCloseWorkspace={closeWorkspaceSwitcher}
          onToggle={() => setAccountOpen((isOpen) => !isOpen)}
          onToggleSidebar={() => {
            closeWorkspaceSwitcher()
            closeAccountMenu()
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
