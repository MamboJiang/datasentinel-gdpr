import { describe, expect, it } from 'vitest'
import { getInitialMockData, type MockData } from './mockApi'
import { completeScanWorkflow, startScanWorkflow } from './scanWorkflow'
import type { StartScanOptions } from './scanProfiles'

const startedAt = '2026-05-30T13:10:00.000Z'
const completedAt = '2026-05-30T13:10:05.200Z'

function startDeltaScan(data: MockData = getInitialMockData(), options: Partial<StartScanOptions> = {}) {
  return startScanWorkflow(data, {
    actorId: 'user_demo_admin',
    auditEventId: 'audit_delta_started',
    occurredAt: startedAt,
    scanType: 'delta',
    sourceId: 'source_001',
    ...options,
  })
}

describe('delta scan workflow', () => {
  it('starts a changed-file-only scan from a completed full-scan baseline', () => {
    const result = startDeltaScan()

    expect(result.accepted).toBe(true)

    if (!result.accepted) {
      return
    }

    expect(result.data.scan).toMatchObject({
      scanId: 'scan_demo_delta',
      sourceId: 'source_001',
      scanType: 'delta',
      status: 'running',
      totalFiles: 6,
      scannedFiles: 4,
      flaggedFiles: 2,
    })
    expect(result.data.scan.deltaScan).toMatchObject({
      status: 'running',
      baselineScanId: 'scan_001',
      baselineTotalFiles: 42,
      baselineFindingCount: 17,
      changedFiles: 6,
      newFiles: 2,
      modifiedFiles: 4,
      unchangedFiles: 35,
      missingFiles: 1,
      processedChangedFiles: 4,
      carriedForwardFiles: 35,
      missingFilesTreatedAsDeleted: false,
      rawContentExposed: false,
      legalConclusionProvided: false,
      deletionExecuted: false,
    })
    expect(result.data.scan.pipelineStages?.map((stage) => stage.stage).slice(0, 3)).toEqual([
      'source_ready',
      'comparing_delta_baseline',
      'inventorying_files',
    ])
    expect(result.data.metrics).toMatchObject({
      totalScannedFiles: 4,
      flaggedFiles: 2,
      deltaBaselineFiles: 42,
      deltaChangedFiles: 6,
      deltaNewFiles: 2,
      deltaModifiedFiles: 4,
      deltaUnchangedFiles: 35,
      deltaMissingFiles: 1,
      deltaProcessedChangedFiles: 4,
    })
    expect(result.data.meta.partial).toBe(true)
    expect(result.data.meta.warnings).toContain('Delta comparison is partial while the changed-file scan is running.')
    expect(result.data.auditEvents[0]).toMatchObject({
      eventType: 'delta_scan_started',
      actorId: 'user_demo_admin',
      scanId: 'scan_demo_delta',
      policyPackVersion: '2026.05-demo',
    })
  })

  it('completes delta processing without treating unchanged or missing files as new findings or deletion', () => {
    const started = startDeltaScan()

    if (!started.accepted) {
      throw new Error('Expected delta scan start to be accepted.')
    }

    const completed = completeScanWorkflow(started.data, {
      auditEventId: 'audit_delta_completed',
      occurredAt: completedAt,
      scanId: started.scanId,
    })

    expect(completed.scan).toMatchObject({
      scanId: 'scan_demo_delta',
      scanType: 'delta',
      status: 'completed',
      scannedFiles: 6,
      flaggedFiles: 2,
      durationMs: 5200,
      throughputFilesPerSecond: 1.15,
      reproducibilityFingerprint: 'sha256:demo_delta_findings',
    })
    expect(completed.scan.deltaScan).toMatchObject({
      status: 'completed',
      baselineScanId: 'scan_001',
      changedFiles: 6,
      unchangedFiles: 35,
      missingFiles: 1,
      processedChangedFiles: 6,
      reopenedFindings: 2,
      unchangedFindingsCarriedForward: 15,
      missingFilesTreatedAsDeleted: false,
      deletionExecuted: false,
    })
    expect(completed.scan.contextRisk).toMatchObject({
      highRiskFindings: 1,
      mediumRiskFindings: 1,
      lowRiskFindings: 0,
      legalConclusionProvided: false,
    })
    expect(completed.scan.ownerAssignment).toMatchObject({
      assignedFindings: 2,
      unownedFindings: 0,
    })
    expect(completed.scan.findingAssembly).toMatchObject({
      assembledFindings: 2,
      evidenceCards: 2,
      rawContentExposed: false,
      legalConclusionProvided: false,
    })
    expect(completed.findings).toHaveLength(2)
    expect(completed.findings.every((finding) => finding.scanId === 'scan_demo_delta')).toBe(true)
    expect(completed.metrics).toMatchObject({
      totalScannedFiles: 6,
      flaggedFiles: 2,
      deltaBaselineFiles: 42,
      deltaChangedFiles: 6,
      deltaProcessedChangedFiles: 6,
      deltaReopenedFindings: 2,
      deltaCarriedForwardFindings: 15,
    })
    expect(completed.evaluation).toMatchObject({
      scanId: 'scan_demo_delta',
      deltaScanRulesHash: completed.scan.deltaScan?.deltaFingerprint,
      findingFingerprint: 'sha256:demo_delta_findings',
      throughputFilesPerSecond: 1.15,
    })
    expect(completed.evaluation.resourceIntensity).toMatchObject({
      modelCalls: 0,
      estimatedCostUsd: 0,
    })
    expect(completed.auditEvents[0]).toMatchObject({
      auditEventId: 'audit_delta_completed',
      eventType: 'delta_scan_completed',
      actorId: 'system',
      scanId: 'scan_demo_delta',
    })
    expect(completed.auditEvents.some((event) => event.action === 'execute_real_deletion')).toBe(false)
  })

  it('rejects delta start before a completed baseline is available', () => {
    const fullStart = startScanWorkflow(getInitialMockData(), {
      actorId: 'user_demo_admin',
      auditEventId: 'audit_full_started',
      occurredAt: startedAt,
      scanType: 'full',
      sourceId: 'source_001',
    })

    if (!fullStart.accepted) {
      throw new Error('Expected full scan start to be accepted.')
    }

    const rejected = startDeltaScan(fullStart.data)

    expect(rejected.accepted).toBe(false)
    expect(rejected.data).toBe(fullStart.data)
    expect(rejected.toast).toContain('requires a completed full-scan baseline')
  })

  it('rejects an unavailable explicit delta baseline', () => {
    const rejected = startDeltaScan(getInitialMockData(), { baselineScanId: 'scan_missing' })

    expect(rejected.accepted).toBe(false)
    expect(rejected.toast).toContain('scan_missing')
  })
})
