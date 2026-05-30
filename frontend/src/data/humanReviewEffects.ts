import { buildAuditRecordingSummary } from './auditEventRecording'
import { refreshReviewAggregation } from './adminMetricsAggregation'
import { refreshEvaluationReviewContext } from './scanEvaluation'
import type {
  AdminMetrics,
  AuditEvent,
  EvaluationSummary,
  ReviewDecision,
  Scan,
} from '../types'

const decisionMetricKey: Record<ReviewDecision, keyof AdminMetrics> = {
  delete_candidate: 'deletionCandidateDecisions',
  keep_with_reason: 'retainedDecisions',
  correct_false_positive: 'falsePositiveDecisions',
  reassign_owner: 'reassignedDecisions',
  escalate: 'escalatedDecisions',
}

export function updateReviewDecisionMetrics({
  auditEvents,
  decision,
  evaluation,
  metrics,
  scanId,
}: {
  auditEvents: AuditEvent[]
  decision: ReviewDecision
  evaluation: EvaluationSummary
  metrics: AdminMetrics
  scanId: string
}): AdminMetrics {
  const metricKey = decisionMetricKey[decision]
  const closesOwnerBacklog = decision !== 'reassign_owner'
  const reviewDecisionCount = (metrics.reviewDecisionCount ?? 0) + 1
  const auditRecordedEvents = auditEvents.filter((event) => event.scanId === scanId).length
  const auditLinkedFindingEvents = auditEvents.filter((event) => event.scanId === scanId && event.findingId).length
  const auditReviewDecisionEvents = auditEvents.filter((event) => event.scanId === scanId && event.eventType === 'review_recorded').length
  const nextMetrics: AdminMetrics = {
    ...metrics,
    [metricKey]: Number(metrics[metricKey] ?? 0) + 1,
    evaluation,
    medianReviewTimeHours: metrics.medianReviewTimeHours ?? null,
    openReviewBacklog: closesOwnerBacklog
      ? Math.max(0, metrics.openReviewBacklog - 1)
      : metrics.openReviewBacklog,
    reviewDecisionCount,
    reviewThroughputPerDay: Number(((metrics.reviewThroughputPerDay ?? 0) + 1).toFixed(1)),
    auditRecordedEvents,
    auditLinkedFindingEvents,
    auditReviewDecisionEvents,
  }
  const nextEvaluation = refreshEvaluationReviewContext(evaluation, nextMetrics)

  return {
    ...nextMetrics,
    evaluation: nextEvaluation,
    aggregation: refreshReviewAggregation({
      auditLinkedFindingEvents,
      auditRecordedEvents,
      auditReviewDecisionEvents,
      evaluation: nextEvaluation,
      metrics: nextMetrics,
    }),
  }
}

export function updateReviewDecisionEvaluation(
  evaluation: EvaluationSummary,
  policyPackVersion: string,
  reviewSupportRulesFingerprint: string | undefined,
): EvaluationSummary {
  return {
    ...evaluation,
    reviewDecisionRulesHash: `sha256:${policyPackVersion}_${reviewSupportRulesFingerprint ?? 'no_review_support_hash'}_review_decision_v1`,
    resourceIntensity: {
      ...evaluation.resourceIntensity,
      modelCalls: 0,
      estimatedCostUsd: 0,
    },
  }
}

export function updateScanAuditRecording(scan: Scan, auditEvents: AuditEvent[], policyPackVersion: string): Scan {
  const auditRecording = buildAuditRecordingSummary({
    auditEvents,
    policyPackVersion,
    scanId: scan.scanId,
    state: scan.status === 'completed' ? 'completed' : 'pending',
  })

  return {
    ...scan,
    auditRecording,
    pipelineStages: scan.pipelineStages?.map((stage) => (
      stage.stage === 'recording_audit_events'
        ? {
            ...stage,
            status: auditRecording.status,
            processedFiles: auditRecording.recordedEventCount,
            totalFiles: auditRecording.status === 'completed' ? auditRecording.recordedEventCount : stage.totalFiles,
            warnings: auditRecording.warnings,
          }
        : stage
    )),
  }
}
