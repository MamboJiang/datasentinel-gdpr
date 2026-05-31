import { describe, expect, it } from 'vitest'
import { canOpenEvidenceReview, evidenceReviewDeniedReason } from './findingDetailAccess'
import type { ReviewSupport } from '../types'

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
