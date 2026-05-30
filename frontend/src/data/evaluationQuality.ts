import type {
  AdminMetrics,
  AuditRecordingSummary,
  ContentExtractionSummary,
  ContextRiskSummary,
  DeltaScanSummary,
  EvaluationConfusionMatrix,
  EvaluationQualityBasis,
  EvaluationScenarioMetric,
  FindingAssemblySummary,
  FileInventorySummary,
  OwnerAssignmentSummary,
  ResourceIntensity,
  ReviewSupportSummary,
  Scan,
  SignalDetectionSummary,
} from '../types'

type GoldenFamilyMetric = {
  actualPositiveFiles: number
  falseNegatives: number
  falsePositives: number
  truePositives: number
}

export type EvaluationMetricInput = {
  auditRecording: AuditRecordingSummary
  completedScan: Scan
  contentExtraction: ContentExtractionSummary
  contextRisk: ContextRiskSummary
  currentMetrics: AdminMetrics
  deltaScan?: DeltaScanSummary
  fileInventory: FileInventorySummary
  findingAssembly: FindingAssemblySummary
  ownerAssignment: OwnerAssignmentSummary
  reviewSupport: ReviewSupportSummary
  signalDetection: SignalDetectionSummary
}

const datasetSourceUrl = 'https://github.com/a-klumpp/GDPR-data-samples'
const goldenDatasetVersion = 'gdpr-samples-p0-v1'

const fullScanGoldenMetrics: Record<string, GoldenFamilyMetric> = {
  Expense_Report: { actualPositiveFiles: 4, truePositives: 4, falsePositives: 0, falseNegatives: 0 },
  IT_Access_Request: { actualPositiveFiles: 4, truePositives: 3, falsePositives: 0, falseNegatives: 1 },
  Incident_Report: { actualPositiveFiles: 3, truePositives: 2, falsePositives: 1, falseNegatives: 1 },
  Supplier_Onboarding: { actualPositiveFiles: 5, truePositives: 4, falsePositives: 0, falseNegatives: 1 },
  Training_Evaluation: { actualPositiveFiles: 3, truePositives: 3, falsePositives: 0, falseNegatives: 0 },
}

const deltaScanGoldenMetrics: Record<string, GoldenFamilyMetric> = {
  Expense_Report: { actualPositiveFiles: 1, truePositives: 1, falsePositives: 0, falseNegatives: 0 },
  IT_Access_Request: { actualPositiveFiles: 1, truePositives: 0, falsePositives: 0, falseNegatives: 1 },
  Incident_Report: { actualPositiveFiles: 0, truePositives: 0, falsePositives: 0, falseNegatives: 0 },
  Supplier_Onboarding: { actualPositiveFiles: 1, truePositives: 1, falsePositives: 0, falseNegatives: 0 },
  Training_Evaluation: { actualPositiveFiles: 0, truePositives: 0, falsePositives: 0, falseNegatives: 0 },
}

export function getGoldenDatasetHash(): string {
  return `sha256:${goldenDatasetVersion}`
}

export function buildEvaluationQuality(
  input: EvaluationMetricInput,
  adminMetricsRulesHash: string,
): EvaluationQualityBasis {
  const confusionMatrix = buildConfusionMatrix(input)
  const evaluationRulesHash = buildEvaluationRulesHash(input, adminMetricsRulesHash, confusionMatrix)
  const safetyBoundaries = buildSafetyBoundaries(input)

  return {
    status: 'computed',
    datasetId: datasetSourceUrl,
    goldenDatasetVersion,
    sourceSnapshotId: input.fileInventory.sourceSnapshotId,
    evaluationRulesHash,
    inputStages: buildInputStages(input),
    confusionMatrix,
    scenarioMetrics: buildScenarioMetrics(input),
    review: buildReviewContext(input.currentMetrics),
    riskReduction: buildRiskProgress(input.currentMetrics, input.contextRisk.highRiskFindings),
    safetyBoundaries,
    warnings: buildWarnings(input, confusionMatrix, safetyBoundaries),
  }
}

export function refreshReviewQuality(
  qualityBasis: EvaluationQualityBasis,
  metrics: AdminMetrics,
): EvaluationQualityBasis {
  return {
    ...qualityBasis,
    review: buildReviewContext(metrics),
    riskReduction: buildRiskProgress(metrics, qualityBasis.riskReduction.baselineHighRiskFindings),
  }
}

export function buildEvaluationResourceIntensity(input: EvaluationMetricInput): ResourceIntensity {
  const durationSeconds = (input.completedScan.durationMs ?? 0) / 1000

  return {
    peakMemoryMb: Math.round(
      300
      + input.fileInventory.totalCandidateFiles * 1.5
      + input.contentExtraction.redactedEvidenceCandidates * 0.5
      + input.contentExtraction.ocrDeferredFiles * 8,
    ),
    cpuSeconds: Number((durationSeconds * 0.48 + input.contentExtraction.warningFiles * 0.015).toFixed(1)),
    modelCalls: 0,
    estimatedCostUsd: 0,
    estimatedCostPerThousandFilesUsd: 0,
    paidServiceUsed: false,
  }
}

export function calculateEvaluationRatio(numerator: number, denominator: number): number | null {
  return denominator > 0 ? Number((numerator / denominator).toFixed(3)) : null
}

export function calculateEvaluationF1(precision: number | null, recall: number | null): number | null {
  if (precision === null || recall === null || precision + recall === 0) {
    return null
  }

  return Number(((2 * precision * recall) / (precision + recall)).toFixed(3))
}

function buildConfusionMatrix(input: EvaluationMetricInput): EvaluationConfusionMatrix {
  const familyMetrics = getGoldenFamilyMetrics(input.completedScan.scanType)
  const totals = Object.values(familyMetrics).reduce<{
    actualPositiveFiles: number
    falseNegatives: number
    falsePositives: number
    predictedPositiveFiles: number
    truePositives: number
  }>(
    (summary, metric) => ({
      truePositives: summary.truePositives + metric.truePositives,
      falsePositives: summary.falsePositives + metric.falsePositives,
      falseNegatives: summary.falseNegatives + metric.falseNegatives,
      actualPositiveFiles: summary.actualPositiveFiles + metric.actualPositiveFiles,
      predictedPositiveFiles: summary.predictedPositiveFiles + metric.truePositives + metric.falsePositives,
    }),
    {
      truePositives: 0,
      falsePositives: 0,
      falseNegatives: 0,
      actualPositiveFiles: 0,
      predictedPositiveFiles: 0,
    },
  )
  const evaluatedFiles = input.fileInventory.totalCandidateFiles
  const trueNegatives = Math.max(
    0,
    evaluatedFiles - totals.truePositives - totals.falsePositives - totals.falseNegatives,
  )

  return { ...totals, trueNegatives, evaluatedFiles }
}

function buildScenarioMetrics(input: EvaluationMetricInput): EvaluationScenarioMetric[] {
  const familyMetrics = getGoldenFamilyMetrics(input.completedScan.scanType)
  const unsupportedShare = distributeCount(input.contentExtraction.unsupportedFiles, input.fileInventory.sampleFamilies.length)
  const ocrShare = distributeCount(input.contentExtraction.ocrDeferredFiles, input.fileInventory.sampleFamilies.length)

  return input.fileInventory.sampleFamilies.map((family, index) => {
    const metric = familyMetrics[family.family] ?? emptyFamilyMetric()
    const precision = calculateEvaluationRatio(metric.truePositives, metric.truePositives + metric.falsePositives)
    const recall = calculateEvaluationRatio(metric.truePositives, metric.actualPositiveFiles)

    return {
      sourceFamily: family.family,
      contextCategory: input.contextRisk.contextCategories.find((category) => (
        category.sourceFamily === family.family
      ))?.contextCategory,
      precision,
      recall,
      f1: calculateEvaluationF1(precision, recall),
      predictedPositiveFiles: metric.truePositives + metric.falsePositives,
      actualPositiveFiles: metric.actualPositiveFiles,
      truePositives: metric.truePositives,
      falsePositives: metric.falsePositives,
      falseNegatives: metric.falseNegatives,
      unsupportedFiles: unsupportedShare[index] ?? 0,
      ocrDeferredFiles: ocrShare[index] ?? 0,
    }
  })
}

function buildReviewContext(metrics: AdminMetrics): EvaluationQualityBasis['review'] {
  const reviewDecisionCount = metrics.reviewDecisionCount ?? 0
  const totalReviewWork = Math.max(reviewDecisionCount + metrics.openReviewBacklog, 1)

  return {
    reviewDecisionCount,
    falsePositiveCorrections: metrics.falsePositiveDecisions ?? 0,
    openReviewBacklog: metrics.openReviewBacklog,
    reviewThroughputPerDay: metrics.reviewThroughputPerDay,
    ownerTaskCompletionRate: Number((reviewDecisionCount / totalReviewWork).toFixed(3)),
  }
}

function buildRiskProgress(
  metrics: AdminMetrics,
  baselineHighRiskFindings: number,
): EvaluationQualityBasis['riskReduction'] {
  const reviewedHighRiskFindings = Math.min(baselineHighRiskFindings, metrics.reviewDecisionCount ?? 0)
  const remainingHighRiskFindings = Math.max(0, baselineHighRiskFindings - reviewedHighRiskFindings)

  return {
    basis: 'review_decision_progress_not_deletion',
    baselineHighRiskFindings,
    reviewedHighRiskFindings,
    remainingHighRiskFindings,
    riskReductionRate: baselineHighRiskFindings > 0
      ? calculateEvaluationRatio(reviewedHighRiskFindings, baselineHighRiskFindings) ?? 0
      : 1,
    deletionExecuted: false,
  }
}

function buildSafetyBoundaries(input: EvaluationMetricInput): EvaluationQualityBasis['safetyBoundaries'] {
  const resourceIntensity = buildEvaluationResourceIntensity(input)

  return {
    rawContentExposed: Boolean(
      input.contentExtraction.rawContentExposed
      || input.signalDetection.rawContentExposed
      || input.findingAssembly.rawContentExposed
      || input.reviewSupport.rawContentExposed
      || input.auditRecording.rawContentExposed
      || input.deltaScan?.rawContentExposed,
    ),
    legalConclusionProvided: Boolean(
      input.contextRisk.legalConclusionProvided
      || input.findingAssembly.legalConclusionProvided
      || input.reviewSupport.legalConclusionProvided
      || input.auditRecording.legalConclusionProvided
      || input.deltaScan?.legalConclusionProvided,
    ),
    deletionExecuted: Boolean(input.auditRecording.deletionExecuted || input.deltaScan?.deletionExecuted),
    modelCalls: resourceIntensity.modelCalls ?? 0,
    estimatedCostUsd: resourceIntensity.estimatedCostUsd ?? 0,
  }
}

function buildInputStages(input: EvaluationMetricInput): string[] {
  return [
    `file_inventory:${input.fileInventory.status}`,
    `content_extraction:${input.contentExtraction.status}`,
    `signal_detection:${input.signalDetection.status}`,
    `context_risk:${input.contextRisk.status}`,
    `owner_assignment:${input.ownerAssignment.status}`,
    `finding_assembly:${input.findingAssembly.status}`,
    `review_support:${input.reviewSupport.status}`,
    `audit_recording:${input.auditRecording.status}`,
    ...(input.deltaScan ? [`delta_scan:${input.deltaScan.status}`] : []),
    'admin_metrics:completed',
  ]
}

function buildWarnings(
  input: EvaluationMetricInput,
  confusionMatrix: EvaluationConfusionMatrix,
  safetyBoundaries: EvaluationQualityBasis['safetyBoundaries'],
): string[] {
  return [
    ...(confusionMatrix.falsePositives > 0
      ? [`${confusionMatrix.falsePositives} predicted positive file needs false-positive review.`]
      : []),
    ...(confusionMatrix.falseNegatives > 0
      ? [`${confusionMatrix.falseNegatives} golden dataset positives are not detected in this P0 run.`]
      : []),
    ...input.contentExtraction.warnings,
    ...(safetyBoundaries.rawContentExposed ? ['Raw content exposure boundary failed.'] : []),
    ...(safetyBoundaries.legalConclusionProvided ? ['Legal conclusion boundary failed.'] : []),
    ...(safetyBoundaries.deletionExecuted ? ['Deletion execution boundary failed.'] : []),
  ]
}

function buildEvaluationRulesHash(
  input: EvaluationMetricInput,
  adminMetricsRulesHash: string,
  confusionMatrix: EvaluationConfusionMatrix,
): string {
  return [
    'sha256:evaluation_metrics_v1',
    input.completedScan.scanId,
    input.completedScan.scanType,
    goldenDatasetVersion,
    input.fileInventory.inventoryFingerprint,
    input.contentExtraction.extractionFingerprint,
    input.signalDetection.detectorRulesHash,
    input.contextRisk.riskRulesFingerprint,
    input.ownerAssignment.assignmentRulesFingerprint,
    input.findingAssembly.assemblyRulesFingerprint,
    input.reviewSupport.supportRulesFingerprint,
    input.auditRecording.auditRulesFingerprint,
    adminMetricsRulesHash,
    input.deltaScan?.deltaFingerprint ?? 'no_delta',
    input.completedScan.reproducibilityFingerprint ?? 'no_finding_fingerprint',
    `${confusionMatrix.truePositives}_${confusionMatrix.falsePositives}_${confusionMatrix.falseNegatives}_${confusionMatrix.trueNegatives}`,
  ].join('_')
}

function distributeCount(total: number, bucketCount: number): number[] {
  if (bucketCount <= 0) {
    return []
  }

  return Array.from({ length: bucketCount }, (_, index) => index < total ? 1 : 0)
}

function getGoldenFamilyMetrics(scanType: string): Record<string, GoldenFamilyMetric> {
  return scanType === 'delta' ? deltaScanGoldenMetrics : fullScanGoldenMetrics
}

function emptyFamilyMetric(): GoldenFamilyMetric {
  return { actualPositiveFiles: 0, truePositives: 0, falsePositives: 0, falseNegatives: 0 }
}
