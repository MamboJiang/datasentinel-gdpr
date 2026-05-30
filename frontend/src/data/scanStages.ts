import type {
  ContentExtractionSummary,
  ContextRiskSummary,
  AuditRecordingSummary,
  DeltaScanSummary,
  EvaluationSummary,
  FindingAssemblySummary,
  FileInventorySummary,
  OwnerAssignmentSummary,
  ReviewSupportSummary,
  SignalDetectionSummary,
  ScanPipelineStage,
} from '../types'

export function createPipelineStages(
  fileInventory: FileInventorySummary,
  contentExtraction: ContentExtractionSummary,
  signalDetection: SignalDetectionSummary,
  contextRisk: ContextRiskSummary,
  ownerAssignment: OwnerAssignmentSummary,
  findingAssembly: FindingAssemblySummary,
  reviewSupport: ReviewSupportSummary,
  auditRecording: AuditRecordingSummary,
  completed: boolean,
  deltaScan?: DeltaScanSummary,
  evaluation?: EvaluationSummary,
): ScanPipelineStage[] {
  const stages: ScanPipelineStage[] = [
    {
      stage: 'source_ready',
      status: 'completed',
    },
    {
      stage: 'inventorying_files',
      status: completed ? 'completed' : 'running',
      processedFiles: fileInventory.fingerprintedFiles,
      totalFiles: fileInventory.totalCandidateFiles,
      warnings: fileInventory.warnings,
    },
    {
      stage: 'extracting_content',
      status: contentExtraction.warningFiles > 0 && !completed ? 'warning' : contentExtraction.status,
      processedFiles: contentExtraction.processedFiles,
      totalFiles: fileInventory.totalCandidateFiles,
      warnings: contentExtraction.warnings,
    },
    {
      stage: 'detecting_signals',
      status: signalDetection.status,
      processedFiles: signalDetection.redactedSignals,
      totalFiles: completed ? signalDetection.evaluatedEvidenceCandidates : undefined,
      warnings: signalDetection.warnings,
    },
    {
      stage: 'judging_context_risk',
      status: contextRisk.status,
      processedFiles: contextRisk.riskAssessedFindings,
      totalFiles: completed ? contentExtraction.redactedEvidenceCandidates : undefined,
      warnings: contextRisk.warnings,
    },
    {
      stage: 'assigning_owner',
      status: ownerAssignment.status,
      processedFiles: ownerAssignment.assignedFindings,
      totalFiles: completed ? contextRisk.humanReviewRequiredFindings : undefined,
      warnings: ownerAssignment.warnings,
    },
    {
      stage: 'assembling_findings',
      status: findingAssembly.status,
      processedFiles: findingAssembly.assembledFindings,
      totalFiles: completed ? ownerAssignment.assignedFindings : undefined,
      warnings: findingAssembly.warnings,
    },
    {
      stage: 'preparing_review_support',
      status: reviewSupport.status,
      processedFiles: reviewSupport.supportedFindings,
      totalFiles: completed ? findingAssembly.evidenceCards : undefined,
      warnings: reviewSupport.warnings,
    },
    {
      stage: 'recording_audit_events',
      status: auditRecording.status,
      processedFiles: auditRecording.recordedEventCount,
      totalFiles: completed ? auditRecording.recordedEventCount : undefined,
      warnings: auditRecording.warnings,
    },
    {
      stage: 'generating_evaluation_metrics',
      status: completed ? evaluation?.qualityBasis?.status ?? 'computed' : 'pending',
      processedFiles: completed ? evaluation?.qualityBasis?.confusionMatrix.evaluatedFiles : 0,
      totalFiles: completed ? fileInventory.totalCandidateFiles : undefined,
      warnings: evaluation?.qualityBasis?.warnings ?? [],
    },
  ]

  if (!deltaScan) {
    return stages
  }

  return [
    stages[0],
    {
      stage: 'comparing_delta_baseline',
      status: deltaScan.status,
      processedFiles: deltaScan.processedChangedFiles,
      totalFiles: deltaScan.changedFiles,
      warnings: deltaScan.warnings,
    },
    ...stages.slice(1),
  ]
}
