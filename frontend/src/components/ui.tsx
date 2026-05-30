import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { AlertCircle, ArrowRight, Inbox } from 'lucide-react'
import { Link } from 'react-router-dom'
import { humanize } from './formatters'
import { useI18n } from '../i18n'

function translatedNode(node: ReactNode, t: (text: string) => string) {
  return typeof node === 'string' ? t(node) : node
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string
  title: string
  description?: string
  actions?: ReactNode
}) {
  const { t } = useI18n()

  return (
    <header className="page-header">
      <div>
        {eyebrow ? <p className="eyebrow">{t(eyebrow)}</p> : null}
        <h1>{t(title)}</h1>
        {description ? <p className="page-description">{t(description)}</p> : null}
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
  const { t } = useI18n()

  return (
    <div className="section-header">
      <div>
        <h2>{t(title)}</h2>
        {description ? <p>{t(description)}</p> : null}
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
  const { t } = useI18n()

  return (
    <button className={`button button-${variant}`} disabled={disabled} type={type} onClick={onClick}>
      {Icon ? <Icon aria-hidden="true" size={17} strokeWidth={2} /> : null}
      {translatedNode(children, t)}
    </button>
  )
}

export function StatusBadge({ value }: { value?: string | null }) {
  const { t } = useI18n()
  const normalized = value || 'unknown'
  const tone =
    {
      completed: 'positive',
      connected: 'positive',
      computed: 'positive',
      mock_ready: 'positive',
      retained: 'positive',
      running: 'info',
      assigned: 'info',
      under_review: 'info',
      mocked: 'neutral',
      open: 'neutral',
      pending: 'neutral',
      delete_candidate: 'warning',
      overdue: 'warning',
      warning: 'warning',
      escalated: 'critical',
      failed: 'critical',
      false_positive: 'neutral',
    }[normalized] ?? 'neutral'

  return <span className={`badge badge-${tone}`}>{t(humanize(normalized))}</span>
}

export function RiskBadge({ riskLevel, score }: { riskLevel?: string; score?: number }) {
  const { t } = useI18n()
  const normalized = riskLevel || 'unknown'
  const knownTone = ['high', 'medium', 'low'].includes(normalized) ? normalized : 'unknown'

  return (
    <span className={`risk-badge risk-${knownTone}`}>
      <span className="risk-dot" aria-hidden="true" />
      {t(humanize(normalized))}
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
  helper?: string
  icon: LucideIcon
  tone?: 'blue' | 'green' | 'amber' | 'red'
}) {
  const { t } = useI18n()

  return (
    <article className="metric-card">
      <div className={`metric-icon metric-icon-${tone}`}>
        <Icon aria-hidden="true" size={18} strokeWidth={2} />
      </div>
      <p>{t(label)}</p>
      <strong>{value}</strong>
      {helper ? <span>{t(helper)}</span> : null}
    </article>
  )
}

export function ProgressBar({ value }: { value: number }) {
  const { t } = useI18n()
  const percent = Math.max(0, Math.min(100, Math.round(value * 100)))

  return (
    <div className="progress-track" aria-label={t('{{percent}}% complete', { percent })} role="progressbar" aria-valuenow={percent}>
      <span style={{ width: `${percent}%` }} />
    </div>
  )
}

export function EmptyState({ title, description }: { title: string; description?: string }) {
  const { t } = useI18n()

  return (
    <div className="empty-state">
      <Inbox aria-hidden="true" size={24} />
      <h3>{t(title)}</h3>
      {description ? <p>{t(description)}</p> : null}
    </div>
  )
}

export function PartialWarning({ warnings }: { warnings: string[] }) {
  const { t } = useI18n()

  return (
    <div className="partial-warning" role="status">
      <AlertCircle aria-hidden="true" size={17} />
      <span>{t('Partial data is available.')} {warnings.join(' ') || t('Some values may still be processing.')}</span>
    </div>
  )
}

export function TextLink({ to, children }: { to: string; children: ReactNode }) {
  const { t } = useI18n()

  return (
    <Link className="text-link" to={to}>
      {translatedNode(children, t)}
      <ArrowRight aria-hidden="true" size={15} />
    </Link>
  )
}
