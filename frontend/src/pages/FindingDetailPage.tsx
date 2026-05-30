import { ArrowLeft, CalendarClock, FileText, Flag, ShieldAlert, UserRound, X } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useData } from '../data/useData'
import type { ReviewDecision } from '../types'
import { formatBytes, formatDate, humanize } from '../components/formatters'
import {
  Button,
  EmptyState,
  RiskBadge,
  StatusBadge,
} from '../components/ui'

export function FindingDetailPage() {
  const { findingId = '' } = useParams()
  const { getFinding } = useData()
  const finding = getFinding(findingId)
  const [reviewOpen, setReviewOpen] = useState(false)

  if (!finding) {
    return <EmptyState title="Finding not available" description="This finding is missing from the current contract-backed fixture." />
  }

  return (
    <>
      <Link className="back-link" to="/findings"><ArrowLeft aria-hidden="true" size={16} /> Back to findings</Link>
      <header className="detail-header">
        <div>
          <p className="eyebrow">{finding.findingId}</p>
          <h1>{finding.fileName}</h1>
          <p className="page-description">{finding.sourcePath ?? 'Source path is not available'}</p>
        </div>
        <div className="detail-actions">
          <RiskBadge riskLevel={finding.riskLevel} score={finding.riskScore} />
          <Button icon={Flag} onClick={() => setReviewOpen(true)}>Record review</Button>
        </div>
      </header>

      <div className="detail-grid">
        <div className="detail-main">
          <section className="panel">
            <div className="section-header">
              <div><h2>Risk explanation</h2><p>Contextual guidance for human review</p></div>
              <ShieldAlert aria-hidden="true" className="section-icon" size={20} />
            </div>
            <p className="explanation">{finding.riskExplanation ?? 'No explanation is available for this finding.'}</p>
            <div className="tag-row">
              {(finding.personalDataTypes ?? []).map((type) => <span className="data-tag" key={type}>{humanize(type)}</span>)}
            </div>
          </section>

          <section className="panel">
            <div className="section-header">
              <div><h2>Redacted evidence</h2><p>Detector signals are masked by default</p></div>
              <FileText aria-hidden="true" className="section-icon" size={20} />
            </div>
            <div className="signal-list">
              {(finding.signals ?? []).map((signal) => (
                <article className="signal-card" key={`${signal.type}-${signal.detector}`}>
                  <div className="signal-topline">
                    <strong>{humanize(signal.type)}</strong>
                    <span>{Math.round(signal.confidence * 100)}% confidence</span>
                  </div>
                  <code>{signal.snippet}</code>
                  <div className="signal-meta">
                    <span>{humanize(signal.detector)}</span>
                    {signal.page ? <span>Page {signal.page}</span> : null}
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="section-header">
              <div><h2>Audit timeline</h2><p>Visible, attributable workflow events</p></div>
            </div>
            <div className="timeline">
              {(finding.auditTimeline ?? []).map((event) => (
                <div className="timeline-item" key={event.auditEventId}>
                  <div className="timeline-marker"><CalendarClock aria-hidden="true" size={14} /></div>
                  <div>
                    <strong>{humanize(event.eventType)}</strong>
                    <p>{event.summary}</p>
                    {event.reason ? <small>Reason: {event.reason}</small> : null}
                    <span>{formatDate(event.occurredAt)} · {event.actorId}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        <aside className="detail-sidebar">
          <section className="panel">
            <h2>Review context</h2>
            <dl className="definition-list">
              <div><dt>Status</dt><dd><StatusBadge value={finding.status} /></dd></div>
              <div><dt>Retention</dt><dd><StatusBadge value={finding.retentionStatus} /></dd></div>
              <div><dt>Recommended action</dt><dd>{finding.recommendedAction ? humanize(finding.recommendedAction) : 'Unknown'}</dd></div>
              <div><dt>Context</dt><dd>{finding.contextCategory ? humanize(finding.contextCategory) : 'Unknown'}</dd></div>
            </dl>
          </section>

          <section className="panel">
            <h2>Accountable owner</h2>
            <div className="owner-card">
              <div className="owner-avatar"><UserRound aria-hidden="true" size={18} /></div>
              <div><strong>{finding.owner?.displayName ?? 'Unassigned'}</strong><span>{finding.owner?.email ?? 'No email available'}</span></div>
            </div>
            <p className="assignment-label">{finding.owner?.assignmentType ? humanize(finding.owner.assignmentType) : 'Unknown assignment'}</p>
          </section>

          <section className="panel">
            <h2>File details</h2>
            <dl className="definition-list">
              <div><dt>Source</dt><dd>{finding.file?.sourceName ?? 'Unknown'}</dd></div>
              <div><dt>Type</dt><dd>{finding.file?.sourceType ? humanize(finding.file.sourceType) : 'Unknown'}</dd></div>
              <div><dt>Last modified</dt><dd>{formatDate(finding.file?.lastModifiedAt)}</dd></div>
              <div><dt>Size</dt><dd>{formatBytes(finding.file?.sizeBytes)}</dd></div>
            </dl>
          </section>

          <section className="panel">
            <h2>Policy context</h2>
            <dl className="definition-list">
              <div><dt>Policy pack</dt><dd>{finding.policyContext?.policyPackId ?? 'Unknown'}</dd></div>
              <div><dt>Version</dt><dd>{finding.policyContext?.policyPackVersion ?? 'Unknown'}</dd></div>
              <div><dt>Guidance</dt><dd>{finding.policyContext?.policyConclusion ? humanize(finding.policyContext.policyConclusion) : 'Unknown'}</dd></div>
            </dl>
          </section>
        </aside>
      </div>

      {reviewOpen ? <ReviewDialog findingId={finding.findingId} onClose={() => setReviewOpen(false)} /> : null}
    </>
  )
}

function ReviewDialog({ findingId, onClose }: { findingId: string; onClose: () => void }) {
  const { reviewFinding, reviewSupport } = useData()
  const decisions = reviewSupport.findingId === findingId ? reviewSupport.availableDecisions : []
  const [decision, setDecision] = useState<ReviewDecision>(decisions[0]?.decision ?? 'escalate')
  const [reason, setReason] = useState('')
  const [nextAction, setNextAction] = useState('')
  const [checkedItems, setCheckedItems] = useState<Record<string, boolean>>({})
  const checklistComplete = reviewSupport.checklist.every((item) => !item.required || checkedItems[item.itemId])

  function submitReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    reviewFinding({ findingId, decision, reason, actorId: reviewSupport.actorId, nextAction })
    onClose()
  }

  return (
    <div className="dialog-overlay" role="presentation">
      <section aria-labelledby="review-title" aria-modal="true" className="dialog-card" role="dialog">
        <div className="dialog-header">
          <div>
            <p className="eyebrow">Human-accountable action</p>
            <h2 id="review-title">Record review decision</h2>
          </div>
          <button className="icon-button" type="button" aria-label="Close review dialog" onClick={onClose}><X aria-hidden="true" size={18} /></button>
        </div>
        <form onSubmit={submitReview}>
          <div className="review-guidance">
            <strong>Policy guidance · {reviewSupport.policyPackVersion}</strong>
            <p>{reviewSupport.plainLanguageSummary ?? 'A human reviewer must make the final decision.'}</p>
          </div>
          <label className="form-field">
            <span>Decision</span>
            <select value={decision} onChange={(event) => setDecision(event.target.value as ReviewDecision)}>
              {decisions.map((option) => <option key={option.decision} value={option.decision}>{option.label ?? humanize(option.decision)}</option>)}
            </select>
          </label>
          {decision === 'reassign_owner' ? (
            <label className="form-field">
              <span>Transfer target</span>
              <select required value={nextAction} onChange={(event) => setNextAction(event.target.value)}>
                <option value="">Select an owner</option>
                {(reviewSupport.transferOptions ?? []).map((option) => <option key={option.userId} value={option.userId}>{option.displayName}</option>)}
              </select>
            </label>
          ) : null}
          {decision === 'escalate' ? (
            <label className="form-field">
              <span>Escalation queue</span>
              <select required value={nextAction} onChange={(event) => setNextAction(event.target.value)}>
                <option value="">Select a queue</option>
                {(reviewSupport.escalationOptions ?? []).map((option) => <option key={option.queueId} value={option.queueId}>{option.label}</option>)}
              </select>
            </label>
          ) : null}
          <label className="form-field">
            <span>Reason</span>
            <textarea required rows={4} value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Document the accountable reason for this decision" />
          </label>
          <div className="review-checklist">
            <strong>Required checklist</strong>
            {reviewSupport.checklist.map((item) => (
              <label key={item.itemId}>
                <input checked={Boolean(checkedItems[item.itemId])} onChange={(event) => setCheckedItems((current) => ({ ...current, [item.itemId]: event.target.checked }))} type="checkbox" />
                <span>{item.label}</span>
              </label>
            ))}
          </div>
          <div className="dialog-notice">
            <ShieldAlert aria-hidden="true" size={17} />
            <span>Deletion is simulated in this prototype. No source file will be changed.</span>
          </div>
          <div className="permission-summary">
            <strong>Your permission boundary</strong>
            {(reviewSupport.permissionBoundary?.deniedActions ?? []).map((action) => <p key={action.action}>{humanize(action.action)}: {action.reason}</p>)}
          </div>
          <div className="dialog-actions">
            <Button variant="ghost" onClick={onClose}>Cancel</Button>
            <Button disabled={!reason.trim() || !checklistComplete} type="submit">Record decision</Button>
          </div>
        </form>
      </section>
    </div>
  )
}
