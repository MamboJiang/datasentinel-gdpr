import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { AlertCircle, ArrowRight, Inbox } from 'lucide-react'
import { Link } from 'react-router-dom'
import { humanize } from './formatters'

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string
  title: string
  description: string
  actions?: ReactNode
}) {
  return (
    <header className="page-header">
      <div>
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h1>{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </header>
  )
}

export function SectionHeader({
  title,
  description,
  action,
}: {
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="section-header">
      <div>
        <h2>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
      {action}
    </div>
  )
}

export function Button({
  children,
  icon: Icon,
  variant = 'primary',
  type = 'button',
  onClick,
  disabled = false,
}: {
  children: ReactNode
  icon?: LucideIcon
  variant?: 'primary' | 'secondary' | 'ghost'
  type?: 'button' | 'submit'
  onClick?: () => void
  disabled?: boolean
}) {
  return (
    <button className={`button button-${variant}`} disabled={disabled} type={type} onClick={onClick}>
      {Icon ? <Icon aria-hidden="true" size={17} strokeWidth={2} /> : null}
      {children}
    </button>
  )
}

export function StatusBadge({ value }: { value?: string | null }) {
  const normalized = value || 'unknown'
  const tone =
    {
      completed: 'positive',
      connected: 'positive',
      retained: 'positive',
      running: 'info',
      assigned: 'info',
      under_review: 'info',
      mocked: 'neutral',
      open: 'neutral',
      delete_candidate: 'warning',
      overdue: 'warning',
      escalated: 'critical',
      failed: 'critical',
      false_positive: 'neutral',
    }[normalized] ?? 'neutral'

  return <span className={`badge badge-${tone}`}>{humanize(normalized)}</span>
}

export function RiskBadge({ riskLevel, score }: { riskLevel?: string; score?: number }) {
  const normalized = riskLevel || 'unknown'
  const knownTone = ['high', 'medium', 'low'].includes(normalized) ? normalized : 'unknown'

  return (
    <span className={`risk-badge risk-${knownTone}`}>
      <span className="risk-dot" aria-hidden="true" />
      {humanize(normalized)}
      {typeof score === 'number' ? <strong>{score}</strong> : null}
    </span>
  )
}

export function MetricCard({
  label,
  value,
  helper,
  icon: Icon,
  tone = 'blue',
}: {
  label: string
  value: string
  helper: string
  icon: LucideIcon
  tone?: 'blue' | 'green' | 'amber' | 'red'
}) {
  return (
    <article className="metric-card">
      <div className={`metric-icon metric-icon-${tone}`}>
        <Icon aria-hidden="true" size={18} strokeWidth={2} />
      </div>
      <p>{label}</p>
      <strong>{value}</strong>
      <span>{helper}</span>
    </article>
  )
}

export function ProgressBar({ value }: { value: number }) {
  const percent = Math.max(0, Math.min(100, Math.round(value * 100)))

  return (
    <div className="progress-track" aria-label={`${percent}% complete`} role="progressbar" aria-valuenow={percent}>
      <span style={{ width: `${percent}%` }} />
    </div>
  )
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="empty-state">
      <Inbox aria-hidden="true" size={24} />
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  )
}

export function PartialWarning({ warnings }: { warnings: string[] }) {
  return (
    <div className="partial-warning" role="status">
      <AlertCircle aria-hidden="true" size={17} />
      <span>Partial data is available. {warnings.join(' ') || 'Some values may still be processing.'}</span>
    </div>
  )
}

export function TextLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link className="text-link" to={to}>
      {children}
      <ArrowRight aria-hidden="true" size={15} />
    </Link>
  )
}
