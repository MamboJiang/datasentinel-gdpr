import { describe, expect, it } from 'vitest'
import { getInitialMockData, type MockData } from './mockApi'
import { recordHumanReviewDecision, type HumanReviewCommand } from './humanReviewDecision'
import { buildReviewSupport } from './reviewSupport'
import { completeScanWorkflow, startScanWorkflow } from './scanWorkflow'
import type { ReviewSupport } from '../types'

const startedAt = '2026-05-30T14:00:00.000Z'
const completedAt = '2026-05-30T14:00:38.200Z'
const reviewedAt = '2026-05-30T14:08:00.000Z'

function startFullScan(data: MockData = getInitialMockData(), sourceId = 'source_001') {
  return startScanWorkflow(data, {
    actorId: 'user_demo_admin',
    auditEventId: 'audit_metrics_started',
    occurredAt: startedAt,
    scanType: 'full',
    sourceId,
  })
}

function completeFullScan(data: MockData = getInitialMockData()) {
  const started = startFullScan(data)

  if (!started.accepted) {
    throw new Error('Expected full scan start to be accepted.')
  }

  return completeScanWorkflow(started.data, {
    auditEventId: 'audit_metrics_completed',
    occurredAt: completedAt,
    scanId: started.scanId,
  })
}

function startDeltaScan(data: MockData = getInitialMockData()) {
  return startScanWorkflow(data, {
    actorId: 'user_demo_admin',
    auditEventId: 'audit_metrics_delta_started',
    occurredAt: startedAt,
    scanType: 'delta',
    sourceId: 'source_001',
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
    auditEventId: 'audit_metrics_review',
    checklistItemIds: reviewSupport.checklist.filter((item) => item.required).map((item) => item.itemId),
    decision: 'keep_with_reason',
    findingId: reviewSupport.findingId,
    idempotencyKey: 'idem_metrics_review',
    occurredAt: reviewedAt,
    reason: 'Business owner confirmed a time-boxed retention reason from the redacted evidence card.',
    retentionUntil: '2027-05-30',
    reviewId: 'review_metrics',
    reviewSupportRulesFingerprint: data.scan.reviewSupport?.supportRulesFingerprint,
  }
}

describe('admin metrics aggregation workflow', () => {
  it('aggregates running metrics from upstream stage summaries without exposing unsafe outputs', () => {
    const result = startFullScan()

    expect(result.accepted).toBe(true)

    if (!result.accepted) {
      return
    }

    expect(result.data.metrics.aggregation).toMatchObject({
      status: 'partial',
      scanId: 'scan_demo_full',
      scanType: 'full',
      sourceId: 'source_001',
      policyPackVersion: '2026.05-demo',
      partial: true,
      scanCoverage: {
        scannedFiles: 14,
        candidateFiles: 42,
        flaggedFiles: 5,
        scanProgress: 0.34,
        scanTimeSeconds: null,
      },
      risk: {
        riskAssessedFindings: 0,
        highRiskFindings: 0,
        retentionReviewFiles: 0,
        humanReviewRequiredFindings: 0,
      },
      rawContentExposed: false,
      legalConclusionProvided: false,
      deletionExecuted: false,
      modelCalls: 0,
      estimatedCostUsd: 0,
    })
    expect(result.data.metrics.aggregation?.rulesFingerprint).toContain('admin_metrics_v1')
    expect(result.data.metrics.aggregation?.inputStages).toEqual([
      'file_inventory:running',
      'content_extraction:running',
      'signal_detection:pending',
      'context_risk:pending',
      'owner_assignment:pending',
      'finding_assembly:pending',
      'review_support:pending',
      'audit_recording:pending',
    ])
    expect(result.data.metrics.aggregation?.warnings).toContain(
      'Admin metrics are partial while upstream workflow stages are running.',
    )
  })

  it('links completed aggregation to scan, review, audit, and evaluation state', () => {
    const completed = completeFullScan()
    const aggregation = completed.metrics.aggregation

    expect(aggregation).toMatchObject({
      status: 'completed',
      partial: false,
      scanCoverage: {
        scannedFiles: 42,
        candidateFiles: 42,
        flaggedFiles: 17,
        scanProgress: 1,
        scanTimeSeconds: 38.2,
        throughputFilesPerSecond: 1.1,
      },
      risk: {
        riskAssessedFindings: completed.scan.contextRisk?.riskAssessedFindings,
        highRiskFindings: completed.scan.contextRisk?.highRiskFindings,
        retentionReviewFiles: completed.scan.contextRisk?.retentionReviewFiles,
        humanReviewRequiredFindings: completed.scan.contextRisk?.humanReviewRequiredFindings,
      },
      ownerBacklog: {
        openReviewBacklog: completed.metrics.openReviewBacklog,
        reviewDecisionCount: completed.metrics.reviewDecisionCount,
      },
      audit: {
        recordedEvents: completed.scan.auditRecording?.recordedEventCount,
        linkedFindingEvents: completed.scan.auditRecording?.linkedFindingEvents,
        reviewDecisionEvents: 0,
      },
      evaluationLinked: true,
      rawContentExposed: false,
      legalConclusionProvided: false,
      deletionExecuted: false,
    })
    expect(completed.evaluation.adminMetricsRulesHash).toBe(aggregation?.rulesFingerprint)
    expect(aggregation?.ownerBacklog.ownerTaskCompletionRate).toBeCloseTo(0.353, 3)
  })

  it('keeps delta aggregation connected to baseline counts without treating missing files as deletion', () => {
    const started = startDeltaScan()

    expect(started.accepted).toBe(true)

    if (!started.accepted) {
      return
    }

    const completed = completeScanWorkflow(started.data, {
      auditEventId: 'audit_metrics_delta_completed',
      occurredAt: completedAt,
      scanId: started.scanId,
    })

    expect(completed.metrics.aggregation).toMatchObject({
      scanId: 'scan_demo_delta',
      scanType: 'delta',
      delta: {
        baselineFiles: 42,
        changedFiles: 6,
        processedChangedFiles: 6,
        carriedForwardFindings: 15,
        missingFiles: 1,
        missingFilesTreatedAsDeleted: false,
      },
      deletionExecuted: false,
    })
    expect(completed.metrics.aggregation?.inputStages).toContain('delta_scan:completed')
    expect(completed.evaluation.adminMetricsRulesHash).toBe(completed.metrics.aggregation?.rulesFingerprint)
  })

  it('updates aggregation after accepted review decisions and preserves rejected path identity', () => {
    const completed = completeFullScan()
    const rejected = startFullScan(completed, 'source_002')

    expect(rejected.accepted).toBe(false)
    expect(rejected.data.metrics).toBe(completed.metrics)

    const reviewSupport = supportFor(completed)
    const result = recordHumanReviewDecision(completed, commandFor(completed, reviewSupport), reviewSupport)

    expect(result.accepted).toBe(true)

    if (!result.accepted) {
      return
    }

    expect(result.data.metrics.aggregation).toMatchObject({
      ownerBacklog: {
        openReviewBacklog: completed.metrics.openReviewBacklog - 1,
        reviewDecisionCount: (completed.metrics.reviewDecisionCount ?? 0) + 1,
      },
      outcomes: {
        retainedDecisions: (completed.metrics.retainedDecisions ?? 0) + 1,
      },
      audit: {
        recordedEvents: result.data.scan.auditRecording?.recordedEventCount,
        linkedFindingEvents: result.data.scan.auditRecording?.linkedFindingEvents,
        reviewDecisionEvents: 1,
      },
      deletionExecuted: false,
      modelCalls: 0,
      estimatedCostUsd: 0,
    })
  })
})
