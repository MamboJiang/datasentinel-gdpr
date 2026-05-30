import type {
  AuditRecordingSummary,
  ContentExtractionSummary,
  ContextRiskSummary,
  EvaluationSummary,
  FindingAssemblySummary,
  FileInventorySummary,
  OwnerAssignmentSummary,
  ReviewSupportSummary,
  Scan,
} from '../types'

export function updateEvaluation(
  current: EvaluationSummary,
  completedScan: Scan,
  fileInventory: FileInventorySummary,
  contentExtraction: ContentExtractionSummary,
  contextRisk: ContextRiskSummary,
  ownerAssignment: OwnerAssignmentSummary,
  findingAssembly: FindingAssemblySummary,
  reviewSupport: ReviewSupportSummary,
  auditRecording: AuditRecordingSummary,
): EvaluationSummary {
  return {
    ...current,
    scanId: completedScan.scanId,
    configHash: fileInventory.inventoryFingerprint,
    detectorRulesHash: contentExtraction.extractionFingerprint,
    contextRiskRulesHash: contextRisk.riskRulesFingerprint,
    ownerAssignmentRulesHash: ownerAssignment.assignmentRulesFingerprint,
    findingAssemblyRulesHash: findingAssembly.assemblyRulesFingerprint,
    reviewSupportRulesHash: reviewSupport.supportRulesFingerprint,
    auditRecordingRulesHash: auditRecording.auditRulesFingerprint,
    findingFingerprint: completedScan.reproducibilityFingerprint ?? current.findingFingerprint,
    reproducibility: 1,
    throughputFilesPerSecond: completedScan.throughputFilesPerSecond,
    resourceIntensity: {
      ...current.resourceIntensity,
      modelCalls: 0,
      estimatedCostUsd: 0,
    },
  }
}
