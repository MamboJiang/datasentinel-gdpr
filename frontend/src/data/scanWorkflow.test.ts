import { describe, expect, it } from 'vitest'
import { getInitialMockData } from './mockApi'
import type { MockData } from './mockApi'
import {
  getDefaultFullScanSource,
  isSourceScanReady,
  startScanWorkflow,
} from './scanWorkflow'

const startedAt = '2026-05-30T12:30:00.000Z'

function startFullScan(data: MockData = getInitialMockData()) {
  return startScanWorkflow(data, {
    actorId: 'user_demo_admin',
    auditEventId: 'audit_started',
    occurredAt: startedAt,
    scanType: 'full',
    sourceId: 'source_001',
  })
}

describe('scan workflow', () => {
  it('selects the organizer sample source as the default full-scan target', () => {
    const data = getInitialMockData()

    expect(getDefaultFullScanSource(data.sources, data.governanceConfig)?.sourceId).toBe('source_001')
  })

  it('recognizes only governance-backed mock-ready sources as scan-ready', () => {
    const data = getInitialMockData()

    expect(isSourceScanReady(data.sources[0], data.governanceConfig)).toBe(true)
    expect(isSourceScanReady(data.sources[1], data.governanceConfig)).toBe(false)
  })

  it('starts a running full scan with source-specific status, metrics, and audit state', () => {
    const result = startFullScan()

    expect(result.accepted).toBe(true)

    if (!result.accepted) {
      return
    }

    expect(result.data.scan).toMatchObject({
      scanId: 'scan_demo_full',
      sourceId: 'source_001',
      scanType: 'full',
      status: 'running',
      stage: 'extracting_content',
      progress: 0.34,
      scannedFiles: 14,
      flaggedFiles: 5,
      durationMs: null,
      throughputFilesPerSecond: null,
    })
    expect(result.data.scan.fileInventory).toMatchObject({
      status: 'running',
      totalCandidateFiles: 42,
      fingerprintedFiles: 14,
      skippedFiles: 28,
      sourceSnapshotId: 'snapshot_source_001_scan_demo_full',
    })
    expect(result.data.scan.contentExtraction).toMatchObject({
      status: 'running',
      processedFiles: 14,
      successfulFiles: 12,
      warningFiles: 2,
      unsupportedFiles: 1,
      redactedEvidenceCandidates: 21,
      rawContentExposed: false,
    })
    expect(result.data.scan.signalDetection).toMatchObject({
      status: 'pending',
      detectorRulesVersion: 'deterministic-p0-v1',
      evaluatedEvidenceCandidates: 0,
      detectedSignals: 0,
      redactedSignals: 0,
      findingsWithSignals: 0,
      rawContentExposed: false,
    })
    expect(result.data.scan.pipelineStages?.map((stage) => stage.stage)).toEqual([
      'source_ready',
      'inventorying_files',
      'extracting_content',
      'detecting_signals',
      'judging_context_risk',
      'assigning_owner',
      'assembling_findings',
      'preparing_review_support',
      'recording_audit_events',
      'generating_evaluation_metrics',
    ])
    expect(result.data.scan.auditRecording).toMatchObject({
      status: 'pending',
      recordedEventCount: 1,
      linkedScanEvents: 1,
      rawContentExposed: false,
      legalConclusionProvided: false,
      deletionExecuted: false,
    })
    expect(result.data.scan.contextRisk).toMatchObject({
      status: 'pending',
      policyPackVersion: '2026.05-demo',
      assessedEvidenceCandidates: 0,
      contextClassifiedFindings: 0,
      riskAssessedFindings: 0,
      legalConclusionProvided: false,
    })
    expect(result.data.scan.pipelineStages?.find((stage) => stage.stage === 'assigning_owner')).toMatchObject({
      stage: 'assigning_owner',
      status: 'pending',
      processedFiles: 0,
    })
    expect(result.data.scan.ownerAssignment).toMatchObject({
      status: 'pending',
      policyPackVersion: '2026.05-demo',
      organizationModelVersion: '2026.05-demo',
      humanReviewRequiredFindings: 0,
      assignedFindings: 0,
      unownedFindings: 0,
    })
    expect(result.data.scan.ownerAssignment?.warnings).toContain('Owner assignment waits for completed context/risk judgment.')
    expect(result.data.scan.findingAssembly).toMatchObject({
      status: 'pending',
      policyPackVersion: '2026.05-demo',
      assembledFindings: 0,
      evidenceCards: 0,
      rawContentExposed: false,
      legalConclusionProvided: false,
    })
    expect(result.data.scan.findingAssembly?.warnings).toContain('Finding assembly waits for completed owner assignment and redacted signals.')
    expect(result.data.scan.pipelineStages?.find((stage) => stage.stage === 'judging_context_risk')).toMatchObject({
      stage: 'judging_context_risk',
      status: 'pending',
      processedFiles: 0,
    })
    expect(result.data.scan.pipelineStages?.find((stage) => stage.stage === 'assembling_findings')).toMatchObject({
      stage: 'assembling_findings',
      status: 'pending',
      processedFiles: 0,
    })
    expect(result.data.scan.pipelineStages?.find((stage) => stage.stage === 'preparing_review_support')).toMatchObject({
      stage: 'preparing_review_support',
      status: 'pending',
      processedFiles: 0,
    })
    expect(result.data.metrics).toMatchObject({
      totalScannedFiles: 14,
      flaggedFiles: 5,
      scanProgress: 0.34,
      lastScanTimeSeconds: null,
      inventoryCandidateFiles: 42,
      fingerprintedFiles: 14,
      extractedFiles: 12,
      extractionWarnings: 2,
      redactedEvidenceCandidates: 21,
      detectedSignals: 0,
      redactedSignals: 0,
      findingsWithSignals: 0,
      contextClassifiedFindings: 0,
      riskAssessedFindings: 0,
      humanReviewRequiredFindings: 0,
      ownerRoutedFindings: 0,
      assignedFindings: 0,
      directOwnerAssignments: 0,
      masterOfDataAssignments: 0,
      escalationAssignments: 0,
      assembledFindings: 0,
      evidenceCards: 0,
      reviewSupportedFindings: 0,
      deniedReviewActions: 0,
    })
    expect(result.data.meta.partial).toBe(true)
    expect(result.data.meta.warnings).toContain('Inventory is partial while the scan is running.')
    expect(result.data.meta.warnings).toContain('Extraction is partial while the scan is running.')
    expect(result.data.auditEvents[0]).toMatchObject({
      auditEventId: 'audit_started',
      scanId: 'scan_demo_full',
      findingId: null,
      eventType: 'full_scan_started',
      actorId: 'user_demo_admin',
      occurredAt: startedAt,
      policyPackVersion: '2026.05-demo',
    })
    expect(result.data.auditEvents[0].summary).toContain('Organizer GDPR Data Samples')
  })
})
