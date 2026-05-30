export type Scan = {
  scanId: string
  sourceId: string
  scanType: string
  status: string
  stage?: string
  progress: number
  totalFiles?: number
  scannedFiles?: number
  flaggedFiles?: number
  totalBytes?: number
  durationMs?: number | null
  throughputFilesPerSecond?: number | null
  reproducibilityFingerprint?: string | null
  pipelineStages?: ScanPipelineStage[]
  fileInventory?: FileInventorySummary
  contentExtraction?: ContentExtractionSummary
  contextRisk?: ContextRiskSummary
  ownerAssignment?: OwnerAssignmentSummary
  findingAssembly?: FindingAssemblySummary
  reviewSupport?: ReviewSupportSummary
  auditRecording?: AuditRecordingSummary
}

export type ScanPipelineStage = {
  stage: string
  status: string
  processedFiles?: number
  totalFiles?: number
  warnings?: string[]
}

export type FileInventoryFamily = {
  family: string
  candidateFiles: number
  processedFiles?: number
  flaggedFiles?: number
  bytes?: number
}

export type FileInventorySummary = {
  status: string
  sourceSnapshotId: string
  inventoryFingerprint: string
  totalCandidateFiles: number
  fingerprintedFiles: number
  skippedFiles: number
  totalBytes: number
  permissionSnapshots: number
  sampleFamilies: FileInventoryFamily[]
  warnings: string[]
}

export type ContentExtractionMethod = {
  method: string
  files: number
  status?: string
}

export type ContentExtractionSummary = {
  status: string
  extractionFingerprint: string
  processedFiles: number
  successfulFiles: number
  warningFiles: number
  unsupportedFiles: number
  ocrDeferredFiles: number
  redactedEvidenceCandidates: number
  rawContentExposed: boolean
  methods: ContentExtractionMethod[]
  warnings: string[]
}

export type ContextCategorySummary = {
  contextCategory: string
  sourceFamily?: string
  flaggedFiles: number
  evidenceCandidates: number
  riskGuidance?: string
  retentionRuleApplied?: boolean
}

export type ContextRiskSummary = {
  status: string
  policyPackVersion: string
  riskRulesFingerprint: string
  assessedEvidenceCandidates: number
  contextClassifiedFindings: number
  riskAssessedFindings: number
  highRiskFindings: number
  mediumRiskFindings: number
  lowRiskFindings: number
  retentionReviewFiles: number
  humanReviewRequiredFindings: number
  legalConclusionProvided: boolean
  contextCategories: ContextCategorySummary[]
  warnings: string[]
}

export type OwnerAssignmentSummary = {
  status: string
  policyPackVersion: string
  organizationModelVersion: string
  ownerResolutionStrategy: string
  assignmentRulesFingerprint: string
  humanReviewRequiredFindings: number
  assignedFindings: number
  directOwnerAssignments: number
  masterOfDataAssignments: number
  escalationAssignments: number
  unownedFindings: number
  transferOptionCount: number
  escalationOptionCount: number
  sourceOwnerAvailable: boolean
  warnings: string[]
}

export type FindingAssemblySummary = {
  status: string
  policyPackVersion: string
  sourceSnapshotId: string
  assemblyRulesFingerprint: string
  assembledFindings: number
  evidenceCards: number
  evidenceSignals: number
  redactedEvidenceSnippets: number
  missingEvidenceCards: number
  deniedActionCount: number
  rawContentExposed: boolean
  legalConclusionProvided: boolean
  warnings: string[]
}

export type ReviewSupportSummary = {
  status: string
  policyPackVersion: string
  organizationModelVersion: string
  supportRulesFingerprint: string
  reviewableFindings: number
  supportedFindings: number
  allowedActionCount: number
  deniedActionCount: number
  availableDecisionCount: number
  reasonRequiredDecisionCount: number
  checklistItemCount: number
  transferOptionCount: number
  escalationOptionCount: number
  rawContentExposed: boolean
  legalConclusionProvided: boolean
  warnings: string[]
}

export type AuditRecordingSummary = {
  status: string
  policyPackVersion: string
  auditRulesFingerprint: string
  recordedEventCount: number
  linkedScanEvents: number
  linkedFindingEvents: number
  reviewDecisionEvents: number
  systemEvents: number
  humanEvents: number
  rawContentExposed: boolean
  legalConclusionProvided: boolean
  deletionExecuted: boolean
  warnings: string[]
}
