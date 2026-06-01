import { describe, expect, it } from 'vitest'
import { canOpenEvidenceReview, evidenceReviewDeniedReason, hasRenderableFindingDetail } from './findingDetailAccess'
import type { Finding, ReviewSupport } from '../types'

describe('finding detail evidence review permissions', () => {
  it('allows evidence navigation when review decisions are available', () => {
    const reviewSupport = support({
      allowedActions: ['view_assigned_findings'],
      availableDecisions: ['escalate'],
    })

    expect(canOpenEvidenceReview(reviewSupport)).toBe(true)
  })

  it('allows evidence navigation for a reviewer boundary even after decisions are unavailable', () => {
    const reviewSupport = support({
      allowedActions: ['view_assigned_findings', 'keep_with_reason'],
      availableDecisions: [],
    })

    expect(canOpenEvidenceReview(reviewSupport)).toBe(true)
  })

  it('allows evidence navigation for workspace review authority', () => {
    const reviewSupport = support({
      allowedActions: ['view_assigned_findings'],
      availableDecisions: [],
      deniedActions: [{
        action: 'keep_with_reason',
        reason: 'Finding-level reviewer is different from the current workspace reviewer.',
      }],
    })

    expect(canOpenEvidenceReview(reviewSupport, {
      allowedActions: ['view_assigned_findings', 'review_findings'],
      deniedActions: [],
    })).toBe(true)
  })

  it('denies evidence navigation for view-only actors and exposes the permission reason', () => {
    const reviewSupport = support({
      allowedActions: ['view_assigned_findings'],
      availableDecisions: [],
      deniedActions: [{
        action: 'keep_with_reason',
        reason: 'Current actor can view assigned findings but cannot record review decisions for this finding.',
      }],
    })

    expect(canOpenEvidenceReview(reviewSupport)).toBe(false)
    expect(evidenceReviewDeniedReason(reviewSupport)).toBe(
      'Current actor can view assigned findings but cannot record review decisions for this finding.',
    )
  })
})

describe('finding detail payload readiness', () => {
  it('does not treat a list summary as a renderable detail payload', () => {
    expect(hasRenderableFindingDetail({
      evidenceSignalCount: 2,
      fileName: 'summary-only.csv',
      findingId: 'finding_002',
      riskLevel: 'high',
      riskScore: 91,
      status: 'assigned',
    })).toBe(false)
  })

  it('rejects a partial detail payload that lacks expected redacted signals', () => {
    expect(hasRenderableFindingDetail({
      auditTimeline: [],
      evidenceSignalCount: 2,
      fileName: 'partial-detail.csv',
      findingId: 'finding_002',
      riskLevel: 'high',
      riskScore: 91,
      status: 'assigned',
    })).toBe(false)
  })

  it('accepts a requested finding detail with redacted evidence and context', () => {
    expect(hasRenderableFindingDetail({
      auditTimeline: [],
      evidenceSignalCount: 1,
      file: {
        sourceName: 'Controlled source',
        sourceType: 'local_repo',
      },
      fileName: 'detail.csv',
      findingId: 'finding_002',
      policyContext: {
        policyPackVersion: '2026.05-demo',
      },
      riskExplanation: 'Redacted evidence requires review.',
      riskLevel: 'high',
      riskScore: 91,
      signals: [{ confidence: 0.98, detector: 'regex', snippet: '[REDACTED_EMAIL]', type: 'email' }],
      status: 'assigned',
    } satisfies Finding)).toBe(true)
  })
})

function support({
  allowedActions,
  availableDecisions,
  deniedActions = [],
}: {
  allowedActions: string[]
  availableDecisions: Array<'delete_candidate' | 'keep_with_reason' | 'correct_false_positive' | 'reassign_owner' | 'escalate'>
  deniedActions?: { action: string; reason: string }[]
}): ReviewSupport {
  return {
    actorId: 'actor',
    availableDecisions: availableDecisions.map((decision) => ({ decision })),
    checklist: [],
    findingId: 'finding_001',
    permissionBoundary: {
      actorId: 'actor',
      allowedActions,
      deniedActions,
      roles: ['viewer'],
      visibleScopes: ['assigned_findings'],
    },
    policyPackVersion: 'test',
  }
}
