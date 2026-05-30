import {
  Activity,
  Bell,
  Database,
  FileSearch,
  Gauge,
  LayoutDashboard,
  Menu,
  ScanSearch,
  Search,
  Settings2,
  ShieldCheck,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useData } from '../data/useData'
import { humanize } from './formatters'
import { StatusBadge } from './ui'

const navigation = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/sources', label: 'Sources', icon: Database },
  { to: '/findings', label: 'Findings', icon: FileSearch },
  { to: '/audit', label: 'Audit trail', icon: Activity },
  { to: '/evaluation', label: 'Evaluation', icon: Gauge },
  { to: '/governance', label: 'Governance', icon: Settings2 },
]

export function AppShell() {
  const { scan, toast, clearToast, meta } = useData()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [navQuery, setNavQuery] = useState('')
  const visibleNavigation = navigation.filter(({ label }) => label.toLowerCase().includes(navQuery.toLowerCase()))

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <div className="brand-mark">
            <ShieldCheck aria-hidden="true" size={21} />
          </div>
          <div>
            <strong>DataSentinel</strong>
            <span>Privacy control center</span>
          </div>
          <button className="sidebar-close" type="button" aria-label="Close navigation" onClick={() => setMobileOpen(false)}>
            <X aria-hidden="true" size={18} />
          </button>
        </div>

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

        <div className="sidebar-footer">
          <ScanSearch aria-hidden="true" size={18} />
          <div>
            <strong>Contract-backed mode</strong>
            <span>API v{meta.contractVersion}</span>
          </div>
        </div>
      </aside>

      <div className="content-shell">
        <header className="topbar">
          <button className="mobile-menu" type="button" aria-label="Open navigation" onClick={() => setMobileOpen(true)}>
            <Menu aria-hidden="true" size={20} />
          </button>
          <div className="topbar-mode">
            <span className="mode-dot" aria-hidden="true" />
            Contract-backed mock mode
          </div>
          <div className="topbar-actions">
            <div className="scan-summary">
              <span>Latest scan</span>
              <StatusBadge value={scan.status} />
            </div>
            <button className="icon-button" type="button" aria-label="Notifications">
              <Bell aria-hidden="true" size={18} />
            </button>
            <div className="profile">
              <span>AS</span>
              <div>
                <strong>Anna Schneider</strong>
                <small>{humanize('master_of_data')}</small>
              </div>
            </div>
          </div>
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
