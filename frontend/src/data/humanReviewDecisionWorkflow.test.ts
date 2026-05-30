import { describe, expect, it } from 'vitest'
import { getInitialMockData, type MockData } from './mockApi'
import { recordHumanReviewDecision, type HumanReviewCommand } from './humanReviewDecision'
import { buildReviewSupport } from './reviewSupport'
import {
  completeScanWorkflow,
  startScanWorkflow,
} from './scanWorkflow'
import type { ReviewDecision, ReviewSupport } from '../types'

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

function supportFor(data: MockData, actorId = 'user_anna') {
  return buildReviewSupport({
    actorId,
    finding: data.findingDetails.finding_001,
    governanceConfig: data.governanceConfig,
    occurredAt: reviewedAt,
  })
}

function checklistIds(reviewSupport: ReviewSupport): string[] {
  return reviewSupport.checklist.filter((item) => item.required).map((item) => item.itemId)
}

function commandFor(
  data: MockData,
  reviewSupport: ReviewSupport,
  decision: ReviewDecision,
  overrides: Partial<HumanReviewCommand> = {},
): HumanReviewCommand {
  return {
    actorId: reviewSupport.actorId,
    auditEventId: `audit_review_${decision}`,
    checklistItemIds: checklistIds(reviewSupport),
    decision,
    findingId: reviewSupport.findingId,
    idempotencyKey: `idem_${decision}`,
    occurredAt: reviewedAt,
    reason: 'Human reviewer checked redacted evidence, owner context, and permission boundary.',
    reviewId: `review_${decision}`,
    reviewSupportRulesFingerprint: data.scan.reviewSupport?.supportRulesFingerprint,
    ...overrides,
  }
}

describe('human review decision handling', () => {
  it('records a delete candidate as an auditable human decision without executing deletion', () => {
    const completed = completeStartedScan()
    const reviewSupport = supportFor(completed)
    const beforeBacklog = completed.metrics.openReviewBacklog
    const result = recordHumanReviewDecision(
      completed,
      commandFor(completed, reviewSupport, 'delete_candidate'),
      reviewSupport,
    )

    expect(result.accepted).toBe(true)

    if (!result.accepted) {
      return
    }

    expect(result.review).toMatchObject({
      decision: 'delete_candidate',
      deletionExecuted: false,
      findingId: 'finding_001',
      policyPackVersion: '2026.05-demo',
      resultingStatus: 'delete_candidate',
    })
    expect(result.auditEvent).toMatchObject({
      actorId: 'user_anna',
      decision: 'delete_candidate',
      deletionExecuted: false,
      eventType: 'review_recorded',
      findingId: 'finding_001',
      occurredAt: reviewedAt,
      reason: 'Human reviewer checked redacted evidence, owner context, and permission boundary.',
      resultingStatus: 'delete_candidate',
      policyPackVersion: '2026.05-demo',
      permissionBoundaryFingerprint: reviewSupport.permissionBoundary?.boundaryFingerprint,
      reviewSupportRulesFingerprint: completed.scan.reviewSupport?.supportRulesFingerprint,
    })
    expect(result.data.findingDetails.finding_001.status).toBe('delete_candidate')
    expect(result.data.findingDetails.finding_001.auditTimeline?.[0]).toEqual(result.auditEvent)
    expect(result.data.auditEvents[0]).toEqual(result.auditEvent)
    expect(result.data.sources).toEqual(completed.sources)
    expect(result.data.metrics.openReviewBacklog).toBe(beforeBacklog - 1)
    expect(result.data.metrics.reviewDecisionCount).toBe((completed.metrics.reviewDecisionCount ?? 0) + 1)
    expect(result.data.metrics.deletionCandidateDecisions).toBe((completed.metrics.deletionCandidateDecisions ?? 0) + 1)
    expect(result.data.evaluation.reviewDecisionRulesHash).toContain('review_decision_v1')
    expect(result.data.evaluation.resourceIntensity).toMatchObject({
      modelCalls: 0,
      estimatedCostUsd: 0,
    })
  })

  it('records retain, false-positive, transfer, and escalation outcomes with required context', () => {
    const cases: {
      decision: ReviewDecision
      expectedStatus: string
      metric: string
      overrides?: Partial<HumanReviewCommand>
    }[] = [
      {
        decision: 'keep_with_reason',
        expectedStatus: 'retained',
        metric: 'retainedDecisions',
        overrides: { retentionUntil: '2027-05-30' },
      },
      {
        decision: 'correct_false_positive',
        expectedStatus: 'false_positive',
        metric: 'falsePositiveDecisions',
      },
      {
        decision: 'reassign_owner',
        expectedStatus: 'assigned',
        metric: 'reassignedDecisions',
        overrides: { nextAction: 'user_markus', reassignToUserId: 'user_markus' },
      },
      {
        decision: 'escalate',
        expectedStatus: 'escalated',
        metric: 'escalatedDecisions',
        overrides: { nextAction: 'legal_escalation' },
      },
    ]

    for (const entry of cases) {
      const completed = completeStartedScan()
      const reviewSupport = supportFor(completed)
      const result = recordHumanReviewDecision(
        completed,
        commandFor(completed, reviewSupport, entry.decision, entry.overrides),
        reviewSupport,
      )

      expect(result.accepted).toBe(true)

      if (!result.accepted) {
        continue
      }

      expect(result.data.findingDetails.finding_001.status).toBe(entry.expectedStatus)
      expect(result.data.metrics[entry.metric as keyof typeof result.data.metrics]).toBe(
        Number(completed.metrics[entry.metric as keyof typeof completed.metrics] ?? 0) + 1,
      )

      if (entry.decision === 'keep_with_reason') {
        expect(result.review.retentionUntil).toBe('2027-05-30')
        expect(result.data.findingDetails.finding_001.retentionStatus).toBe('retained_until_review')
      }

      if (entry.decision === 'reassign_owner') {
        expect(result.data.findingDetails.finding_001.owner).toMatchObject({
          userId: 'user_markus',
          assignmentSource: 'review_transfer',
        })
        expect(result.data.metrics.openReviewBacklog).toBe(completed.metrics.openReviewBacklog)
      }

      if (entry.decision === 'escalate') {
        expect(result.auditEvent.targetId).toBe('legal_escalation')
      }
    }
  })

  it('rejects denied, incomplete, stale, and unknown review commands without state changes', () => {
    const completed = completeStartedScan()
    const reviewerSupport = supportFor(completed)
    const guestSupport = supportFor(completed, 'user_guest')
    const rejectedCommands: { command: HumanReviewCommand; support: ReviewSupport; reason: string }[] = [
      {
        command: commandFor(completed, guestSupport, 'delete_candidate', {
          actorId: 'user_guest',
        }),
        support: guestSupport,
        reason: 'Mark as deletion candidate is outside the current permission boundary.',
      },
      {
        command: commandFor(completed, reviewerSupport, 'delete_candidate', {
          checklistItemIds: [],
        }),
        support: reviewerSupport,
        reason: 'All required review checklist items must be acknowledged before submission.',
      },
      {
        command: commandFor(completed, reviewerSupport, 'keep_with_reason'),
        support: reviewerSupport,
        reason: 'Retain decisions require a retention review date.',
      },
      {
        command: commandFor(completed, reviewerSupport, 'reassign_owner', {
          nextAction: 'user_missing',
          reassignToUserId: 'user_missing',
        }),
        support: reviewerSupport,
        reason: 'Transfer target is outside the current review support options.',
      },
      {
        command: commandFor(completed, reviewerSupport, 'escalate', {
          nextAction: 'queue_missing',
        }),
        support: reviewerSupport,
        reason: 'Escalation queue is outside the current review support options.',
      },
      {
        command: commandFor(completed, reviewerSupport, 'delete_candidate', {
          reviewSupportRulesFingerprint: 'sha256:stale_review_support',
        }),
        support: reviewerSupport,
        reason: 'Review support is stale and must be refreshed before submission.',
      },
      {
        command: commandFor(completed, reviewerSupport, 'delete_candidate', {
          findingId: 'finding_missing',
        }),
        support: reviewerSupport,
        reason: 'Finding is not available for review.',
      },
    ]

    for (const entry of rejectedCommands) {
      const result = recordHumanReviewDecision(completed, entry.command, entry.support)

      expect(result).toMatchObject({
        accepted: false,
        data: completed,
        reason: entry.reason,
      })
      expect(completed.auditEvents[0].eventType).toBe('full_scan_completed')
    }
  })

  it('does not duplicate audit events or metrics for the same idempotency key', () => {
    const completed = completeStartedScan()
    const reviewSupport = supportFor(completed)
    const command = commandFor(completed, reviewSupport, 'delete_candidate', {
      idempotencyKey: 'idem_repeat_delete_candidate',
    })
    const first = recordHumanReviewDecision(completed, command, reviewSupport)

    expect(first.accepted).toBe(true)

    if (!first.accepted) {
      return
    }

    const repeated = recordHumanReviewDecision(first.data, {
      ...command,
      auditEventId: 'audit_should_not_be_created',
      reviewId: 'review_repeat',
    }, reviewSupport)

    expect(repeated.accepted).toBe(true)

    if (!repeated.accepted) {
      return
    }

    expect(repeated.duplicate).toBe(true)
    expect(repeated.data).toBe(first.data)
    expect(repeated.auditEvent.auditEventId).toBe(first.auditEvent.auditEventId)
    expect(repeated.data.auditEvents.filter((event) => event.idempotencyKey === command.idempotencyKey)).toHaveLength(1)
    expect(repeated.data.metrics.reviewDecisionCount).toBe(first.data.metrics.reviewDecisionCount)
  })
})
