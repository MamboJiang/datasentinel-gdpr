import { describe, expect, it } from 'vitest'
import { getInitialMockData, type MockData } from './mockApi'
import { recordHumanReviewDecision, type HumanReviewCommand } from './humanReviewDecision'
import { buildReviewSupport } from './reviewSupport'
import { completeScanWorkflow, startScanWorkflow } from './scanWorkflow'
import type { ReviewSupport } from '../types'

const startedAt = '2026-05-30T15:00:00.000Z'
const completedAt = '2026-05-30T15:00:38.200Z'
const reviewedAt = '2026-05-30T15:10:00.000Z'

function completeFullScan(data: MockData = getInitialMockData()) {
  const started = startScanWorkflow(data, {
    actorId: 'user_demo_admin',
    auditEventId: 'audit_eval_started',
    occurredAt: startedAt,
    scanType: 'full',
    sourceId: 'source_001',
  })

  if (!started.accepted) {
    throw new Error('Expected full scan start to be accepted.')
  }

  return completeScanWorkflow(started.data, {
    auditEventId: 'audit_eval_completed',
    occurredAt: completedAt,
    scanId: started.scanId,
  })
}

function completeDeltaScan(data: MockData = getInitialMockData()) {
  const started = startScanWorkflow(data, {
    actorId: 'user_demo_admin',
    auditEventId: 'audit_eval_delta_started',
    occurredAt: startedAt,
    scanType: 'delta',
    sourceId: 'source_001',
  })

  if (!started.accepted) {
    throw new Error('Expected delta scan start to be accepted.')
  }

  return completeScanWorkflow(started.data, {
    auditEventId: 'audit_eval_delta_completed',
    occurredAt: completedAt,
    scanId: started.scanId,
  })
}

function supportFor(data: MockData): ReviewSupport {
  return buildReviewSupport({
    actorId: 'user_anna',
    finding: data.findingDetails.finding_001,
    governanceConfig: data.governanceConfig,
    occurredAt: reviewedAt,
  })
}

function commandFor(data: MockData, reviewSupport: ReviewSupport): HumanReviewCommand {
  return {
    actorId: reviewSupport.actorId,
    auditEventId: 'audit_eval_review',
    checklistItemIds: reviewSupport.checklist.filter((item) => item.required).map((item) => item.itemId),
    decision: 'keep_with_reason',
    findingId: reviewSupport.findingId,
    idempotencyKey: 'idem_eval_review',
    occurredAt: reviewedAt,
    reason: 'Owner confirmed the redacted evidence belongs to a time-boxed business record.',
    retentionUntil: '2027-05-30',
    reviewId: 'review_eval',
    reviewSupportRulesFingerprint: data.scan.reviewSupport?.supportRulesFingerprint,
  }
}

describe('evaluation metrics generation workflow', () => {
  it('generates full-scan quality metrics from prior workflow summaries and golden dataset basis', () => {
    const completed = completeFullScan()

    expect(completed.evaluation).toMatchObject({
      scanId: 'scan_demo_full',
      precision: 0.941,
      recall: 0.842,
      f1: 0.889,
      reproducibility: 1,
      throughputFilesPerSecond: 1.1,
    })
    expect(completed.evaluation.evaluationRulesHash).toContain('evaluation_metrics_v1')
    expect(completed.evaluation.qualityBasis).toMatchObject({
      status: 'computed',
      datasetId: 'https://github.com/a-klumpp/GDPR-data-samples',
      goldenDatasetVersion: 'gdpr-samples-p0-v1',
      confusionMatrix: {
        truePositives: 16,
        falsePositives: 1,
        falseNegatives: 3,
        trueNegatives: 22,
        predictedPositiveFiles: 17,
        actualPositiveFiles: 19,
        evaluatedFiles: 42,
      },
      safetyBoundaries: {
        rawContentExposed: false,
        legalConclusionProvided: false,
        deletionExecuted: false,
        modelCalls: 0,
        estimatedCostUsd: 0,
      },
    })
    expect(completed.evaluation.qualityBasis?.scenarioMetrics).toHaveLength(5)
    expect(completed.evaluation.qualityBasis?.warnings).toEqual([
      '1 predicted positive file needs false-positive review.',
      '3 golden dataset positives are not detected in this P0 run.',
      '4 files need recoverable extraction review.',
      '2 files use unsupported formats in this P0 fixture.',
      '2 files are marked for future OCR instead of paid P0 processing.',
    ])
    expect(completed.evaluation.resourceIntensity).toMatchObject({
      peakMemoryMb: 411,
      cpuSeconds: 18.4,
      modelCalls: 0,
      estimatedCostUsd: 0,
      estimatedCostPerThousandFilesUsd: 0,
      paidServiceUsed: false,
    })
  })

  it('generates changed-file evaluation for delta scans without treating missing files as deletion', () => {
    const completed = completeDeltaScan()

    expect(completed.evaluation).toMatchObject({
      scanId: 'scan_demo_delta',
      precision: 1,
      recall: 0.667,
      f1: 0.8,
      throughputFilesPerSecond: 1.15,
    })
    expect(completed.evaluation.deltaScanRulesHash).toBe(completed.scan.deltaScan?.deltaFingerprint)
    expect(completed.evaluation.qualityBasis).toMatchObject({
      confusionMatrix: {
        truePositives: 2,
        falsePositives: 0,
        falseNegatives: 1,
        trueNegatives: 3,
        predictedPositiveFiles: 2,
        actualPositiveFiles: 3,
        evaluatedFiles: 6,
      },
      riskReduction: {
        basis: 'review_decision_progress_not_deletion',
        deletionExecuted: false,
      },
      safetyBoundaries: {
        rawContentExposed: false,
        legalConclusionProvided: false,
        deletionExecuted: false,
      },
    })
    expect(completed.evaluation.qualityBasis?.inputStages).toContain('delta_scan:completed')
    expect(completed.evaluation.qualityBasis?.warnings).toContain(
      '1 golden dataset positives are not detected in this P0 run.',
    )
    expect(completed.evaluation.resourceIntensity).toMatchObject({
      peakMemoryMb: 322,
      cpuSeconds: 2.5,
      modelCalls: 0,
      estimatedCostUsd: 0,
    })
  })

  it('refreshes review context after accepted decisions and preserves evaluation identity for rejected commands', () => {
    const completed = completeFullScan()
    const rejected = startScanWorkflow(completed, {
      actorId: 'user_demo_admin',
      auditEventId: 'audit_eval_rejected',
      occurredAt: startedAt,
      scanType: 'full',
      sourceId: 'source_002',
    })

    expect(rejected.accepted).toBe(false)
    expect(rejected.data.evaluation).toBe(completed.evaluation)

    const reviewSupport = supportFor(completed)
    const result = recordHumanReviewDecision(completed, commandFor(completed, reviewSupport), reviewSupport)

    expect(result.accepted).toBe(true)

    if (!result.accepted) {
      return
    }

    expect(result.data.evaluation.precision).toBe(completed.evaluation.precision)
    expect(result.data.evaluation.recall).toBe(completed.evaluation.recall)
    expect(result.data.evaluation.f1).toBe(completed.evaluation.f1)
    expect(result.data.evaluation.qualityBasis?.review).toMatchObject({
      reviewDecisionCount: (completed.metrics.reviewDecisionCount ?? 0) + 1,
      openReviewBacklog: completed.metrics.openReviewBacklog - 1,
      reviewThroughputPerDay: Number(((completed.metrics.reviewThroughputPerDay ?? 0) + 1).toFixed(1)),
    })
    expect(result.data.evaluation.qualityBasis?.riskReduction.deletionExecuted).toBe(false)
    expect(result.data.metrics.evaluation).toBe(result.data.evaluation)
  })
})
