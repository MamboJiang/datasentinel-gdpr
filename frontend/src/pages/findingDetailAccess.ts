import type { Finding, FindingSummary, PermissionBoundary, ReviewSupport } from '../types'

const EVIDENCE_REVIEW_ACTIONS = ['delete_candidate', 'keep_with_reason', 'correct_false_positive', 'reassign_owner', 'escalate']
const WORKSPACE_REVIEW_ACTION = 'review_findings'
type EvidenceReviewBoundary = Pick<PermissionBoundary, 'allowedActions' | 'deniedActions'>

export function canOpenEvidenceReview(
  reviewSupport: Pick<ReviewSupport, 'availableDecisions' | 'permissionBoundary'>,
  workspaceBoundary?: EvidenceReviewBoundary,
): boolean {
  const allowedActions = reviewSupport.permissionBoundary?.allowedActions ?? []
  return (
    reviewSupport.availableDecisions.length > 0
    || EVIDENCE_REVIEW_ACTIONS.some((action) => allowedActions.includes(action))
    || Boolean(workspaceBoundary?.allowedActions.includes(WORKSPACE_REVIEW_ACTION))
  )
}

export function evidenceReviewDeniedReason(
  reviewSupport: Pick<ReviewSupport, 'permissionBoundary'>,
  workspaceBoundary?: EvidenceReviewBoundary,
): string {
  const denial = reviewSupport.permissionBoundary?.deniedActions.find((item) => EVIDENCE_REVIEW_ACTIONS.includes(item.action))
  const workspaceDenial = workspaceBoundary?.deniedActions.find((item) => item.action === WORKSPACE_REVIEW_ACTION)
  return denial?.reason ?? workspaceDenial?.reason ?? 'Evidence navigation is outside the current permission boundary.'
}

export function hasRenderableFindingDetail(finding: Finding | undefined): finding is Finding {
  if (!finding) {
    return false
  }

  const expectedSignals = finding.evidenceSignalCount ?? finding.personalDataTypes?.length ?? 0
  const hasExpectedEvidence = expectedSignals <= 0 || Boolean(finding.signals?.length)
  const hasDetailContext = Boolean(finding.riskExplanation || finding.file || finding.auditTimeline)

  return hasExpectedEvidence && hasDetailContext
}

export function currentFindingRedirectPath(requestedFindingId: string, findings: FindingSummary[]): string | null {
  if (findings.some((finding) => finding.findingId === requestedFindingId)) {
    return null
  }

  const target = [...findings].sort(compareFindingPriority)[0]
  return target ? `/findings/${target.findingId}` : '/findings'
}

function compareFindingPriority(left: FindingSummary, right: FindingSummary): number {
  const riskDelta = riskPriority(right.riskLevel) - riskPriority(left.riskLevel)
  if (riskDelta !== 0) {
    return riskDelta
  }

  return (right.evidenceSignalCount ?? 0) - (left.evidenceSignalCount ?? 0)
}

function riskPriority(riskLevel: string | undefined): number {
  if (riskLevel === 'high') {
    return 3
  }
  if (riskLevel === 'medium') {
    return 2
  }
  if (riskLevel === 'low') {
    return 1
  }
  return 0
}
