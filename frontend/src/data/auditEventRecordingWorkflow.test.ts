import { describe, expect, it } from 'vitest'
import { buildReviewSupport } from './reviewSupport'
import { getInitialMockData, type MockData } from './mockApi'
import { recordHumanReviewDecision, type HumanReviewCommand } from './humanReviewDecision'
import { completeScanWorkflow, startScanWorkflow } from './scanWorkflow'
import type { ReviewSupport } from '../types'

const startedAt = '2026-05-30T12:30:00.000Z'
const completedAt = '2026-05-30T12:30:38.200Z'
const reviewedAt = '2026-05-30T12:42:00.000Z'

function completeStartedScan(data: MockData = getInitialMockData()) {
  const started = startScanWorkflow(data, {
    actorId: 'user_demo_admin',
    auditEventId: 'audit_started',
    occurredAt: startedAt,
    scanType: 'full',
    sourceId: 'source_001',
  })

  if (!started.accepted) {
    throw new Error('Expected full scan start to be accepted.')
  }

  return completeScanWorkflow(started.data, {
    auditEventId: 'audit_completed',
    occurredAt: completedAt,
    scanId: started.scanId,
  })
}

function supportFor(data: MockData): ReviewSupport {
  return buildReviewSupport({
    actorId: 'user_anna',
    finding: data.findingDetails.finding_001,
    governanceConfig: data.governanceConfig,
    occurredAt: reviewedAt,
  })
}

function commandFor(data: MockData, reviewSupport: ReviewSupport, overrides: Partial<HumanReviewCommand> = {}): HumanReviewCommand {
  return {
    actorId: reviewSupport.actorId,
    auditEventId: 'audit_review_sensitive_reason',
    checklistItemIds: reviewSupport.checklist.filter((item) => item.required).map((item) => item.itemId),
    decision: 'delete_candidate',
    findingId: reviewSupport.findingId,
    idempotencyKey: 'idem_sensitive_reason',
    occurredAt: reviewedAt,
    reason: 'Reviewer saw anna@example.com and DE44500105175407324931 in notes.\nProceed with candidate only.',
    reviewId: 'review_sensitive_reason',
    reviewSupportRulesFingerprint: data.scan.reviewSupport?.supportRulesFingerprint,
    ...overrides,
  }
}

describe('audit event recording workflow', () => {
  it('records scan, assignment, assembly, and finding timeline events as first-class audit events', () => {
    const completed = completeStartedScan()
    const scanEvents = completed.auditEvents.filter((event) => event.scanId === 'scan_demo_full')
    const stageNames = completed.scan.pipelineStages?.map((stage) => stage.stage)

    expect(stageNames).toContain('recording_audit_events')
    expect(stageNames?.at(-1)).toBe('generating_evaluation_metrics')
    expect(completed.scan.auditRecording).toMatchObject({
      status: 'completed',
      recordedEventCount: 38,
      linkedScanEvents: 2,
      linkedFindingEvents: 34,
      reviewDecisionEvents: 0,
      rawContentExposed: false,
      legalConclusionProvided: false,
      deletionExecuted: false,
    })
    expect(scanEvents.some((event) => event.eventType === 'finding_assembled')).toBe(true)
    expect(scanEvents.some((event) => event.eventType === 'finding_assigned')).toBe(true)
    expect(scanEvents.every((event) => event.auditRecordVersion === 'audit-event-v1')).toBe(true)
    expect(scanEvents.every((event) => event.rawContentExposed === false)).toBe(true)
    expect(scanEvents.every((event) => event.legalConclusionProvided === false)).toBe(true)
    expect(scanEvents.every((event) => event.evidenceReferences?.length)).toBe(true)
  })

  it('sanitizes human review reasons and updates audit counts without executing deletion', () => {
    const completed = completeStartedScan()
    const reviewSupport = supportFor(completed)
    const result = recordHumanReviewDecision(completed, commandFor(completed, reviewSupport), reviewSupport)

    expect(result.accepted).toBe(true)

    if (!result.accepted) {
      return
    }

    expect(result.auditEvent).toMatchObject({
      actorType: 'human',
      eventType: 'review_recorded',
      objectType: 'review_decision',
      previousState: 'assigned',
      resultingState: 'delete_candidate',
      rawContentExposed: false,
      legalConclusionProvided: false,
      deletionExecuted: false,
    })
    expect(result.auditEvent.reason).toContain('[redacted-email]')
    expect(result.auditEvent.reason).toContain('[redacted-iban]')
    expect(result.auditEvent.reason).not.toMatch(/\n|anna@example\.com|DE44500105175407324931/)
    expect(result.data.scan.auditRecording).toMatchObject({
      recordedEventCount: 39,
      linkedFindingEvents: 35,
      reviewDecisionEvents: 1,
      systemEvents: 37,
      humanEvents: 2,
      deletionExecuted: false,
    })
    expect(result.data.metrics).toMatchObject({
      auditRecordedEvents: 39,
      auditLinkedFindingEvents: 35,
      auditReviewDecisionEvents: 1,
    })
  })
})
