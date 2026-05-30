export type PolicyPack = {
  policyPackId: string
  version: string
  status: string
  jurisdictionTags?: string[]
  effectiveFrom: string
  effectiveTo?: string | null
  retentionRules?: {
    ruleId?: string
    documentCategory?: string
    reviewAfterDays?: number
    guidance?: string
  }[]
  riskGuidance?: {
    guidanceId?: string
    contextCategory?: string
    signalTypes?: string[]
    riskLevel?: string
    scoreFloor?: number
    reviewReason?: string
  }[]
  evidenceRequirements?: string[]
  escalationPaths?: {
    pathId?: string
    label?: string
  }[]
  reviewDecisions: string[]
}

export type OrganizationModel = {
  organizationModelId: string
  version: string
  ownerResolutionStrategy: string
  orgUnits?: {
    orgUnitId?: string
    displayName?: string
    masterOfDataUserId?: string
  }[]
  delegationRules?: {
    ruleId?: string
    description?: string
  }[]
  delegationTargets?: {
    userId: string
    displayName: string
    orgUnitId?: string
    reason?: string
  }[]
}

export type GovernanceConfig = {
  configId: string
  activePolicyPack: PolicyPack
  organizationModel: OrganizationModel
  sourceAdapters: {
    sourceType?: string
    label?: string
    status?: string
    referenceUrl?: string
  }[]
  changeControls?: {
    policyChangesRequirePreview?: boolean
    orgChangesRequireAuditEvent?: boolean
    realDeletionAllowed?: boolean
  }
}
