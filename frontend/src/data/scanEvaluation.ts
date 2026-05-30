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
  Scan,
  SignalDetectionSummary,
} from '../types'
import { buildAdminMetricsRulesFingerprint } from './adminMetricsAggregation'
import {
  buildEvaluationQuality,
  buildEvaluationResourceIntensity,
  calculateEvaluationF1,
  calculateEvaluationRatio,
  getGoldenDatasetHash,
  refreshReviewQuality,
  type EvaluationMetricInput,
} from './evaluationQuality'

type UpdateEvaluationInput = EvaluationMetricInput & {
  current: EvaluationSummary
}

export function updateEvaluation(input: UpdateEvaluationInput): EvaluationSummary {
  const adminMetricsRulesHash = buildAdminMetricsHash(input)
  const qualityBasis = buildEvaluationQuality(input, adminMetricsRulesHash)
  const precision = calculateEvaluationRatio(
    qualityBasis.confusionMatrix.truePositives,
    qualityBasis.confusionMatrix.predictedPositiveFiles,
  )
  const recall = calculateEvaluationRatio(
    qualityBasis.confusionMatrix.truePositives,
    qualityBasis.confusionMatrix.actualPositiveFiles,
  )

  return {
    ...input.current,
    scanId: input.completedScan.scanId,
    datasetHash: input.current.datasetHash ?? getGoldenDatasetHash(),
    configHash: input.fileInventory.inventoryFingerprint,
    detectorRulesHash: input.signalDetection.detectorRulesHash,
    signalDetectionRulesHash: input.signalDetection.detectorRulesHash,
    contextRiskRulesHash: input.contextRisk.riskRulesFingerprint,
    ownerAssignmentRulesHash: input.ownerAssignment.assignmentRulesFingerprint,
    findingAssemblyRulesHash: input.findingAssembly.assemblyRulesFingerprint,
    reviewSupportRulesHash: input.reviewSupport.supportRulesFingerprint,
    auditRecordingRulesHash: input.auditRecording.auditRulesFingerprint,
    adminMetricsRulesHash,
    deltaScanRulesHash: input.deltaScan?.deltaFingerprint ?? input.current.deltaScanRulesHash,
    evaluationRulesHash: qualityBasis.evaluationRulesHash,
    findingFingerprint: input.completedScan.reproducibilityFingerprint ?? input.current.findingFingerprint,
    precision,
    recall,
    f1: calculateEvaluationF1(precision, recall),
    reproducibility: 1,
    throughputFilesPerSecond: input.completedScan.throughputFilesPerSecond,
    resourceIntensity: buildEvaluationResourceIntensity(input),
    qualityBasis,
  }
}

export function refreshEvaluationReviewContext(
  evaluation: EvaluationSummary,
  metrics: AdminMetrics,
): EvaluationSummary {
  if (!evaluation.qualityBasis) {
    return evaluation
  }

  return {
    ...evaluation,
    qualityBasis: refreshReviewQuality(evaluation.qualityBasis, metrics),
    resourceIntensity: {
      ...evaluation.resourceIntensity,
      modelCalls: 0,
      estimatedCostUsd: 0,
      estimatedCostPerThousandFilesUsd: 0,
      paidServiceUsed: false,
    },
  }
}

function buildAdminMetricsHash(input: {
  auditRecording: AuditRecordingSummary
  completedScan: Scan
  contentExtraction: ContentExtractionSummary
  contextRisk: ContextRiskSummary
  deltaScan?: DeltaScanSummary
  fileInventory: FileInventorySummary
  findingAssembly: FindingAssemblySummary
  ownerAssignment: OwnerAssignmentSummary
  reviewSupport: ReviewSupportSummary
  signalDetection: SignalDetectionSummary
}): string {
  return buildAdminMetricsRulesFingerprint({
    auditRecording: input.auditRecording,
    contentExtraction: input.contentExtraction,
    contextRisk: input.contextRisk,
    deltaScan: input.deltaScan,
    fileInventory: input.fileInventory,
    findingAssembly: input.findingAssembly,
    ownerAssignment: input.ownerAssignment,
    reviewSupport: input.reviewSupport,
    signalDetection: input.signalDetection,
    scanId: input.completedScan.scanId,
    scanType: input.completedScan.scanType,
    state: 'completed',
  })
}
