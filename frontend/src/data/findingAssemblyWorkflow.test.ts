import { describe, expect, it } from 'vitest'
import { getInitialMockData, type MockData } from './mockApi'
import {
  completeScanWorkflow,
  getSourceConnectionMessage,
  startScanWorkflow,
} from './scanWorkflow'

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

function completeStartedScan(data: MockData = getInitialMockData()) {
  const started = startFullScan(data)

  if (!started.accepted) {
    throw new Error('Expected full scan start to be accepted.')
  }

  return completeScanWorkflow(started.data, {
    auditEventId: 'audit_completed',
    occurredAt: completedAt,
    scanId: started.scanId,
  })
}

describe('finding assembly workflow continuity', () => {
  it('rejects a not-ready source without changing scan or audit state', () => {
    const data = getInitialMockData()
    const result = startScanWorkflow(data, {
      actorId: 'user_demo_admin',
      auditEventId: 'audit_blocked',
      occurredAt: startedAt,
      scanType: 'full',
      sourceId: 'source_002',
    })

    expect(result.accepted).toBe(false)
    expect(result.data.scan).toEqual(data.scan)
    expect(result.data.metrics).toEqual(data.metrics)
    expect(result.data.auditEvents).toHaveLength(data.auditEvents.length)
    expect(result.toast).toBe('Mock SharePoint Finance is not scan-ready in this P0 workflow.')
  })

  it('keeps extraction output redacted and recoverable when files are unsupported or OCR-deferred', () => {
    const started = startFullScan()

    if (!started.accepted) {
      throw new Error('Expected full scan start to be accepted.')
    }

    const extraction = started.data.scan.contentExtraction

    expect(extraction?.rawContentExposed).toBe(false)
    expect(extraction?.unsupportedFiles).toBe(1)
    expect(extraction?.ocrDeferredFiles).toBe(1)
    expect(extraction?.warnings.join(' ')).not.toContain('IBAN')
    expect(extraction?.warnings.join(' ')).not.toContain('@example.com')
  })

  it('keeps context/risk output policy-backed, redacted, and non-legal', () => {
    const completed = completeStartedScan()
    const contextRisk = completed.scan.contextRisk
    const serialized = JSON.stringify(contextRisk)

    expect(contextRisk?.policyPackVersion).toBe(completed.governanceConfig.activePolicyPack.version)
    expect(contextRisk?.legalConclusionProvided).toBe(false)
    expect(contextRisk?.warnings).toEqual([])
    expect(serialized).not.toContain('IBAN')
    expect(serialized).not.toContain('@example.com')
    expect(completed.evaluation.resourceIntensity).toMatchObject({
      modelCalls: 0,
      estimatedCostUsd: 0,
    })
  })

  it('keeps owner routing accountable, redacted, and zero-cost', () => {
    const completed = completeStartedScan()
    const ownerAssignment = completed.scan.ownerAssignment
    const serialized = JSON.stringify(ownerAssignment)

    expect(ownerAssignment?.policyPackVersion).toBe(completed.governanceConfig.activePolicyPack.version)
    expect(ownerAssignment?.organizationModelVersion).toBe(completed.governanceConfig.organizationModel.version)
    expect(ownerAssignment?.assignedFindings).toBe(completed.scan.contextRisk?.humanReviewRequiredFindings)
    expect(ownerAssignment?.unownedFindings).toBe(0)
    expect(ownerAssignment?.masterOfDataAssignments).toBeGreaterThan(0)
    expect(ownerAssignment?.escalationAssignments).toBeGreaterThan(0)
    expect(completed.auditEvents.some((event) => event.eventType === 'owner_assignment_completed')).toBe(true)
    expect(completed.evaluation.ownerAssignmentRulesHash).toBe(ownerAssignment?.assignmentRulesFingerprint)
    expect(serialized).not.toContain('IBAN')
    expect(serialized).not.toContain('@example.com')
    expect(completed.evaluation.resourceIntensity).toMatchObject({
      modelCalls: 0,
      estimatedCostUsd: 0,
    })
  })

  it('assembles evidence cards from prior stage outputs without raw content or model cost', () => {
    const completed = completeStartedScan()
    const assembly = completed.scan.findingAssembly
    const detailSignals = Object.values(completed.findingDetails).flatMap((finding) => finding.signals ?? [])
    const serializedSignals = JSON.stringify(detailSignals)

    expect(assembly?.assembledFindings).toBe(completed.scan.ownerAssignment?.assignedFindings)
    expect(assembly?.evidenceCards).toBe(completed.findings.length)
    expect(assembly?.evidenceSignals).toBe(detailSignals.length)
    expect(assembly?.rawContentExposed).toBe(false)
    expect(assembly?.legalConclusionProvided).toBe(false)
    expect(completed.evaluation.findingAssemblyRulesHash).toBe(assembly?.assemblyRulesFingerprint)
    expect(serializedSignals).not.toContain('@example.com')
    expect(serializedSignals).not.toContain('DE89')
    expect(detailSignals.every((signal) => signal.snippet.includes('[REDACTED'))).toBe(true)
    expect(completed.evaluation.resourceIntensity).toMatchObject({
      modelCalls: 0,
      estimatedCostUsd: 0,
    })
  })

  it('routes to escalation instead of leaving findings unowned when source owner metadata is missing', () => {
    const data = getInitialMockData()
    const ownerlessData: MockData = {
      ...data,
      sources: data.sources.map((source) =>
        source.sourceId === 'source_001'
          ? { ...source, masterOfDataUserId: null }
          : source,
      ),
    }
    const completed = completeStartedScan(ownerlessData)

    expect(completed.scan.ownerAssignment).toMatchObject({
      assignedFindings: 17,
      directOwnerAssignments: 0,
      masterOfDataAssignments: 0,
      escalationAssignments: 17,
      unownedFindings: 0,
      sourceOwnerAvailable: false,
    })
    expect(completed.scan.ownerAssignment?.warnings).toContain('Source Master of Data is missing; review-required findings route to escalation.')
    expect(Object.values(completed.findingDetails).every((finding) => finding.owner?.assignmentType === 'escalation_queue')).toBe(true)
    expect(completed.scan.findingAssembly?.missingEvidenceCards).toBe(0)
  })

  it('does not create duplicate audit events for the same running scan', () => {
    const started = startFullScan()

    if (!started.accepted) {
      throw new Error('Expected full scan start to be accepted.')
    }

    const duplicate = startScanWorkflow(started.data, {
      actorId: 'user_demo_admin',
      auditEventId: 'audit_duplicate',
      occurredAt: startedAt,
      scanType: 'full',
      sourceId: 'source_001',
    })

    expect(duplicate.accepted).toBe(false)
    expect(duplicate.data.auditEvents[0].auditEventId).toBe('audit_started')
    expect(duplicate.data.auditEvents).toHaveLength(started.data.auditEvents.length)
  })

  it('can target a selected source when that source is explicitly made scan-ready', () => {
    const data = getInitialMockData()
    const selectedSourceData: MockData = {
      ...data,
      sources: data.sources.map((source) =>
        source.sourceId === 'source_002'
          ? { ...source, status: 'mock_ready' }
          : source,
      ),
      governanceConfig: {
        ...data.governanceConfig,
        sourceAdapters: [
          ...data.governanceConfig.sourceAdapters,
          {
            sourceType: 'sharepoint_mock',
            label: 'Mock SharePoint Finance',
            status: 'mock_ready',
          },
        ],
      },
    }

    const result = startScanWorkflow(selectedSourceData, {
      actorId: 'user_demo_admin',
      auditEventId: 'audit_selected_source',
      occurredAt: startedAt,
      scanType: 'full',
      sourceId: 'source_002',
    })

    expect(result.accepted).toBe(true)

    if (!result.accepted) {
      return
    }

    expect(result.data.scan.sourceId).toBe('source_002')
    expect(result.data.auditEvents[0].summary).toContain('Mock SharePoint Finance')
  })

  it('reports source connection readiness without creating workflow state', () => {
    const data = getInitialMockData()

    expect(getSourceConnectionMessage(data.sources[0], data.governanceConfig)).toBe(
      'Organizer GDPR Data Samples is mock-ready for full scan.',
    )
    expect(getSourceConnectionMessage(data.sources[1], data.governanceConfig)).toBe(
      'Mock SharePoint Finance is not scan-ready in this P0 workflow.',
    )
  })
})
