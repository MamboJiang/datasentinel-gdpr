import type {
  AdminMetrics,
  AdminMetricsAggregationSummary,
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

type MetricsStageInput = {
  auditRecording: AuditRecordingSummary
  contentExtraction: ContentExtractionSummary
  contextRisk: ContextRiskSummary
  deltaScan?: DeltaScanSummary
  fileInventory: FileInventorySummary
  findingAssembly: FindingAssemblySummary
  ownerAssignment: OwnerAssignmentSummary
  reviewSupport: ReviewSupportSummary
  signalDetection: SignalDetectionSummary
}

type MetricsFingerprintInput = MetricsStageInput & {
  scanId: string
  scanType: string
  state: string
}

type MetricsAggregationInput = MetricsFingerprintInput & {
  currentMetrics: AdminMetrics
  evaluation?: EvaluationSummary
  flaggedFiles: number
  lastScanTimeSeconds: number | null
  scannedFiles: number
  scannedGb: number
  scanProgress: number
  sourceId: string
  throughputFilesPerSecond: number | null
}

type ReviewAggregationInput = {
  auditLinkedFindingEvents: number
  auditRecordedEvents: number
  auditReviewDecisionEvents: number
  evaluation: EvaluationSummary
  metrics: AdminMetrics
}

export function buildAdminMetricsRulesFingerprint(input: MetricsFingerprintInput): string {
  return [
    'sha256:admin_metrics_v1',
    input.scanId,
    input.scanType,
    input.state,
    input.fileInventory.inventoryFingerprint,
    input.contentExtraction.extractionFingerprint,
    input.signalDetection.detectorRulesHash,
    input.contextRisk.riskRulesFingerprint,
    input.ownerAssignment.assignmentRulesFingerprint,
    input.findingAssembly.assemblyRulesFingerprint,
    input.reviewSupport.supportRulesFingerprint,
    input.auditRecording.auditRulesFingerprint,
    input.deltaScan?.deltaFingerprint ?? 'no_delta',
  ].join('_')
}

export function buildAdminMetricsAggregation(input: MetricsAggregationInput): AdminMetricsAggregationSummary {
  const warnings = collectWarnings(input)

  return {
    status: input.state === 'completed' ? 'completed' : 'partial',
    scanId: input.scanId,
    scanType: input.scanType,
    sourceId: input.sourceId,
    policyPackVersion: input.contextRisk.policyPackVersion,
    rulesFingerprint: buildAdminMetricsRulesFingerprint(input),
    inputStages: buildInputStages(input),
    partial: input.state !== 'completed',
    scanCoverage: {
      scannedFiles: input.scannedFiles,
      candidateFiles: input.fileInventory.totalCandidateFiles,
      flaggedFiles: input.flaggedFiles,
      scanProgress: input.scanProgress,
      scannedGb: input.scannedGb,
      scanTimeSeconds: input.lastScanTimeSeconds,
      throughputFilesPerSecond: input.throughputFilesPerSecond,
    },
    risk: {
      riskAssessedFindings: input.contextRisk.riskAssessedFindings,
      highRiskFindings: input.contextRisk.highRiskFindings,
      retentionReviewFiles: input.contextRisk.retentionReviewFiles,
      humanReviewRequiredFindings: input.contextRisk.humanReviewRequiredFindings,
    },
    ownerBacklog: buildOwnerBacklog(input.currentMetrics, input.reviewSupport.reviewableFindings),
    outcomes: buildOutcomes(input.currentMetrics),
    audit: {
      recordedEvents: input.auditRecording.recordedEventCount,
      linkedFindingEvents: input.auditRecording.linkedFindingEvents,
      reviewDecisionEvents: input.auditRecording.reviewDecisionEvents,
    },
    delta: input.deltaScan ? buildDelta(input.deltaScan) : undefined,
    evaluationLinked: Boolean(input.evaluation?.evaluationRunId),
    rawContentExposed: hasRawContentExposure(input),
    legalConclusionProvided: hasLegalConclusion(input),
    deletionExecuted: Boolean(input.auditRecording.deletionExecuted || input.deltaScan?.deletionExecuted),
    modelCalls: input.evaluation?.resourceIntensity?.modelCalls ?? 0,
    estimatedCostUsd: input.evaluation?.resourceIntensity?.estimatedCostUsd ?? 0,
    warnings,
  }
}

export function refreshReviewAggregation(input: ReviewAggregationInput): AdminMetricsAggregationSummary | undefined {
  const aggregation = input.metrics.aggregation

  if (!aggregation) {
    return undefined
  }

  return {
    ...aggregation,
    rulesFingerprint: input.evaluation.adminMetricsRulesHash ?? aggregation.rulesFingerprint,
    ownerBacklog: buildOwnerBacklog(input.metrics, aggregation.ownerBacklog.reviewableFindings),
    outcomes: buildOutcomes(input.metrics),
    audit: {
      recordedEvents: input.auditRecordedEvents,
      linkedFindingEvents: input.auditLinkedFindingEvents,
      reviewDecisionEvents: input.auditReviewDecisionEvents,
    },
    evaluationLinked: Boolean(input.evaluation.evaluationRunId),
    modelCalls: input.evaluation.resourceIntensity?.modelCalls ?? aggregation.modelCalls,
    estimatedCostUsd: input.evaluation.resourceIntensity?.estimatedCostUsd ?? aggregation.estimatedCostUsd,
    deletionExecuted: false,
  }
}

function buildInputStages(input: MetricsStageInput): string[] {
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
  ]
}

function buildOwnerBacklog(metrics: AdminMetrics, reviewableFindings: number) {
  const reviewDecisionCount = metrics.reviewDecisionCount ?? 0
  const totalReviewWork = Math.max(reviewableFindings, reviewDecisionCount + metrics.openReviewBacklog)

  return {
    openReviewBacklog: metrics.openReviewBacklog,
    reviewableFindings: totalReviewWork,
    reviewDecisionCount,
    ownerTaskCompletionRate: totalReviewWork > 0
      ? Number((reviewDecisionCount / totalReviewWork).toFixed(3))
      : 1,
    reviewThroughputPerDay: metrics.reviewThroughputPerDay,
    medianReviewTimeHours: metrics.medianReviewTimeHours ?? null,
  }
}

function buildOutcomes(metrics: AdminMetrics) {
  return {
    deletionCandidateDecisions: metrics.deletionCandidateDecisions ?? 0,
    retainedDecisions: metrics.retainedDecisions ?? 0,
    falsePositiveDecisions: metrics.falsePositiveDecisions ?? 0,
    reassignedDecisions: metrics.reassignedDecisions ?? 0,
    escalatedDecisions: metrics.escalatedDecisions ?? 0,
  }
}

function buildDelta(deltaScan: DeltaScanSummary) {
  return {
    baselineFiles: deltaScan.baselineTotalFiles,
    changedFiles: deltaScan.changedFiles,
    processedChangedFiles: deltaScan.processedChangedFiles,
    carriedForwardFindings: deltaScan.unchangedFindingsCarriedForward,
    missingFiles: deltaScan.missingFiles,
    missingFilesTreatedAsDeleted: deltaScan.missingFilesTreatedAsDeleted,
  }
}

function collectWarnings(input: MetricsStageInput & { state: string }): string[] {
  return [
    ...(input.state === 'completed' ? [] : ['Admin metrics are partial while upstream workflow stages are running.']),
    ...input.fileInventory.warnings,
    ...input.contentExtraction.warnings,
    ...input.signalDetection.warnings,
    ...input.contextRisk.warnings,
    ...input.ownerAssignment.warnings,
    ...input.findingAssembly.warnings,
    ...input.reviewSupport.warnings,
    ...input.auditRecording.warnings,
    ...(input.deltaScan?.warnings ?? []),
  ]
}

function hasRawContentExposure(input: MetricsStageInput): boolean {
  return Boolean(
    input.contentExtraction.rawContentExposed
    || input.signalDetection.rawContentExposed
    || input.findingAssembly.rawContentExposed
    || input.reviewSupport.rawContentExposed
    || input.auditRecording.rawContentExposed
    || input.deltaScan?.rawContentExposed,
  )
}

function hasLegalConclusion(input: MetricsStageInput): boolean {
  return Boolean(
    input.contextRisk.legalConclusionProvided
    || input.findingAssembly.legalConclusionProvided
    || input.reviewSupport.legalConclusionProvided
    || input.auditRecording.legalConclusionProvided
    || input.deltaScan?.legalConclusionProvided,
  )
}
