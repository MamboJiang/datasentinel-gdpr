import type { AuditEvent, AuditEvidenceReference, AuditRecordingSummary } from '../types'

export type AuditObjectType =
  | 'scan'
  | 'source'
  | 'owner_assignment'
  | 'finding_assembly'
  | 'finding'
  | 'review_decision'

export type AuditEventDraft = {
  action: string
  actorId: string
  auditEventId: string
  eventType: string
  objectId: string
  objectType: AuditObjectType
  occurredAt: string
  outcome: string
  actorType?: 'human' | 'system'
  deletionExecuted?: boolean
  decision?: AuditEvent['decision']
  evidenceReferences?: AuditEvidenceReference[]
  findingId?: string | null
  idempotencyKey?: string
  permissionBoundaryFingerprint?: string
  policyPackVersion?: string
  previousState?: string | null
  reason?: string
  recordedAt?: string
  resultingState?: string | null
  resultingStatus?: string
  retentionUntil?: string | null
  reviewSupportRulesFingerprint?: string
  scanId?: string | null
  sourceId?: string
  stage?: string
  summary?: string
  targetId?: string
  targetLabel?: string
}

export type AuditRecordingSummaryInput = {
  auditEvents: AuditEvent[]
  policyPackVersion: string
  scanId: string
  state: 'pending' | 'completed'
}

const auditRecordVersion = 'audit-event-v1'

const maskingPatterns: { pattern: RegExp; replacement: string }[] = [
  { pattern: /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, replacement: '[redacted-email]' },
  { pattern: /\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]){11,30}\b/g, replacement: '[redacted-iban]' },
  { pattern: /\b(?:\+?\d[\s-]?){9,}\b/g, replacement: '[redacted-number]' },
]

export function createAuditEvent(draft: AuditEventDraft): AuditEvent {
  const summary = sanitizeAuditText(draft.summary)
  const reason = sanitizeAuditText(draft.reason)
  const targetLabel = sanitizeAuditText(draft.targetLabel)

  return removeUndefinedFields({
    auditEventId: draft.auditEventId,
    scanId: draft.scanId ?? null,
    findingId: draft.findingId ?? null,
    eventType: draft.eventType,
    actorId: draft.actorId,
    actorType: draft.actorType ?? inferActorType(draft.actorId),
    occurredAt: draft.occurredAt,
    recordedAt: draft.recordedAt ?? draft.occurredAt,
    auditRecordVersion,
    objectType: draft.objectType,
    objectId: draft.objectId,
    action: draft.action,
    outcome: draft.outcome,
    stage: draft.stage,
    sourceId: draft.sourceId,
    previousState: draft.previousState,
    resultingState: draft.resultingState,
    summary,
    evidenceReferences: draft.evidenceReferences?.map(sanitizeEvidenceReference),
    decision: draft.decision,
    reason,
    resultingStatus: draft.resultingStatus,
    targetId: draft.targetId,
    targetLabel,
    retentionUntil: draft.retentionUntil,
    deletionExecuted: draft.deletionExecuted,
    policyPackVersion: draft.policyPackVersion,
    permissionBoundaryFingerprint: draft.permissionBoundaryFingerprint,
    reviewSupportRulesFingerprint: draft.reviewSupportRulesFingerprint,
    idempotencyKey: draft.idempotencyKey,
    rawContentExposed: false,
    legalConclusionProvided: false,
  })
}

export function prependAuditEvent(auditEvents: AuditEvent[], event: AuditEvent): AuditEvent[] {
  return [event, ...auditEvents]
}

export function prependAuditEvents(auditEvents: AuditEvent[], events: AuditEvent[]): AuditEvent[] {
  return [...deduplicateAuditEvents(events), ...auditEvents]
}

export function deduplicateAuditEvents(events: AuditEvent[]): AuditEvent[] {
  const seen = new Set<string>()

  return events.filter((event) => {
    if (seen.has(event.auditEventId)) {
      return false
    }

    seen.add(event.auditEventId)
    return true
  })
}

export function collectFindingTimelineEvents(findings: Record<string, { auditTimeline?: AuditEvent[] }>): AuditEvent[] {
  return Object.values(findings).flatMap((finding) => finding.auditTimeline ?? [])
}

export function buildAuditRecordingSummary(input: AuditRecordingSummaryInput): AuditRecordingSummary {
  const events = input.auditEvents.filter((event) => event.scanId === input.scanId)

  return {
    status: input.state,
    policyPackVersion: input.policyPackVersion,
    auditRulesFingerprint: `sha256:${input.policyPackVersion}_${input.scanId}_${input.state}_${events.length}_audit_recording_v1`,
    recordedEventCount: events.length,
    linkedScanEvents: events.filter((event) => event.objectType === 'scan').length,
    linkedFindingEvents: events.filter((event) => event.findingId).length,
    reviewDecisionEvents: events.filter((event) => event.eventType === 'review_recorded').length,
    systemEvents: events.filter((event) => (event.actorType ?? inferActorType(event.actorId)) === 'system').length,
    humanEvents: events.filter((event) => (event.actorType ?? inferActorType(event.actorId)) === 'human').length,
    rawContentExposed: events.some((event) => event.rawContentExposed === true),
    legalConclusionProvided: events.some((event) => event.legalConclusionProvided === true),
    deletionExecuted: events.some((event) => event.deletionExecuted === true),
    warnings: input.state === 'pending'
      ? ['Audit recording waits for completed workflow events before final traceability counts are available.']
      : [],
  }
}

export function sanitizeAuditText(value: string | null | undefined): string | undefined {
  if (!value) {
    return undefined
  }

  const collapsed = value.replace(/[\r\n\t]+/g, ' ').replace(/\s{2,}/g, ' ').trim()

  return maskingPatterns.reduce((current, { pattern, replacement }) => (
    current.replace(pattern, replacement)
  ), collapsed)
}

function sanitizeEvidenceReference(reference: AuditEvidenceReference): AuditEvidenceReference {
  return removeUndefinedFields({
    type: sanitizeAuditText(reference.type) ?? 'unknown',
    id: sanitizeAuditText(reference.id) ?? 'unknown',
    label: sanitizeAuditText(reference.label),
  })
}

function inferActorType(actorId: string): 'human' | 'system' {
  return actorId === 'system' || actorId.startsWith('svc_') ? 'system' : 'human'
}

function removeUndefinedFields<T extends Record<string, unknown>>(value: T): T {
  return Object.fromEntries(
    Object.entries(value).filter(([, entry]) => entry !== undefined),
  ) as T
}
