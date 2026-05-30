export type Meta = {
  contractVersion: string
  generatedAt: string
  traceId: string
  partial: boolean
  warnings: string[]
}

export type Source = {
  sourceId: string
  name: string
  sourceType: string
  status: string
  rootLabel?: string | null
  masterOfDataUserId?: string | null
}

export type Scan = {
  scanId: string
  sourceId: string
  scanType: string
  status: string
  progress: number
  totalFiles?: number
  scannedFiles?: number
  flaggedFiles?: number
  totalBytes?: number
  durationMs?: number | null
  throughputFilesPerSecond?: number | null
  reproducibilityFingerprint?: string | null
}

export type Owner = {
  userId: string
  displayName: string
  email?: string | null
  assignmentType: string
}

export type Signal = {
  type: string
  detector: string
  confidence: number
  snippet: string
  page?: number | null
}

export type AuditEvent = {
  auditEventId: string
  scanId?: string | null
  findingId?: string | null
  eventType: string
  actorId: string
  occurredAt: string
  summary?: string
  reason?: string
  resultingStatus?: string
}

export type FindingSummary = {
  findingId: string
  scanId?: string
  fileName: string
  sourcePath?: string
  riskLevel: string
  riskScore: number
  contextCategory?: string
  personalDataTypes?: string[]
  retentionStatus?: string
  recommendedAction?: string
  status: string
  owner?: Owner | null
}

export type Finding = FindingSummary & {
  file?: {
    sourceName?: string
    sourceType?: string
    lastModifiedAt?: string
    sizeBytes?: number
  }
  signals?: Signal[]
  riskExplanation?: string
  policyContext?: {
    policyPackId?: string
    policyPackVersion?: string
    policyConclusion?: string
  }
  availableActions?: string[]
  deniedActions?: DeniedAction[]
  auditTimeline?: AuditEvent[]
}

export type ResourceIntensity = {
  peakMemoryMb?: number
  cpuSeconds?: number
  modelCalls?: number
  estimatedCostUsd?: number
}

export type EvaluationSummary = {
  evaluationRunId?: string
  scanId?: string
  datasetHash?: string
  scannerVersion?: string
  detectorRulesHash?: string
  configHash?: string
  findingFingerprint?: string
  precision?: number | null
  recall?: number | null
  f1?: number | null
  reproducibility?: number | null
  throughputFilesPerSecond?: number | null
  resourceIntensity?: ResourceIntensity
}

export type AdminMetrics = {
  totalScannedFiles: number
  flaggedFiles: number
  totalScannedGb?: number
  scanProgress: number
  lastScanTimeSeconds?: number | null
  openReviewBacklog: number
  highRiskFindings?: number
  retentionOverdueFiles?: number
  findingsBySource?: Record<string, number>
  evaluation?: EvaluationSummary
  governance?: {
    activePolicyPackVersion?: string
    openTransferRequests?: number
    pendingPolicyChangePreviews?: number
  }
}

export type ReviewDecision =
  | 'delete_candidate'
  | 'keep_with_reason'
  | 'correct_false_positive'
  | 'reassign_owner'
  | 'escalate'

export type ReviewInput = {
  findingId: string
  decision: ReviewDecision
  reason: string
  actorId: string
  reassignToUserId?: string
  nextAction?: string
}

export type DeniedAction = {
  action: string
  reason: string
}

export type PermissionBoundary = {
  actorId: string
  roles: string[]
  allowedActions: string[]
  deniedActions: DeniedAction[]
  visibleScopes: string[]
}

export type ReviewSupport = {
  findingId: string
  actorId: string
  policyPackVersion: string
  plainLanguageSummary?: string
  availableDecisions: {
    decision: ReviewDecision
    requiresReason?: boolean
    label?: string
  }[]
  checklist: {
    itemId: string
    label: string
    required?: boolean
  }[]
  transferOptions?: {
    userId: string
    displayName: string
    reason?: string
  }[]
  escalationOptions?: {
    queueId: string
    label: string
  }[]
  permissionBoundary?: PermissionBoundary
}

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
