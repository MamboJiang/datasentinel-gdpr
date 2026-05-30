import { describe, expect, it } from 'vitest'
import { getInitialMockData } from './mockApi'
import type { MockData } from './mockApi'
import { completeScanWorkflow, startScanWorkflow } from './scanWorkflow'

const startedAt = '2026-05-30T12:30:00.000Z'
const completedAt = '2026-05-30T12:30:38.200Z'

function startFullScan(data: MockData = getInitialMockData()) {
  return startScanWorkflow(data, {
    actorId: 'user_demo_admin',
    auditEventId: 'audit_started',
    occurredAt: startedAt,
    scanType: 'full',
    sourceId: 'source_001',
  })
}

describe('scan workflow completion', () => {
  it('completes the full scan with final metrics, evaluation link, and audit state', () => {
    const started = startFullScan()

    if (!started.accepted) {
      throw new Error('Expected full scan start to be accepted.')
    }

    const completed = completeScanWorkflow(started.data, {
      auditEventId: 'audit_completed',
      occurredAt: completedAt,
      scanId: started.scanId,
    })

    expect(completed.scan).toMatchObject({
      scanId: 'scan_demo_full',
      sourceId: 'source_001',
      status: 'completed',
      stage: 'completed',
      progress: 1,
      scannedFiles: 42,
      flaggedFiles: 17,
      durationMs: 38200,
      throughputFilesPerSecond: 1.1,
      reproducibilityFingerprint: 'sha256:demo_findings',
    })
    expect(completed.scan.fileInventory).toMatchObject({
      status: 'completed',
      totalCandidateFiles: 42,
      fingerprintedFiles: 42,
      skippedFiles: 0,
      inventoryFingerprint: 'sha256:scan_demo_full_inventory_completed',
    })
    expect(completed.scan.contentExtraction).toMatchObject({
      status: 'completed',
      processedFiles: 42,
      successfulFiles: 38,
      warningFiles: 4,
      unsupportedFiles: 2,
      ocrDeferredFiles: 2,
      redactedEvidenceCandidates: 64,
      rawContentExposed: false,
    })
    expect(completed.scan.signalDetection).toMatchObject({
      status: 'completed',
      detectorRulesVersion: 'deterministic-p0-v1',
      evaluatedEvidenceCandidates: 64,
      detectedSignals: 38,
      redactedSignals: 38,
      findingsWithSignals: 17,
      rawContentExposed: false,
      warnings: [],
    })
    expect(completed.scan.signalDetection?.signalTypeCounts.find((signalType) => signalType.type === 'iban_like')).toMatchObject({
      signals: 4,
      evidenceRequirement: 'detector_signal',
    })
    expect(completed.scan.pipelineStages?.find((stage) => stage.stage === 'judging_context_risk')).toMatchObject({
      stage: 'judging_context_risk',
      status: 'completed',
      processedFiles: 17,
      totalFiles: 64,
    })
    expect(completed.scan.pipelineStages?.find((stage) => stage.stage === 'assigning_owner')).toMatchObject({
      stage: 'assigning_owner',
      status: 'completed',
      processedFiles: 17,
      totalFiles: 17,
    })
    expect(completed.scan.pipelineStages?.find((stage) => stage.stage === 'assembling_findings')).toMatchObject({
      stage: 'assembling_findings',
      status: 'completed',
      processedFiles: 17,
      totalFiles: 17,
    })
    expect(completed.scan.pipelineStages?.find((stage) => stage.stage === 'preparing_review_support')).toMatchObject({
      stage: 'preparing_review_support',
      status: 'completed',
      processedFiles: 17,
      totalFiles: 17,
    })
    expect(completed.scan.pipelineStages?.find((stage) => stage.stage === 'recording_audit_events')).toMatchObject({
      stage: 'recording_audit_events',
      status: 'completed',
      processedFiles: 38,
      totalFiles: 38,
    })
    expect(completed.scan.pipelineStages?.at(-1)).toMatchObject({
      stage: 'generating_evaluation_metrics',
      status: 'computed',
      processedFiles: 42,
      totalFiles: 42,
    })
    expect(completed.scan.auditRecording).toMatchObject({
      status: 'completed',
      recordedEventCount: 38,
      linkedScanEvents: 2,
      linkedFindingEvents: 34,
      systemEvents: 37,
      humanEvents: 1,
      rawContentExposed: false,
      legalConclusionProvided: false,
      deletionExecuted: false,
    })
    expect(completed.scan.contextRisk).toMatchObject({
      status: 'completed',
      policyPackVersion: '2026.05-demo',
      assessedEvidenceCandidates: 64,
      contextClassifiedFindings: 17,
      riskAssessedFindings: 17,
      highRiskFindings: 5,
      mediumRiskFindings: 9,
      lowRiskFindings: 3,
      retentionReviewFiles: 7,
      humanReviewRequiredFindings: 17,
      legalConclusionProvided: false,
    })
    expect(completed.scan.contextRisk?.contextCategories).toHaveLength(5)
    expect(completed.scan.contextRisk?.contextCategories.find((category) => category.contextCategory === 'supplier_onboarding')).toMatchObject({
      riskGuidance: 'Financial and signature identifiers require accountable human review.',
      retentionRuleApplied: true,
    })
    expect(completed.scan.ownerAssignment).toMatchObject({
      status: 'completed',
      policyPackVersion: '2026.05-demo',
      organizationModelVersion: '2026.05-demo',
      ownerResolutionStrategy: 'direct_owner_then_master_of_data',
      humanReviewRequiredFindings: 17,
      assignedFindings: 17,
      directOwnerAssignments: 10,
      masterOfDataAssignments: 5,
      escalationAssignments: 2,
      unownedFindings: 0,
      transferOptionCount: 1,
      escalationOptionCount: 1,
      sourceOwnerAvailable: true,
      warnings: [],
    })
    expect(completed.scan.findingAssembly).toMatchObject({
      status: 'completed',
      policyPackVersion: '2026.05-demo',
      assembledFindings: 17,
      evidenceCards: 17,
      missingEvidenceCards: 0,
      deniedActionCount: 1,
      rawContentExposed: false,
      legalConclusionProvided: false,
      warnings: [],
    })
    expect(completed.scan.reviewSupport).toMatchObject({
      status: 'completed',
      policyPackVersion: '2026.05-demo',
      organizationModelVersion: '2026.05-demo',
      reviewableFindings: 17,
      supportedFindings: 17,
      allowedActionCount: 6,
      deniedActionCount: 2,
      availableDecisionCount: 5,
      reasonRequiredDecisionCount: 5,
      checklistItemCount: 5,
      transferOptionCount: 1,
      escalationOptionCount: 1,
      rawContentExposed: false,
      legalConclusionProvided: false,
      warnings: [],
    })
    expect(completed.findings).toHaveLength(17)
    expect(Object.keys(completed.findingDetails)).toHaveLength(17)
    expect(completed.findings.every((finding) => finding.scanId === completed.scan.scanId)).toBe(true)
    expect(completed.findings.every((finding) => (finding.evidenceSignalCount ?? 0) > 0)).toBe(true)
    expect(completed.findingDetails.finding_001).toMatchObject({
      findingId: 'finding_001',
      scanId: 'scan_demo_full',
      policyContext: {
        policyPackVersion: '2026.05-demo',
        policyConclusion: 'human_review_required',
      },
      deniedActions: [
        {
          action: 'execute_real_deletion',
          reason: 'Real deletion is disabled in the prototype.',
        },
      ],
    })
    expect(completed.findingDetails.finding_001.signals?.every((signal) => signal.snippet.includes('[REDACTED'))).toBe(true)
    expect(completed.metrics).toMatchObject({
      totalScannedFiles: 42,
      flaggedFiles: 17,
      totalScannedGb: 0.038,
      scanProgress: 1,
      lastScanTimeSeconds: 38.2,
      inventoryCandidateFiles: 42,
      fingerprintedFiles: 42,
      extractedFiles: 38,
      extractionWarnings: 4,
      redactedEvidenceCandidates: 64,
      detectedSignals: 38,
      redactedSignals: 38,
      findingsWithSignals: 17,
      contextClassifiedFindings: 17,
      riskAssessedFindings: 17,
      highRiskFindings: 5,
      retentionOverdueFiles: 7,
      humanReviewRequiredFindings: 17,
      ownerRoutedFindings: 17,
      assignedFindings: 17,
      directOwnerAssignments: 10,
      masterOfDataAssignments: 5,
      escalationAssignments: 2,
      assembledFindings: 17,
      evidenceCards: 17,
      reviewSupportedFindings: 17,
      deniedReviewActions: 2,
      reviewChecklistItems: 5,
      reviewTransferOptions: 1,
      reviewEscalationOptions: 1,
      auditRecordedEvents: 38,
      auditLinkedFindingEvents: 34,
      auditReviewDecisionEvents: 0,
    })
    expect(completed.evaluation).toMatchObject({
      scanId: 'scan_demo_full',
      configHash: 'sha256:scan_demo_full_inventory_completed',
      detectorRulesHash: 'sha256:2026.05-demo_sha256:snapshot_source_001_scan_demo_full_extraction_completed_signal_detection_completed',
      signalDetectionRulesHash: 'sha256:2026.05-demo_sha256:snapshot_source_001_scan_demo_full_extraction_completed_signal_detection_completed',
      contextRiskRulesHash: 'sha256:2026.05-demo_sha256:snapshot_source_001_scan_demo_full_extraction_completed_context_risk_completed',
      ownerAssignmentRulesHash: 'sha256:2026.05-demo_2026.05-demo_sha256:2026.05-demo_sha256:snapshot_source_001_scan_demo_full_extraction_completed_context_risk_completed_owner_assignment_completed',
      findingAssemblyRulesHash: 'sha256:sha256:2026.05-demo_2026.05-demo_sha256:2026.05-demo_sha256:snapshot_source_001_scan_demo_full_extraction_completed_context_risk_completed_owner_assignment_completed_sha256:snapshot_source_001_scan_demo_full_extraction_completed_finding_assembly_completed',
      reviewSupportRulesHash: 'sha256:2026.05-demo_2026.05-demo_sha256:sha256:2026.05-demo_2026.05-demo_sha256:2026.05-demo_sha256:snapshot_source_001_scan_demo_full_extraction_completed_context_risk_completed_owner_assignment_completed_sha256:snapshot_source_001_scan_demo_full_extraction_completed_finding_assembly_completed_user_anna_review_support_completed',
      auditRecordingRulesHash: 'sha256:2026.05-demo_scan_demo_full_completed_38_audit_recording_v1',
      precision: 0.941,
      recall: 0.842,
      f1: 0.889,
      reproducibility: 1,
      throughputFilesPerSecond: 1.1,
    })
    expect(completed.evaluation.evaluationRulesHash).toContain('evaluation_metrics_v1')
    expect(completed.evaluation.qualityBasis).toMatchObject({
      status: 'computed',
      goldenDatasetVersion: 'gdpr-samples-p0-v1',
      inputStages: [
        'file_inventory:completed',
        'content_extraction:completed',
        'signal_detection:completed',
        'context_risk:completed',
        'owner_assignment:completed',
        'finding_assembly:completed',
        'review_support:completed',
        'audit_recording:completed',
        'admin_metrics:completed',
      ],
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
    expect(completed.evaluation.qualityBasis?.scenarioMetrics.find((scenario) => (
      scenario.sourceFamily === 'Incident_Report'
    ))).toMatchObject({
      precision: 0.667,
      recall: 0.667,
      falsePositives: 1,
      falseNegatives: 1,
    })
    expect(completed.evaluation.resourceIntensity).toMatchObject({
      modelCalls: 0,
      estimatedCostUsd: 0,
      estimatedCostPerThousandFilesUsd: 0,
      paidServiceUsed: false,
    })
    expect(completed.meta.partial).toBe(false)
    expect(completed.meta.warnings).toEqual([])
    expect(completed.auditEvents[0]).toMatchObject({
      auditEventId: 'audit_completed',
      eventType: 'full_scan_completed',
      actorId: 'system',
      occurredAt: completedAt,
      policyPackVersion: '2026.05-demo',
    })
    expect(completed.auditEvents[1]).toMatchObject({
      auditEventId: 'audit_completed_owner_assignment',
      eventType: 'owner_assignment_completed',
      actorId: 'system',
      occurredAt: completedAt,
      policyPackVersion: '2026.05-demo',
    })
    expect(completed.auditEvents[1].summary).toContain('17 findings')
    expect(completed.auditEvents[1].summary).toContain('0 unowned')
    expect(completed.auditEvents[2]).toMatchObject({
      auditEventId: 'audit_completed_finding_assembly',
      eventType: 'finding_assembly_completed',
      actorId: 'system',
      occurredAt: completedAt,
      policyPackVersion: '2026.05-demo',
    })
    expect(completed.auditEvents[2].summary).toContain('17 findings')
    expect(completed.auditEvents[2].summary).toContain('17 evidence cards')
  })
})
