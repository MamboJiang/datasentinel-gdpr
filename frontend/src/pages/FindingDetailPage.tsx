import { ArrowLeft, CalendarClock, FileSearch, FileText, Flag, ShieldAlert, UserRound, X } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useData } from '../data/useData'
import type { ReviewDecision } from '../types'
import { formatBytes, formatDate, humanize } from '../components/formatters'
import { FileReviewEditor } from '../components/FileReviewEditor'
import { safeFindingSourceLabel } from '../components/findingDisplay'
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
  const [fileReviewOpen, setFileReviewOpen] = useState(false)
  const [initialSignalIndex, setInitialSignalIndex] = useState(0)

  if (!finding) {
    return <EmptyState title="Finding not available" />
  }

  return (
    <>
      <Link className="back-link" to="/findings"><ArrowLeft aria-hidden="true" size={16} /> Back to findings</Link>
      <header className="detail-header">
        <div>
          <p className="eyebrow">{finding.findingId}</p>
          <h1>{finding.fileName}</h1>
          <p className="page-description">{safeFindingSourceLabel(finding)}</p>
        </div>
        <div className="detail-actions">
          <RiskBadge riskLevel={finding.riskLevel} score={finding.riskScore} />
          <Button
            icon={FileSearch}
            variant="secondary"
            onClick={() => {
              setInitialSignalIndex(0)
              setFileReviewOpen(true)
            }}
          >
            Open file
          </Button>
          <Button icon={Flag} onClick={() => setReviewOpen(true)}>Record review</Button>
        </div>
      </header>

      <div className="detail-grid">
        <div className="detail-main">
          <section className="panel">
            <div className="section-header">
              <div><h2>Risk explanation</h2></div>
              <ShieldAlert aria-hidden="true" className="section-icon" size={20} />
            </div>
            <p className="explanation">{finding.riskExplanation ?? 'No explanation is available for this finding.'}</p>
            <div className="tag-row">
              {(finding.personalDataTypes ?? []).map((type) => <span className="data-tag" key={type}>{humanize(type)}</span>)}
            </div>
          </section>

          <section className="panel">
            <div className="section-header">
              <div><h2>Redacted evidence</h2></div>
              <FileText aria-hidden="true" className="section-icon" size={20} />
            </div>
            <div className="signal-list">
              {(finding.signals ?? []).map((signal, index) => (
                <article className="signal-card" key={`${signal.type}-${signal.detector}-${index}`}>
                  <div className="signal-topline">
                    <strong>{humanize(signal.type)}</strong>
                    <span>{Math.round(signal.confidence * 100)}% confidence</span>
                  </div>
                  <code>{signal.snippet}</code>
                  <div className="signal-meta">
                    <span>{humanize(signal.detector)}</span>
                    {signal.page ? <span>Page {signal.page}</span> : null}
                  </div>
                  <button
                    className="signal-open-button"
                    type="button"
                    onClick={() => {
                      setInitialSignalIndex(index)
                      setFileReviewOpen(true)
                    }}
                  >
                    Open at evidence
                  </button>
                </article>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="section-header">
              <div><h2>Audit timeline</h2></div>
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
            {finding.owner?.assignmentReason ? <p className="assignment-reason">{finding.owner.assignmentReason}</p> : null}
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

          <section className="panel">
            <h2>Action boundary</h2>
            <div className="action-list">
              {(finding.availableActions ?? []).map((action) => (
                <span className="action-pill action-allowed" key={action}>{humanize(action)}</span>
              ))}
              {(finding.deniedActions ?? []).map((denial) => (
                <span className="action-pill action-denied" key={denial.action}>{humanize(denial.action)} denied: {denial.reason}</span>
              ))}
            </div>
          </section>
        </aside>
      </div>

      {reviewOpen ? <ReviewDialog findingId={finding.findingId} onClose={() => setReviewOpen(false)} /> : null}
      {fileReviewOpen ? (
        <FileReviewEditor finding={finding} initialSignalIndex={initialSignalIndex} onClose={() => setFileReviewOpen(false)} />
      ) : null}
    </>
  )
}

function ReviewDialog({ findingId, onClose }: { findingId: string; onClose: () => void }) {
  const { getReviewSupport, reviewFinding } = useData()
  const reviewSupport = getReviewSupport(findingId)
  const decisions = reviewSupport.availableDecisions
  const [decision, setDecision] = useState<ReviewDecision>(decisions[0]?.decision ?? 'escalate')
  const [reason, setReason] = useState('')
  const [nextAction, setNextAction] = useState('')
  const [retentionUntil, setRetentionUntil] = useState(getDefaultRetentionDate())
  const [checkedItems, setCheckedItems] = useState<Record<string, boolean>>({})
  const checklistComplete = reviewSupport.checklist.every((item) => !item.required || checkedItems[item.itemId])
  const decisionAvailable = decisions.some((option) => option.decision === decision)
  const activeDecision = decisionAvailable ? decision : decisions[0]?.decision ?? ''
  const activeNextAction = decisionAvailable ? nextAction : ''
  const targetRequired = activeDecision === 'reassign_owner' || activeDecision === 'escalate'
  const retentionRequired = activeDecision === 'keep_with_reason'
  const checkedChecklistIds = Object.entries(checkedItems)
    .filter(([, checked]) => checked)
    .map(([itemId]) => itemId)
  const canSubmit =
    decisions.length > 0
    && activeDecision.length > 0
    && checklistComplete
    && reason.trim().length > 0
    && (!targetRequired || activeNextAction.length > 0)
    && (!retentionRequired || retentionUntil.length > 0)

  function submitReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canSubmit) {
      return
    }

    reviewFinding({
      findingId,
      decision: activeDecision as ReviewDecision,
      reason,
      actorId: reviewSupport.actorId,
      checklistItemIds: checkedChecklistIds,
      nextAction: activeNextAction,
      reassignToUserId: activeDecision === 'reassign_owner' ? activeNextAction : undefined,
      retentionUntil: activeDecision === 'keep_with_reason' ? retentionUntil : undefined,
    })
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
          </div>
          <label className="form-field">
            <span>Decision</span>
            <select
              disabled={decisions.length === 0}
              value={activeDecision}
              onChange={(event) => {
                if (!event.target.value) {
                  return
                }
                setDecision(event.target.value as ReviewDecision)
                setNextAction('')
              }}
            >
              {decisions.length === 0 ? <option value="">No available decisions</option> : null}
              {decisions.map((option) => <option key={option.decision} value={option.decision}>{option.label ?? humanize(option.decision)}</option>)}
            </select>
            {decisions.length === 0 ? <small className="form-help">No review decision is available inside the current permission boundary.</small> : null}
          </label>
          {activeDecision === 'reassign_owner' ? (
            <label className="form-field">
              <span>Transfer target</span>
              <select required value={activeNextAction} onChange={(event) => setNextAction(event.target.value)}>
                <option value="">Select an owner</option>
                {(reviewSupport.transferOptions ?? []).map((option) => <option key={option.userId} value={option.userId}>{option.displayName}</option>)}
              </select>
            </label>
          ) : null}
          {activeDecision === 'escalate' ? (
            <label className="form-field">
              <span>Escalation queue</span>
              <select required value={activeNextAction} onChange={(event) => setNextAction(event.target.value)}>
                <option value="">Select a queue</option>
                {(reviewSupport.escalationOptions ?? []).map((option) => <option key={option.queueId} value={option.queueId}>{option.label}</option>)}
              </select>
            </label>
          ) : null}
          {activeDecision === 'keep_with_reason' ? (
            <label className="form-field">
              <span>Retention review date</span>
              <input required type="date" value={retentionUntil} onChange={(event) => setRetentionUntil(event.target.value)} />
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
            <span>Source deletion disabled</span>
          </div>
          <div className="permission-summary">
            <strong>Your permission boundary</strong>
            {(reviewSupport.permissionBoundary?.deniedActions ?? []).map((action) => <p key={action.action}>{humanize(action.action)}: {action.reason}</p>)}
          </div>
          <div className="dialog-actions">
            <Button variant="ghost" onClick={onClose}>Cancel</Button>
            <Button disabled={!canSubmit} type="submit">Record decision</Button>
          </div>
        </form>
      </section>
    </div>
  )
}

function getDefaultRetentionDate(): string {
  const date = new Date()
  date.setUTCFullYear(date.getUTCFullYear() + 1)

  return date.toISOString().slice(0, 10)
}
