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
  contextRiskRulesHash?: string
  ownerAssignmentRulesHash?: string
  findingAssemblyRulesHash?: string
  reviewSupportRulesHash?: string
  auditRecordingRulesHash?: string
  reviewDecisionRulesHash?: string
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
  inventoryCandidateFiles?: number
  fingerprintedFiles?: number
  extractedFiles?: number
  extractionWarnings?: number
  redactedEvidenceCandidates?: number
  contextClassifiedFindings?: number
  riskAssessedFindings?: number
  humanReviewRequiredFindings?: number
  ownerRoutedFindings?: number
  assignedFindings?: number
  directOwnerAssignments?: number
  masterOfDataAssignments?: number
  escalationAssignments?: number
  assembledFindings?: number
  evidenceCards?: number
  reviewSupportedFindings?: number
  deniedReviewActions?: number
  reviewChecklistItems?: number
  reviewTransferOptions?: number
  reviewEscalationOptions?: number
  auditRecordedEvents?: number
  auditLinkedFindingEvents?: number
  auditReviewDecisionEvents?: number
  reviewDecisionCount?: number
  deletionCandidateDecisions?: number
  retainedDecisions?: number
  falsePositiveDecisions?: number
  reassignedDecisions?: number
  escalatedDecisions?: number
  reviewThroughputPerDay?: number
  medianReviewTimeHours?: number | null
  findingsBySource?: Record<string, number>
  evaluation?: EvaluationSummary
  governance?: {
    activePolicyPackVersion?: string
    openTransferRequests?: number
    pendingPolicyChangePreviews?: number
  }
}
