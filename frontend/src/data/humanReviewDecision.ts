import type { MockData } from './mockApi'
import {
  createAuditEvent,
  prependAuditEvent,
  sanitizeAuditText,
} from './auditEventRecording'
import {
  updateReviewDecisionEvaluation,
  updateReviewDecisionMetrics,
  updateScanAuditRecording,
} from './humanReviewEffects'
import { validateReviewInput } from './reviewSupport'
import type {
  AuditEvent,
  Finding,
  FindingSummary,
  Owner,
  ReviewDecision,
  ReviewInput,
  ReviewRecord,
  ReviewSupport,
} from '../types'

export type HumanReviewCommand = ReviewInput & {
  auditEventId: string
  occurredAt: string
  reviewId: string
  reviewSupportRulesFingerprint?: string
}

type ReviewDecisionAccepted = {
  accepted: true
  auditEvent: AuditEvent
  data: MockData
  duplicate: boolean
  review: ReviewRecord
  toast: string
}

type ReviewDecisionRejected = {
  accepted: false
  data: MockData
  reason: string
}

export type HumanReviewDecisionResult = ReviewDecisionAccepted | ReviewDecisionRejected

const decisionStatus: Record<ReviewDecision, string> = {
  delete_candidate: 'delete_candidate',
  keep_with_reason: 'retained',
  correct_false_positive: 'false_positive',
  reassign_owner: 'assigned',
  escalate: 'escalated',
}

export function recordHumanReviewDecision(
  current: MockData,
  input: HumanReviewCommand,
  reviewSupport: ReviewSupport,
): HumanReviewDecisionResult {
  const finding = getFinding(current, input.findingId)

  if (!finding) {
    return reject(current, 'Finding is not available for review.')
  }

  if (reviewSupport.findingId !== input.findingId) {
    return reject(current, 'Review support does not match this finding.')
  }

  const expectedFingerprint = current.scan.reviewSupport?.supportRulesFingerprint

  if (
    input.reviewSupportRulesFingerprint
    && expectedFingerprint
    && input.reviewSupportRulesFingerprint !== expectedFingerprint
  ) {
    return reject(current, 'Review support is stale and must be refreshed before submission.')
  }

  const duplicateAuditEvent = findDuplicateAuditEvent(current.auditEvents, input)

  if (duplicateAuditEvent) {
    return {
      accepted: true,
      auditEvent: duplicateAuditEvent,
      data: current,
      duplicate: true,
      review: buildReviewRecordFromAuditEvent(input.reviewId, duplicateAuditEvent),
      toast: 'Review decision already recorded.',
    }
  }

  const validation = validateReviewInput(input, reviewSupport)

  if (!validation.accepted) {
    return reject(current, validation.reason ?? 'Review decision is outside the current permission boundary.')
  }

  const target = resolveDecisionTarget(input, reviewSupport)
  const resultingStatus = decisionStatus[input.decision]
  const supportRulesFingerprint = input.reviewSupportRulesFingerprint ?? expectedFingerprint
  const reason = sanitizeAuditText(input.reason) ?? input.reason.trim()
  const review: ReviewRecord = {
    reviewId: input.reviewId,
    findingId: input.findingId,
    decision: input.decision,
    reason,
    actorId: input.actorId,
    createdAt: input.occurredAt,
    resultingStatus,
    auditEventId: input.auditEventId,
    targetId: target?.id,
    targetLabel: target?.label,
    retentionUntil: input.decision === 'keep_with_reason' ? input.retentionUntil ?? null : null,
    deletionExecuted: false,
    policyPackVersion: reviewSupport.policyPackVersion,
    permissionBoundaryFingerprint: reviewSupport.permissionBoundary?.boundaryFingerprint,
    reviewSupportRulesFingerprint: supportRulesFingerprint,
    idempotencyKey: input.idempotencyKey,
  }
  const auditEvent = createReviewAuditEvent(current, input, review, target)
  const nextAuditEvents = prependAuditEvent(current.auditEvents, auditEvent)
  const transferOwner = input.decision === 'reassign_owner' && target
    ? createDelegatedOwner(target)
    : undefined
  const evaluation = updateReviewDecisionEvaluation(
    current.evaluation,
    reviewSupport.policyPackVersion,
    supportRulesFingerprint,
  )

  return {
    accepted: true,
    auditEvent,
    data: {
      ...current,
      scan: updateScanAuditRecording(current.scan, nextAuditEvents, reviewSupport.policyPackVersion),
      findings: current.findings.map((candidate) => updateFinding(candidate, input, resultingStatus, transferOwner)),
      findingDetail: current.findingDetail.findingId === input.findingId
        ? updateFindingDetail(current.findingDetail, input, resultingStatus, transferOwner, auditEvent)
        : current.findingDetail,
      findingDetails: Object.fromEntries(
        Object.entries(current.findingDetails).map(([id, candidate]) => [
          id,
          candidate.findingId === input.findingId
            ? updateFindingDetail(candidate, input, resultingStatus, transferOwner, auditEvent)
            : candidate,
        ]),
      ),
      auditEvents: nextAuditEvents,
      metrics: updateReviewDecisionMetrics({
        auditEvents: nextAuditEvents,
        decision: input.decision,
        evaluation,
        metrics: current.metrics,
        scanId: current.scan.scanId,
      }),
      evaluation,
    },
    duplicate: false,
    review,
    toast: 'Review decision recorded. Deletion remains simulated.',
  }
}

function reject(current: MockData, reason: string): ReviewDecisionRejected {
  return { accepted: false, data: current, reason }
}

function getFinding(current: MockData, findingId: string): Finding | FindingSummary | undefined {
  return current.findingDetails[findingId]
    ?? (current.findingDetail.findingId === findingId ? current.findingDetail : undefined)
    ?? current.findings.find((candidate) => candidate.findingId === findingId)
}

function findDuplicateAuditEvent(auditEvents: AuditEvent[], input: HumanReviewCommand): AuditEvent | undefined {
  if (!input.idempotencyKey) {
    return undefined
  }

  return auditEvents.find((event) => (
    event.eventType === 'review_recorded'
    && event.findingId === input.findingId
    && event.idempotencyKey === input.idempotencyKey
  ))
}

function resolveDecisionTarget(input: ReviewInput, reviewSupport: ReviewSupport): { id: string; label: string } | undefined {
  if (input.decision === 'reassign_owner') {
    const targetId = input.reassignToUserId ?? input.nextAction
    const target = reviewSupport.transferOptions?.find((option) => option.userId === targetId)

    return target ? { id: target.userId, label: target.displayName } : undefined
  }

  if (input.decision === 'escalate') {
    const target = reviewSupport.escalationOptions?.find((option) => option.queueId === input.nextAction)

    return target ? { id: target.queueId, label: target.label } : undefined
  }

  return undefined
}

function createDelegatedOwner(target: { id: string; label: string }): Owner {
  return {
    userId: target.id,
    displayName: target.label,
    email: null,
    assignmentType: 'delegated',
    assignmentReason: 'Human reviewer transferred accountability with a recorded reason.',
    assignmentSource: 'review_transfer',
  }
}

function createReviewAuditEvent(
  current: MockData,
  input: HumanReviewCommand,
  review: ReviewRecord,
  target: { id: string; label: string } | undefined,
): AuditEvent {
  const previousStatus = getFinding(current, input.findingId)?.status ?? 'unknown'

  return createAuditEvent({
    action: 'record_review_decision',
    actorId: input.actorId,
    auditEventId: input.auditEventId,
    scanId: getFinding(current, input.findingId)?.scanId ?? null,
    findingId: input.findingId,
    eventType: 'review_recorded',
    objectId: input.findingId,
    objectType: 'review_decision',
    occurredAt: input.occurredAt,
    outcome: review.resultingStatus,
    previousState: previousStatus,
    resultingState: review.resultingStatus,
    stage: 'recording_audit_events',
    summary: buildDecisionSummary(input, target),
    evidenceReferences: [
      { type: 'finding', id: input.findingId, label: 'redacted evidence card' },
      { type: 'policy_pack', id: review.policyPackVersion ?? 'unknown' },
      { type: 'permission_boundary', id: review.permissionBoundaryFingerprint ?? 'unknown' },
      { type: 'review_support', id: review.reviewSupportRulesFingerprint ?? 'unknown' },
    ],
    decision: input.decision,
    reason: review.reason,
    resultingStatus: review.resultingStatus,
    targetId: review.targetId,
    targetLabel: review.targetLabel,
    retentionUntil: review.retentionUntil,
    deletionExecuted: false,
    policyPackVersion: review.policyPackVersion,
    permissionBoundaryFingerprint: review.permissionBoundaryFingerprint,
    reviewSupportRulesFingerprint: review.reviewSupportRulesFingerprint,
    idempotencyKey: review.idempotencyKey,
  })
}

function buildDecisionSummary(input: ReviewInput, target: { id: string; label: string } | undefined): string {
  switch (input.decision) {
    case 'delete_candidate':
      return 'Finding marked as a deletion candidate. Real deletion remains disabled.'
    case 'keep_with_reason':
      return `Finding retained with a documented reason until ${input.retentionUntil}.`
    case 'correct_false_positive':
      return 'Finding corrected as a false positive by a human reviewer.'
    case 'reassign_owner':
      return `Finding reassigned to ${target?.label ?? 'another owner'} for review.`
    case 'escalate':
      return `Finding escalated to ${target?.label ?? 'an escalation queue'}.`
  }
}

function updateFinding<T extends FindingSummary>(
  finding: T,
  input: ReviewInput,
  resultingStatus: string,
  transferOwner: Owner | undefined,
): T {
  if (finding.findingId !== input.findingId) {
    return finding
  }

  return {
    ...finding,
    owner: transferOwner ?? finding.owner,
    retentionStatus: input.decision === 'keep_with_reason'
      ? 'retained_until_review'
      : finding.retentionStatus,
    status: resultingStatus,
  }
}

function updateFindingDetail(
  finding: Finding,
  input: ReviewInput,
  resultingStatus: string,
  transferOwner: Owner | undefined,
  auditEvent: AuditEvent,
): Finding {
  return {
    ...updateFinding(finding, input, resultingStatus, transferOwner),
    auditTimeline: [auditEvent, ...(finding.auditTimeline ?? [])],
  }
}

function buildReviewRecordFromAuditEvent(reviewId: string, auditEvent: AuditEvent): ReviewRecord {
  return {
    reviewId,
    findingId: auditEvent.findingId ?? 'unknown',
    decision: auditEvent.decision ?? 'escalate',
    reason: auditEvent.reason ?? 'Review decision already recorded.',
    actorId: auditEvent.actorId,
    createdAt: auditEvent.occurredAt,
    resultingStatus: auditEvent.resultingStatus ?? 'unknown',
    auditEventId: auditEvent.auditEventId,
    targetId: auditEvent.targetId,
    targetLabel: auditEvent.targetLabel,
    retentionUntil: auditEvent.retentionUntil ?? null,
    deletionExecuted: auditEvent.deletionExecuted ?? false,
    policyPackVersion: auditEvent.policyPackVersion,
    permissionBoundaryFingerprint: auditEvent.permissionBoundaryFingerprint,
    reviewSupportRulesFingerprint: auditEvent.reviewSupportRulesFingerprint,
    idempotencyKey: auditEvent.idempotencyKey,
  }
}
