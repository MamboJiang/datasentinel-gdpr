import type {
  Finding,
  GovernanceConfig,
  PermissionBoundary,
  ReviewDecision,
  ReviewInput,
  ReviewSupport,
  ReviewSupportSummary,
  FindingAssemblySummary,
  WorkspaceMembership,
} from '../types'

type ReviewSupportState = 'pending' | 'completed'

type ReviewSupportSummaryInput = {
  actorId: string
  findingAssembly: FindingAssemblySummary
  governanceConfig: GovernanceConfig
  permissionBoundary: PermissionBoundary
  state: ReviewSupportState
}

type ReviewSupportInput = {
  actorId: string
  finding: Finding
  governanceConfig: GovernanceConfig
  occurredAt: string
  workspaceMembers?: WorkspaceMembership[]
}

type ValidationResult = {
  accepted: boolean
  reason?: string
}

const p0ReviewDecisions: ReviewDecision[] = [
  'delete_candidate',
  'keep_with_reason',
  'correct_false_positive',
  'reassign_owner',
  'escalate',
]

const decisionLabels: Record<ReviewDecision, string> = {
  delete_candidate: 'Approve delete (mark candidate)',
  keep_with_reason: 'Keep with business reason',
  correct_false_positive: 'Correct false positive',
  reassign_owner: 'Transfer to another owner',
  escalate: 'Escalate to DPO or Legal',
}

const actorProfiles: Record<string, { roles: string[]; visibleScopes: string[] }> = {
  authenticated_user: {
    roles: ['reviewer'],
    visibleScopes: ['assigned_findings', 'configured_sources'],
  },
  user_anna: {
    roles: ['master_of_data', 'reviewer'],
    visibleScopes: ['assigned_findings', 'finance_org_unit'],
  },
  user_demo_admin: {
    roles: ['governance_admin', 'master_of_data', 'reviewer'],
    visibleScopes: ['assigned_findings', 'finance_org_unit', 'governance_config'],
  },
  user_markus: {
    roles: ['reviewer'],
    visibleScopes: ['assigned_findings', 'it_org_unit'],
  },
}

export function buildPermissionBoundary({
  actorId,
  finding,
  governanceConfig,
  occurredAt,
  workspaceMembers,
}: ReviewSupportInput): PermissionBoundary {
  const workspaceMember = workspaceMembers?.find((member) => member.accountId === actorId)
  const profile = workspaceMember ? {
    roles: workspaceMember.groupIds,
    visibleScopes: ['assigned_findings', `workspace:${workspaceMember.workspaceId}`],
  } : actorProfiles[actorId] ?? {
    roles: ['viewer'],
    visibleScopes: ['assigned_findings'],
  }
  const policyDecisions = getPolicyDecisions(governanceConfig)
  const ownsFinding = finding.owner?.userId === actorId
  const canReview = workspaceMember
    ? ownsFinding && canReceiveReview(workspaceMember)
    : ownsFinding || profile.roles.includes('reviewer') || profile.roles.includes('master_of_data')
  const allowedActions = canReview
    ? ['view_assigned_findings', ...policyDecisions]
    : ['view_assigned_findings']
  const deniedActions = [
    ...(!canReview
      ? policyDecisions.map((decision) => ({
          action: decision,
          reason: 'Current actor can view assigned findings but cannot record review decisions for this finding.',
        }))
      : []),
    ...(!profile.roles.includes('governance_admin')
      ? [{
          action: 'activate_policy_pack',
          reason: 'Governance admin role is required.',
        }]
      : []),
    ...(!governanceConfig.changeControls?.realDeletionAllowed
      ? [{
          action: 'execute_real_deletion',
          reason: 'Real deletion is disabled in the prototype.',
        }]
      : []),
  ]

  return {
    actorId,
    roles: profile.roles,
    allowedActions,
    deniedActions,
    visibleScopes: profile.visibleScopes,
    boundaryFingerprint: `sha256:${actorId}_${governanceConfig.activePolicyPack.version}_${finding.findingId}_permission_boundary`,
    evaluatedAt: occurredAt,
  }
}

export function buildReviewSupportSummary(input: ReviewSupportSummaryInput): ReviewSupportSummary {
  const completed = input.state === 'completed'
  const policyDecisions = getPolicyDecisions(input.governanceConfig)
  const reasonRequiredDecisionCount = policyDecisions.length
  const checklistItemCount = completed ? 5 : 0
  const reviewableFindings = completed ? input.findingAssembly.evidenceCards : 0

  return {
    status: input.state,
    policyPackVersion: input.governanceConfig.activePolicyPack.version,
    organizationModelVersion: input.governanceConfig.organizationModel.version,
    supportRulesFingerprint: `sha256:${input.governanceConfig.activePolicyPack.version}_${input.governanceConfig.organizationModel.version}_${input.findingAssembly.assemblyRulesFingerprint}_${input.actorId}_review_support_${input.state}`,
    reviewableFindings,
    supportedFindings: reviewableFindings,
    allowedActionCount: completed ? input.permissionBoundary.allowedActions.length : 0,
    deniedActionCount: completed ? input.permissionBoundary.deniedActions.length : 0,
    availableDecisionCount: completed ? policyDecisions.length : 0,
    reasonRequiredDecisionCount: completed ? reasonRequiredDecisionCount : 0,
    checklistItemCount,
    transferOptionCount: completed ? input.governanceConfig.organizationModel.delegationTargets?.length ?? 0 : 0,
    escalationOptionCount: completed ? input.governanceConfig.activePolicyPack.escalationPaths?.length ?? 0 : 0,
    rawContentExposed: false,
    legalConclusionProvided: false,
    warnings: buildSummaryWarnings(input.state, input.findingAssembly),
  }
}

export function buildReviewSupport(input: ReviewSupportInput): ReviewSupport {
  const permissionBoundary = buildPermissionBoundary(input)
  const policyDecisions = getPolicyDecisions(input.governanceConfig)
  const findingActions = new Set(input.finding.availableActions ?? policyDecisions)
  const actorActions = new Set(permissionBoundary.allowedActions)
  const availableDecisions = isReviewableStatus(input.finding.status)
    ? policyDecisions
        .filter((decision) => findingActions.has(decision) && actorActions.has(decision))
        .map((decision) => ({
          decision,
          requiresReason: true,
          label: decisionLabels[decision],
        }))
    : []

  return {
    findingId: input.finding.findingId,
    actorId: input.actorId,
    policyPackVersion: input.governanceConfig.activePolicyPack.version,
    plainLanguageSummary: buildPlainLanguageSummary(input.finding, input.governanceConfig),
    availableDecisions,
    checklist: buildChecklist(input.finding),
    transferOptions: actorActions.has('reassign_owner') ? buildTransferOptions(input.governanceConfig, input.finding, input.workspaceMembers) : [],
    escalationOptions: actorActions.has('escalate') ? buildEscalationOptions(input.governanceConfig) : [],
    permissionBoundary,
  }
}

export function validateReviewInput(input: ReviewInput, reviewSupport: ReviewSupport): ValidationResult {
  const allowedDecisions = new Set(reviewSupport.availableDecisions.map((decision) => decision.decision))

  if (input.actorId !== reviewSupport.actorId) {
    return {
      accepted: false,
      reason: 'The review actor does not match the current permission boundary.',
    }
  }

  if (!allowedDecisions.has(input.decision)) {
    return {
      accepted: false,
      reason: `${decisionLabels[input.decision]} is outside the current permission boundary.`,
    }
  }

  if (!input.reason.trim()) {
    return {
      accepted: false,
      reason: 'A human review decision requires a recorded reason.',
    }
  }

  const missingChecklistItem = reviewSupport.checklist
    .filter((item) => item.required && (!item.decision || item.decision === input.decision))
    .find((item) => !(input.checklistItemIds ?? []).includes(item.itemId))

  if (missingChecklistItem) {
    return {
      accepted: false,
      reason: 'All required review checklist items must be acknowledged before submission.',
    }
  }

  if (input.decision === 'keep_with_reason' && !isValidDate(input.retentionUntil)) {
    return {
      accepted: false,
      reason: 'Retain decisions require a retention review date.',
    }
  }

  const transferTargetId = input.reassignToUserId ?? input.nextAction

  if (input.decision === 'reassign_owner' && !transferTargetId) {
    return {
      accepted: false,
      reason: 'Transfer decisions require a target owner.',
    }
  }

  if (
    input.decision === 'reassign_owner'
    && !reviewSupport.transferOptions?.some((option) => option.userId === transferTargetId)
  ) {
    return {
      accepted: false,
      reason: 'Transfer target is outside the current review support options.',
    }
  }

  if (input.decision === 'escalate' && !input.nextAction) {
    return {
      accepted: false,
      reason: 'Escalation decisions require an escalation queue.',
    }
  }

  if (
    input.decision === 'escalate'
    && !reviewSupport.escalationOptions?.some((option) => option.queueId === input.nextAction)
  ) {
    return {
      accepted: false,
      reason: 'Escalation queue is outside the current review support options.',
    }
  }

  return { accepted: true }
}

function getPolicyDecisions(governanceConfig: GovernanceConfig): ReviewDecision[] {
  return governanceConfig.activePolicyPack.reviewDecisions.filter(isP0ReviewDecision)
}

function isP0ReviewDecision(value: string): value is ReviewDecision {
  return p0ReviewDecisions.includes(value as ReviewDecision)
}

function isReviewableStatus(status: string): boolean {
  return status === 'open' || status === 'assigned' || status === 'under_review'
}

function isValidDate(value: string | null | undefined): value is string {
  return Boolean(value && /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(`${value}T00:00:00.000Z`)))
}

function buildPlainLanguageSummary(finding: Finding, governanceConfig: GovernanceConfig): string {
  const policyVersion = governanceConfig.activePolicyPack.version
  const riskLabel = finding.riskLevel.replaceAll('_', ' ')
  const ownerLabel = finding.owner?.displayName ?? 'the accountable owner'

  return `This ${riskLabel} finding is assigned to ${ownerLabel}. Use policy pack ${policyVersion} guidance, redacted evidence, owner context, and the visible permission boundary before recording a human decision. The system does not make a legal conclusion.`
}

function buildChecklist(finding: Finding): ReviewSupport['checklist'] {
  const checklist: ReviewSupport['checklist'] = [
    {
      itemId: 'review_redacted_evidence',
      label: 'Review the redacted evidence card and file anchor before deciding.',
      required: true,
    },
    {
      itemId: 'confirm_business_purpose',
      label: 'Confirm whether a current business purpose exists.',
      required: true,
    },
    {
      itemId: 'confirm_permission_boundary',
      label: 'Confirm the action is inside the displayed permission boundary.',
      required: true,
    },
  ]

  if (finding.retentionStatus === 'overdue' || finding.retentionStatus === 'review_required') {
    checklist.push({
      itemId: 'confirm_retention_context',
      label: 'Check retention context and any hold or exception before changing status.',
      required: true,
    })
  }

  if (finding.riskLevel === 'high' || finding.recommendedAction === 'escalate') {
    checklist.push({
      itemId: 'consider_escalation_path',
      label: 'Consider whether the DPO or Legal review path should handle this finding.',
      required: true,
    })
  }

  checklist.push({
    decision: 'delete_candidate',
    itemId: 'confirm_delete_candidate',
    label: 'Confirm this only marks the file as a deletion candidate and does not execute deletion.',
    required: true,
  })

  return checklist
}

function buildTransferOptions(governanceConfig: GovernanceConfig, finding: Finding, workspaceMembers?: WorkspaceMembership[]): ReviewSupport['transferOptions'] {
  const ownerId = finding.owner?.userId
  const activeWorkspaceTargets = (workspaceMembers ?? [])
    .filter((member) => member.status === 'active' && member.accountId !== ownerId && canReceiveReview(member))
    .map((member) => ({
      userId: member.accountId,
      displayName: member.displayName,
      reason: member.email ? `${member.email} · active Workspace member` : 'Active Workspace member',
    }))

  if (workspaceMembers !== undefined) {
    return activeWorkspaceTargets
  }

  return (governanceConfig.organizationModel.delegationTargets ?? [])
    .filter((target) => target.userId !== ownerId)
    .map((target) => ({
      userId: target.userId,
      displayName: target.displayName,
      reason: target.reason ?? 'Allowed by organization delegation rules.',
    }))
}

function canReceiveReview(member: WorkspaceMembership): boolean {
  return member.groupIds.some((groupId) => ['workspace_owner', 'privacy_reviewer', 'data_steward', 'dpo_legal'].includes(groupId))
}

function buildEscalationOptions(governanceConfig: GovernanceConfig): ReviewSupport['escalationOptions'] {
  return (governanceConfig.activePolicyPack.escalationPaths ?? []).map((path) => ({
    queueId: path.pathId ?? 'queue_dpo',
    label: path.label ?? 'Escalation queue',
  }))
}

function buildSummaryWarnings(state: ReviewSupportState, findingAssembly: FindingAssemblySummary): string[] {
  if (state === 'pending') {
    return ['Review support waits for completed finding assembly and permission-boundary calculation.']
  }

  if (findingAssembly.missingEvidenceCards > 0) {
    return [`${findingAssembly.missingEvidenceCards} findings cannot receive complete review support because evidence cards are missing.`]
  }

  return []
}
