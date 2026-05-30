import type {
  AdminMetrics,
  AuditRecordingSummary,
  ContentExtractionSummary,
  ContextRiskSummary,
  DeltaScanSummary,
  EvaluationSummary,
  FindingAssemblySummary,
  FileInventorySummary,
  OwnerAssignmentSummary,
  ReviewSupportSummary,
  SignalDetectionSummary,
} from '../types'
import type { ScanProfile } from './scanProfiles'
import { buildAdminMetricsAggregation } from './adminMetricsAggregation'
import { calculateScannedGb } from './scanWorkflowUtils'

type RunningMetricsInput = {
  auditRecording: AuditRecordingSummary
  contentExtraction: ContentExtractionSummary
  contextRisk: ContextRiskSummary
  currentMetrics: AdminMetrics
  deltaScan?: DeltaScanSummary
  fileInventory: FileInventorySummary
  findingAssembly: FindingAssemblySummary
  ownerAssignment: OwnerAssignmentSummary
  profile: ScanProfile
  reviewSupport: ReviewSupportSummary
  signalDetection: SignalDetectionSummary
}

type CompletedMetricsInput = RunningMetricsInput & {
  evaluation: EvaluationSummary
}

export function buildRunningScanMetrics(input: RunningMetricsInput): AdminMetrics {
  const scannedGb = calculateScannedGb(input.profile.totalBytes, input.profile.progress)

  return {
    ...input.currentMetrics,
    ...buildSharedMetrics(input),
    totalScannedFiles: input.profile.scannedFiles,
    flaggedFiles: input.profile.flaggedFiles,
    totalScannedGb: scannedGb,
    scanProgress: input.profile.progress,
    lastScanTimeSeconds: null,
    aggregation: buildAdminMetricsAggregation({
      ...input,
      flaggedFiles: input.profile.flaggedFiles,
      lastScanTimeSeconds: null,
      scannedFiles: input.profile.scannedFiles,
      scannedGb,
      scanId: input.profile.scanId,
      scanProgress: input.profile.progress,
      scanType: input.profile.scanType,
      sourceId: getSourceId(input.fileInventory.sourceSnapshotId),
      state: 'running',
      throughputFilesPerSecond: null,
    }),
  }
}

export function buildCompletedScanMetrics(input: CompletedMetricsInput): AdminMetrics {
  const scannedGb = calculateScannedGb(input.profile.totalBytes, 1)

  return {
    ...input.currentMetrics,
    ...buildSharedMetrics(input),
    totalScannedFiles: input.profile.totalFiles,
    flaggedFiles: input.profile.completedFlaggedFiles,
    totalScannedGb: scannedGb,
    scanProgress: 1,
    lastScanTimeSeconds: input.profile.durationMs / 1000,
    highRiskFindings: input.contextRisk.highRiskFindings,
    retentionOverdueFiles: input.contextRisk.retentionReviewFiles,
    evaluation: input.evaluation,
    aggregation: buildAdminMetricsAggregation({
      ...input,
      evaluation: input.evaluation,
      flaggedFiles: input.profile.completedFlaggedFiles,
      lastScanTimeSeconds: input.profile.durationMs / 1000,
      scannedFiles: input.profile.totalFiles,
      scannedGb,
      scanId: input.profile.scanId,
      scanProgress: 1,
      scanType: input.profile.scanType,
      sourceId: getSourceId(input.fileInventory.sourceSnapshotId),
      state: 'completed',
      throughputFilesPerSecond: input.profile.throughputFilesPerSecond,
    }),
  }
}

function buildSharedMetrics(input: RunningMetricsInput): Partial<AdminMetrics> {
  return {
    inventoryCandidateFiles: input.fileInventory.totalCandidateFiles,
    fingerprintedFiles: input.fileInventory.fingerprintedFiles,
    extractedFiles: input.contentExtraction.successfulFiles,
    extractionWarnings: input.contentExtraction.warningFiles,
    redactedEvidenceCandidates: input.contentExtraction.redactedEvidenceCandidates,
    detectedSignals: input.signalDetection.detectedSignals,
    redactedSignals: input.signalDetection.redactedSignals,
    findingsWithSignals: input.signalDetection.findingsWithSignals,
    contextClassifiedFindings: input.contextRisk.contextClassifiedFindings,
    riskAssessedFindings: input.contextRisk.riskAssessedFindings,
    humanReviewRequiredFindings: input.contextRisk.humanReviewRequiredFindings,
    ownerRoutedFindings: input.ownerAssignment.assignedFindings,
    assignedFindings: input.ownerAssignment.assignedFindings,
    directOwnerAssignments: input.ownerAssignment.directOwnerAssignments,
    masterOfDataAssignments: input.ownerAssignment.masterOfDataAssignments,
    escalationAssignments: input.ownerAssignment.escalationAssignments,
    assembledFindings: input.findingAssembly.assembledFindings,
    evidenceCards: input.findingAssembly.evidenceCards,
    reviewSupportedFindings: input.reviewSupport.supportedFindings,
    deniedReviewActions: input.reviewSupport.deniedActionCount,
    reviewChecklistItems: input.reviewSupport.checklistItemCount,
    reviewTransferOptions: input.reviewSupport.transferOptionCount,
    reviewEscalationOptions: input.reviewSupport.escalationOptionCount,
    auditRecordedEvents: input.auditRecording.recordedEventCount,
    auditLinkedFindingEvents: input.auditRecording.linkedFindingEvents,
    auditReviewDecisionEvents: input.auditRecording.reviewDecisionEvents,
    ...buildDeltaMetrics(input.deltaScan),
  }
}

function buildDeltaMetrics(deltaScan: DeltaScanSummary | undefined): Partial<AdminMetrics> {
  if (!deltaScan) {
    return {}
  }

  return {
    deltaBaselineFiles: deltaScan.baselineTotalFiles,
    deltaChangedFiles: deltaScan.changedFiles,
    deltaNewFiles: deltaScan.newFiles,
    deltaModifiedFiles: deltaScan.modifiedFiles,
    deltaUnchangedFiles: deltaScan.unchangedFiles,
    deltaMissingFiles: deltaScan.missingFiles,
    deltaProcessedChangedFiles: deltaScan.processedChangedFiles,
    deltaReopenedFindings: deltaScan.reopenedFindings,
    deltaCarriedForwardFindings: deltaScan.unchangedFindingsCarriedForward,
  }
}

function getSourceId(sourceSnapshotId: string): string {
  const match = /^snapshot_(.+)_scan/.exec(sourceSnapshotId)

  return match?.[1] ?? 'unknown'
}
