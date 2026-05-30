import type {
  ContextRiskSummary,
  GovernanceConfig,
  OwnerAssignmentSummary,
  Source,
} from '../types'

type OwnerAssignmentState = 'pending' | 'completed'

type AssignmentProfile = {
  directOwnerAssignments: number
  escalationAssignments: number
  masterOfDataAssignments: number
  unownedFindings: number
}

export function buildOwnerAssignmentSummary(
  scanType: string,
  source: Source,
  contextRisk: ContextRiskSummary,
  governanceConfig: GovernanceConfig,
  state: OwnerAssignmentState,
): OwnerAssignmentSummary {
  const policyPackVersion = governanceConfig.activePolicyPack.version
  const organizationModelVersion = governanceConfig.organizationModel.version
  const sourceOwnerAvailable = Boolean(source.masterOfDataUserId)
  const humanReviewRequiredFindings = state === 'completed'
    ? contextRisk.humanReviewRequiredFindings
    : 0
  const profile = state === 'completed'
    ? buildAssignmentProfile(scanType, humanReviewRequiredFindings, sourceOwnerAvailable, hasEscalationPath(governanceConfig))
    : emptyAssignmentProfile()
  const assignedFindings = profile.directOwnerAssignments
    + profile.masterOfDataAssignments
    + profile.escalationAssignments

  return {
    status: state,
    policyPackVersion,
    organizationModelVersion,
    ownerResolutionStrategy: governanceConfig.organizationModel.ownerResolutionStrategy,
    assignmentRulesFingerprint: `sha256:${policyPackVersion}_${organizationModelVersion}_${contextRisk.riskRulesFingerprint}_owner_assignment_${state}`,
    humanReviewRequiredFindings,
    assignedFindings,
    directOwnerAssignments: profile.directOwnerAssignments,
    masterOfDataAssignments: profile.masterOfDataAssignments,
    escalationAssignments: profile.escalationAssignments,
    unownedFindings: profile.unownedFindings,
    transferOptionCount: governanceConfig.organizationModel.delegationRules?.length ?? 0,
    escalationOptionCount: governanceConfig.activePolicyPack.escalationPaths?.length ?? 0,
    sourceOwnerAvailable,
    warnings: buildWarnings(state, sourceOwnerAvailable, profile),
  }
}

function buildAssignmentProfile(
  scanType: string,
  humanReviewRequiredFindings: number,
  sourceOwnerAvailable: boolean,
  escalationAvailable: boolean,
): AssignmentProfile {
  if (humanReviewRequiredFindings <= 0) {
    return emptyAssignmentProfile()
  }

  if (!sourceOwnerAvailable) {
    return escalationAvailable
      ? {
          directOwnerAssignments: 0,
          masterOfDataAssignments: 0,
          escalationAssignments: humanReviewRequiredFindings,
          unownedFindings: 0,
        }
      : {
          directOwnerAssignments: 0,
          masterOfDataAssignments: 0,
          escalationAssignments: 0,
          unownedFindings: humanReviewRequiredFindings,
        }
  }

  if (scanType === 'delta') {
    return {
      directOwnerAssignments: Math.min(1, humanReviewRequiredFindings),
      masterOfDataAssignments: Math.max(0, humanReviewRequiredFindings - 1),
      escalationAssignments: 0,
      unownedFindings: 0,
    }
  }

  const escalationAssignments = escalationAvailable ? Math.min(2, humanReviewRequiredFindings) : 0
  const remainingAfterEscalation = humanReviewRequiredFindings - escalationAssignments
  const masterOfDataAssignments = Math.min(5, Math.max(0, remainingAfterEscalation))

  return {
    directOwnerAssignments: Math.max(0, remainingAfterEscalation - masterOfDataAssignments),
    masterOfDataAssignments,
    escalationAssignments,
    unownedFindings: 0,
  }
}

function hasEscalationPath(governanceConfig: GovernanceConfig): boolean {
  return (governanceConfig.activePolicyPack.escalationPaths?.length ?? 0) > 0
}

function buildWarnings(
  state: OwnerAssignmentState,
  sourceOwnerAvailable: boolean,
  profile: AssignmentProfile,
): string[] {
  if (state === 'pending') {
    return ['Owner assignment waits for completed context/risk judgment.']
  }

  if (profile.unownedFindings > 0) {
    return [`${profile.unownedFindings} findings have no accountable owner or escalation path.`]
  }

  if (!sourceOwnerAvailable) {
    return ['Source Master of Data is missing; review-required findings route to escalation.']
  }

  return []
}

function emptyAssignmentProfile(): AssignmentProfile {
  return {
    directOwnerAssignments: 0,
    escalationAssignments: 0,
    masterOfDataAssignments: 0,
    unownedFindings: 0,
  }
}
