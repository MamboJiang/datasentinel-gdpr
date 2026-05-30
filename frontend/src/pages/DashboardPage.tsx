import {
  Activity,
  AlertTriangle,
  Clock3,
  Database,
  Files,
  FolderSearch2,
  Gauge,
  Play,
  RotateCw,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useData } from '../data/useData'
import { formatDate, humanize } from '../components/formatters'
import {
  Button,
  MetricCard,
  PageHeader,
  PartialWarning,
  ProgressBar,
  RiskBadge,
  SectionHeader,
  StatusBadge,
  TextLink,
} from '../components/ui'

export function DashboardPage() {
  const { metrics, scan, findings, auditEvents, meta, startScan } = useData()
  const highRisk = findings.filter((finding) => finding.riskLevel === 'high').slice(0, 3)
  const sourceRows = Object.entries(metrics.findingsBySource ?? {})
  const sourceMax = Math.max(...sourceRows.map(([, count]) => count), 1)

  return (
    <>
      {meta.partial ? <PartialWarning warnings={meta.warnings} /> : null}
      <PageHeader
        eyebrow="Privacy operations"
        title="Data discovery overview"
        description="Monitor GDPR-relevant findings, route accountable review, and keep every decision audit-ready."
        actions={
          <Button icon={Play} onClick={() => startScan('full')}>
            Start full scan
          </Button>
        }
      />

      <section className="metrics-grid" aria-label="Key metrics">
        <MetricCard icon={Files} label="Scanned files" value={metrics.totalScannedFiles.toString()} helper="Across connected sources" />
        <MetricCard icon={FolderSearch2} label="Flagged files" value={metrics.flaggedFiles.toString()} helper="Require contextual review" tone="amber" />
        <MetricCard icon={AlertTriangle} label="High-risk findings" value={(metrics.highRiskFindings ?? 0).toString()} helper="Prioritize for review" tone="red" />
        <MetricCard icon={Clock3} label="Review backlog" value={metrics.openReviewBacklog.toString()} helper="Open owner decisions" tone="amber" />
      </section>

      <div className="dashboard-grid">
        <section className="panel scan-panel">
          <SectionHeader
            title="Latest scan activity"
            description="Controlled sample repository"
            action={<StatusBadge value={scan.status} />}
          />
          <div className="scan-hero">
            <div>
              <span className="scan-type">{humanize(scan.scanType)} scan</span>
              <strong>{Math.round(scan.progress * 100)}%</strong>
              <small>{scan.scannedFiles ?? 0} of {scan.totalFiles ?? 0} files processed</small>
            </div>
            <div className="scan-hero-icon">
              <RotateCw aria-hidden="true" size={24} />
            </div>
          </div>
          <ProgressBar value={scan.progress} />
          <div className="scan-stats">
            <div><span>Flagged</span><strong>{scan.flaggedFiles ?? 0}</strong></div>
            <div><span>Duration</span><strong>{metrics.lastScanTimeSeconds ?? '—'}s</strong></div>
            <div><span>Throughput</span><strong>{scan.throughputFilesPerSecond ?? '—'}/s</strong></div>
          </div>
          <div className="panel-actions">
            <Button icon={RotateCw} variant="secondary" onClick={() => startScan('delta')}>Run delta scan</Button>
          </div>
        </section>

        <section className="panel">
          <SectionHeader title="Findings by source" description="Flagged files grouped by origin" />
          <div className="source-chart">
            {sourceRows.map(([source, count]) => (
              <div className="chart-row" key={source}>
                <div><span>{humanize(source)}</span><strong>{count}</strong></div>
                <div className="chart-track"><span style={{ width: `${(count / sourceMax) * 100}%` }} /></div>
              </div>
            ))}
          </div>
          <TextLink to="/sources">Manage sources</TextLink>
        </section>
      </div>

      <div className="dashboard-grid lower-grid">
        <section className="panel">
          <SectionHeader title="Priority findings" description="High-risk files waiting for accountable review" action={<TextLink to="/findings">View all</TextLink>} />
          <div className="compact-list">
            {highRisk.map((finding) => (
              <Link className="finding-list-item" key={finding.findingId} to={`/findings/${finding.findingId}`}>
                <div className="file-avatar"><Database aria-hidden="true" size={16} /></div>
                <div className="list-item-main">
                  <strong>{finding.fileName}</strong>
                  <span>{finding.contextCategory ? humanize(finding.contextCategory) : 'Unclassified context'}</span>
                </div>
                <RiskBadge riskLevel={finding.riskLevel} score={finding.riskScore} />
              </Link>
            ))}
          </div>
        </section>

        <section className="panel">
          <SectionHeader title="Recent audit activity" description="Latest visible workflow events" action={<TextLink to="/audit">View trail</TextLink>} />
          <div className="timeline compact-timeline">
            {auditEvents.slice(0, 3).map((event) => (
              <div className="timeline-item" key={event.auditEventId}>
                <div className="timeline-marker"><Activity aria-hidden="true" size={14} /></div>
                <div>
                  <strong>{humanize(event.eventType)}</strong>
                  <p>{event.summary}</p>
                  <span>{formatDate(event.occurredAt)}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="trust-strip">
        <Gauge aria-hidden="true" size={18} />
        <div>
          <strong>Evaluation is visible by design</strong>
          <span>Precision, recall, reproducibility, throughput, and resource intensity remain first-class product signals.</span>
        </div>
        <TextLink to="/evaluation">Open evaluation</TextLink>
      </section>
    </>
  )
}
