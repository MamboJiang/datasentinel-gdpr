import {
  Activity,
  AlertTriangle,
  Clock3,
  Database,
  Files,
  Gauge,
  Play,
  RotateCw,
  ShieldCheck,
  UserCheck,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useData } from '../data/useData'
import { getDefaultFullScanSource, isSourceScanReady } from '../data/scanWorkflow'
import { formatBytes, formatDate, humanize } from '../components/formatters'
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
  const { metrics, scan, findings, auditEvents, meta, sources, governanceConfig, startScan } = useData()
  const highRisk = findings.filter((finding) => finding.riskLevel === 'high').slice(0, 3)
  const defaultFullScanSource = getDefaultFullScanSource(sources, governanceConfig)
  const currentScanSource = sources.find((source) => source.sourceId === scan.sourceId)
  const scanIsRunning = scan.status === 'running'
  const canRunDelta = Boolean(currentScanSource && isSourceScanReady(currentScanSource, governanceConfig) && !scanIsRunning && scan.status === 'completed')
  const inventory = scan.fileInventory
  const extraction = scan.contentExtraction
  const contextRisk = scan.contextRisk
  const ownerAssignment = scan.ownerAssignment
  const findingAssembly = scan.findingAssembly
  const reviewSupport = scan.reviewSupport
  const auditRecording = scan.auditRecording
  const pipelineStages = scan.pipelineStages ?? []
  const processedFiles = scan.scannedFiles ?? 0
  const totalFiles = scan.totalFiles ?? 0
  const scanCoverage = totalFiles > 0 ? `${processedFiles}/${totalFiles}` : processedFiles.toString()
  const humanReviewCount = contextRisk?.humanReviewRequiredFindings ?? metrics.humanReviewRequiredFindings ?? metrics.openReviewBacklog
  const highRiskCount = contextRisk?.highRiskFindings ?? metrics.highRiskFindings ?? 0
  const retentionReviewCount = contextRisk?.retentionReviewFiles ?? metrics.retentionOverdueFiles ?? 0
  const ownerRoutedCount = ownerAssignment?.assignedFindings ?? metrics.assignedFindings ?? metrics.ownerRoutedFindings ?? 0
  const unownedCount = ownerAssignment?.unownedFindings ?? 0
  const scanTypeLabel = scan.scanType === 'delta' ? 'Changed files scan' : 'All files scan'

  return (
    <>
      {meta.partial ? <PartialWarning warnings={meta.warnings} /> : null}
      <PageHeader
        eyebrow="Privacy operations"
        title="Data discovery overview"
        actions={
          <Button
            disabled={!defaultFullScanSource || scanIsRunning}
            icon={Play}
            onClick={() => defaultFullScanSource ? startScan({ scanType: 'full', sourceId: defaultFullScanSource.sourceId }) : undefined}
          >
            Start full scan
          </Button>
        }
      />

      <section className="metrics-grid" aria-label="Key metrics">
        <MetricCard icon={Gauge} label="Scan coverage" value={scanCoverage} helper={`${formatBytes(scan.totalBytes)} processed`} />
        <MetricCard icon={UserCheck} label="Needs review" value={humanReviewCount.toString()} helper={`${metrics.openReviewBacklog} open owner decisions`} tone="amber" />
        <MetricCard icon={AlertTriangle} label="High-risk queue" value={highRiskCount.toString()} helper={`${retentionReviewCount} retention reviews`} tone="red" />
        <MetricCard icon={ShieldCheck} label="Owner routed" value={ownerRoutedCount.toString()} helper={`${unownedCount} unowned findings`} tone="green" />
      </section>

      <div className="dashboard-grid dashboard-overview-grid">
        <section className="panel scan-panel dashboard-primary-panel">
          <SectionHeader
            title="Latest scan"
            action={<StatusBadge value={scan.status} />}
          />
          <div className="scan-summary-row">
            <div className="scan-hero">
              <div>
                <span className="scan-type">{scanTypeLabel}</span>
                <strong>{Math.round(scan.progress * 100)}%</strong>
                <small>{processedFiles} of {totalFiles} files processed</small>
              </div>
            </div>
            <div className="scan-facts" aria-label="Scan facts">
              <div><span>Flagged</span><strong>{scan.flaggedFiles ?? 0}</strong></div>
              <div><span>Duration</span><strong>{metrics.lastScanTimeSeconds ?? '—'}s</strong></div>
              <div><span>Throughput</span><strong>{scan.throughputFilesPerSecond ?? '—'}/s</strong></div>
              <div><span>Warnings</span><strong>{extraction?.warningFiles ?? 0}</strong></div>
            </div>
          </div>
          <ProgressBar value={scan.progress} />
          <div className="scan-footer">
            <div className="scan-boundary-note">
              <ShieldCheck aria-hidden="true" size={17} />
              <span>{extraction?.rawContentExposed ? 'Raw content boundary needs review' : 'No raw source content exposed'}</span>
            </div>
            <Button
              disabled={!canRunDelta}
              icon={RotateCw}
              variant="secondary"
              onClick={() => currentScanSource ? startScan({ scanType: 'delta', sourceId: currentScanSource.sourceId }) : undefined}
            >
              Scan changed files
            </Button>
          </div>
        </section>

        <section className="panel review-focus-panel">
          <SectionHeader title="Review focus" action={<TextLink to="/findings">Open findings</TextLink>} />
          <div className="review-focus-list">
            <div className="review-focus-row">
              <AlertTriangle aria-hidden="true" size={17} />
              <div>
                <strong>{highRiskCount} high-risk findings</strong>
              </div>
            </div>
            <div className="review-focus-row">
              <Clock3 aria-hidden="true" size={17} />
              <div>
                <strong>{metrics.openReviewBacklog} open owner decisions</strong>
              </div>
            </div>
            <div className="review-focus-row">
              <ShieldCheck aria-hidden="true" size={17} />
              <div>
                <strong>{metrics.reviewDecisionCount ?? 0} review decisions recorded</strong>
                <span>{metrics.retainedDecisions ?? 0} retained · {metrics.deletionCandidateDecisions ?? 0} deletion candidates · {metrics.escalatedDecisions ?? 0} escalated</span>
              </div>
            </div>
            <div className="review-focus-row">
              <UserCheck aria-hidden="true" size={17} />
              <div>
                <strong>{ownerAssignment?.escalationAssignments ?? metrics.escalationAssignments ?? 0} escalation routes</strong>
              </div>
            </div>
          </div>
        </section>
      </div>

      <section className="panel pipeline-panel">
        <SectionHeader title="Pipeline summary" />
        <div className="pipeline-list">
          {pipelineStages.map((stage) => (
            <div className="pipeline-row" key={stage.stage}>
              <div className="pipeline-main">
                <strong>{humanize(stage.stage)}</strong>
                <span>
                  {typeof stage.processedFiles === 'number'
                    ? `${stage.processedFiles}${typeof stage.totalFiles === 'number' ? ` of ${stage.totalFiles}` : ''} processed`
                    : 'Ready'}
                </span>
              </div>
              <div className="pipeline-meta">
                {stage.warnings?.length ? <span>{stage.warnings.length} warning{stage.warnings.length === 1 ? '' : 's'}</span> : <span>No warnings</span>}
                <StatusBadge value={stage.status} />
              </div>
            </div>
          ))}
        </div>
        {inventory && extraction ? (
          <div className="pipeline-footnote">
            <Files aria-hidden="true" size={16} />
            <span>{inventory.totalCandidateFiles} candidates · {extraction.redactedEvidenceCandidates} redacted evidence candidates · {findingAssembly?.evidenceCards ?? 0} evidence cards · {reviewSupport?.supportedFindings ?? 0} review supports · {auditRecording?.recordedEventCount ?? metrics.auditRecordedEvents ?? 0} audit events · policy {contextRisk?.policyPackVersion ?? 'unknown'}</span>
          </div>
        ) : null}
      </section>

      <div className="dashboard-grid lower-grid">
        <section className="panel">
          <SectionHeader title="Priority findings" action={<TextLink to="/findings">View all</TextLink>} />
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
          <SectionHeader title="Recent audit activity" action={<TextLink to="/audit">View trail</TextLink>} />
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
    </>
  )
}
