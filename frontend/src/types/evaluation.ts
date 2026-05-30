export type ResourceIntensity = {
  peakMemoryMb?: number
  cpuSeconds?: number
  modelCalls?: number
  estimatedCostUsd?: number
  estimatedCostPerThousandFilesUsd?: number
  paidServiceUsed?: boolean
}

export type EvaluationConfusionMatrix = {
  truePositives: number
  falsePositives: number
  falseNegatives: number
  trueNegatives: number
  predictedPositiveFiles: number
  actualPositiveFiles: number
  evaluatedFiles: number
}

export type EvaluationScenarioMetric = {
  sourceFamily: string
  contextCategory?: string
  precision: number | null
  recall: number | null
  f1: number | null
  predictedPositiveFiles: number
  actualPositiveFiles: number
  truePositives: number
  falsePositives: number
  falseNegatives: number
  unsupportedFiles?: number
  ocrDeferredFiles?: number
}

export type EvaluationQualityBasis = {
  status: string
  datasetId: string
  goldenDatasetVersion: string
  sourceSnapshotId?: string
  evaluationRulesHash: string
  inputStages: string[]
  confusionMatrix: EvaluationConfusionMatrix
  scenarioMetrics: EvaluationScenarioMetric[]
  review: {
    reviewDecisionCount: number
    falsePositiveCorrections: number
    openReviewBacklog: number
    reviewThroughputPerDay?: number
    ownerTaskCompletionRate?: number
  }
  riskReduction: {
    basis: string
    baselineHighRiskFindings: number
    reviewedHighRiskFindings: number
    remainingHighRiskFindings: number
    riskReductionRate: number
    deletionExecuted: boolean
  }
  safetyBoundaries: {
    rawContentExposed: boolean
    legalConclusionProvided: boolean
    deletionExecuted: boolean
    modelCalls: number
    estimatedCostUsd: number
  }
  warnings: string[]
}

export type EvaluationSummary = {
  evaluationRunId?: string
  scanId?: string
  datasetHash?: string
  scannerVersion?: string
  detectorRulesHash?: string
  signalDetectionRulesHash?: string
  contextRiskRulesHash?: string
  ownerAssignmentRulesHash?: string
  findingAssemblyRulesHash?: string
  reviewSupportRulesHash?: string
  auditRecordingRulesHash?: string
  adminMetricsRulesHash?: string
  reviewDecisionRulesHash?: string
  deltaScanRulesHash?: string
  evaluationRulesHash?: string
  configHash?: string
  findingFingerprint?: string
  precision?: number | null
  recall?: number | null
  f1?: number | null
  reproducibility?: number | null
  throughputFilesPerSecond?: number | null
  resourceIntensity?: ResourceIntensity
  qualityBasis?: EvaluationQualityBasis
}

export type AdminMetricsAggregationSummary = {
  status: string
  scanId?: string
  scanType?: string
  sourceId?: string
  policyPackVersion?: string
  rulesFingerprint: string
  inputStages: string[]
  partial: boolean
  scanCoverage: {
    scannedFiles: number
    candidateFiles: number
    flaggedFiles: number
    scanProgress: number
    scannedGb?: number
    scanTimeSeconds?: number | null
    throughputFilesPerSecond?: number | null
  }
  risk: {
    riskAssessedFindings: number
    highRiskFindings: number
    retentionReviewFiles: number
    humanReviewRequiredFindings: number
  }
  ownerBacklog: {
    openReviewBacklog: number
    reviewableFindings: number
    reviewDecisionCount: number
    ownerTaskCompletionRate: number
    reviewThroughputPerDay?: number
    medianReviewTimeHours?: number | null
  }
  outcomes: {
    deletionCandidateDecisions: number
    retainedDecisions: number
    falsePositiveDecisions: number
    reassignedDecisions: number
    escalatedDecisions: number
  }
  audit: {
    recordedEvents: number
    linkedFindingEvents: number
    reviewDecisionEvents: number
  }
  delta?: {
    baselineFiles: number
    changedFiles: number
    processedChangedFiles: number
    carriedForwardFindings: number
    missingFiles: number
    missingFilesTreatedAsDeleted: boolean
  }
  evaluationLinked: boolean
  rawContentExposed: boolean
  legalConclusionProvided: boolean
  deletionExecuted: boolean
  modelCalls: number
  estimatedCostUsd: number
  warnings: string[]
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
  detectedSignals?: number
  redactedSignals?: number
  findingsWithSignals?: number
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
  deltaBaselineFiles?: number
  deltaChangedFiles?: number
  deltaNewFiles?: number
  deltaModifiedFiles?: number
  deltaUnchangedFiles?: number
  deltaMissingFiles?: number
  deltaProcessedChangedFiles?: number
  deltaReopenedFindings?: number
  deltaCarriedForwardFindings?: number
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
  aggregation?: AdminMetricsAggregationSummary
  governance?: {
    activePolicyPackVersion?: string
    openTransferRequests?: number
    pendingPolicyChangePreviews?: number
  }
}
