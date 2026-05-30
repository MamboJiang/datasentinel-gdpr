import type { MockData } from './mockApi'
import {
  buildAuditRecordingSummary,
  collectFindingTimelineEvents,
  prependAuditEvent,
  prependAuditEvents,
} from './auditEventRecording'
import { buildContentExtractionSummary } from './contentExtraction'
import { buildContextRiskSummary } from './contextRisk'
import { buildDeltaScanSummary, completeDeltaScanSummary, getDeltaScanBaseline } from './deltaScan'
import { assembleFindings, buildFindingAssemblySummary, createFindingAssemblyAuditEvent } from './findingAssembly'
import { buildFileInventorySummary } from './fileInventory'
import { buildOwnerAssignmentSummary } from './ownerRouting'
import { buildReviewSupport, buildReviewSupportSummary } from './reviewSupport'
import { createOwnerAssignmentAuditEvent, createScanAuditEvent } from './scanAudit'
import { updateEvaluation } from './scanEvaluation'
import { formatScanType } from './scanLabels'
import { buildSignalDetectionSummary } from './signalDetection'
import {
  getDefaultFullScanSource,
  isSourceScanReady,
  scanProfiles,
  type ScanType,
  type StartScanOptions,
} from './scanProfiles'
import { createPipelineStages } from './scanStages'
import { buildCompletedScanMetrics, buildRunningScanMetrics } from './scanWorkflowMetrics'
import {
  clearPartialMeta,
  createPartialMeta,
  getSourceConnectionMessage,
  normalizeScanType,
} from './scanWorkflowUtils'
import type { CompleteScanInput, StartScanInput, StartScanResult } from './scanWorkflowTypes'
import type { Scan } from '../types'

export { canStartDeltaScan } from './deltaScan'
export { getDefaultFullScanSource, getSourceConnectionMessage, isSourceScanReady }
export type { ScanType, StartScanOptions }

const demoReviewActorId = 'user_anna'

export function startScanWorkflow(current: MockData, input: StartScanInput): StartScanResult {
  const source = input.sourceId
    ? current.sources.find((candidate) => candidate.sourceId === input.sourceId)
    : getDefaultFullScanSource(current.sources, current.governanceConfig)

  if (!source) {
    return {
      accepted: false,
      data: current,
      toast: 'Full scan is unavailable until a mock-ready source is selected.',
    }
  }

  if (!isSourceScanReady(source, current.governanceConfig)) {
    return {
      accepted: false,
      data: current,
      toast: `${source.name} is not scan-ready in this P0 workflow.`,
    }
  }

  const profile = scanProfiles[input.scanType]
  const deltaBaseline = input.scanType === 'delta'
    ? getDeltaScanBaseline(current.scan, source.sourceId)
    : null

  if (input.scanType === 'delta' && !deltaBaseline) {
    return {
      accepted: false,
      data: current,
      toast: `Delta scan requires a completed full-scan baseline for ${source.name}.`,
    }
  }

  if (input.scanType === 'delta' && input.baselineScanId && input.baselineScanId !== deltaBaseline?.baselineScanId) {
    return {
      accepted: false,
      data: current,
      toast: `Delta scan baseline ${input.baselineScanId} is not available for ${source.name}.`,
    }
  }

  if (current.scan.status === 'running' && current.scan.sourceId === source.sourceId && current.scan.scanType === input.scanType) {
    return {
      accepted: false,
      data: current,
      toast: `${formatScanType(input.scanType)} scan is already running for ${source.name}.`,
    }
  }

  const deltaScan = deltaBaseline
    ? buildDeltaScanSummary({ baseline: deltaBaseline, profile, state: 'running' })
    : undefined
  const fileInventory = buildFileInventorySummary(source, profile, 'running')
  const contentExtraction = buildContentExtractionSummary(input.scanType, fileInventory, 'running')
  const signalDetection = buildSignalDetectionSummary(
    fileInventory,
    contentExtraction,
    current.governanceConfig,
    'pending',
  )
  const contextRisk = buildContextRiskSummary(
    input.scanType,
    fileInventory,
    contentExtraction,
    current.governanceConfig,
    'pending',
  )
  const ownerAssignment = buildOwnerAssignmentSummary(
    input.scanType,
    source,
    contextRisk,
    current.governanceConfig,
    'pending',
  )
  const findingAssembly = buildFindingAssemblySummary({
    contentExtraction,
    contextRisk,
    governanceConfig: current.governanceConfig,
    occurredAt: input.occurredAt,
    ownerAssignment,
    scan: {
      scanId: profile.scanId,
      sourceId: source.sourceId,
      scanType: input.scanType,
      status: 'running',
      progress: profile.progress,
      fileInventory,
    },
    source,
    state: 'pending',
  })
  const reviewSupport = buildReviewSupportSummary({
    actorId: current.permissionBoundary.actorId,
    findingAssembly,
    governanceConfig: current.governanceConfig,
    permissionBoundary: current.permissionBoundary,
    state: 'pending',
  })
  const auditEvent = createScanAuditEvent({
    actorId: input.actorId,
    auditEventId: input.auditEventId,
    eventType: `${input.scanType}_scan_started`,
    occurredAt: input.occurredAt,
    scanId: profile.scanId,
    sourceId: source.sourceId,
    sourceName: source.name,
    scanType: input.scanType,
    previousState: current.scan.status,
    policyPackVersion: current.governanceConfig.activePolicyPack.version,
  })
  const nextAuditEvents = prependAuditEvent(current.auditEvents, auditEvent)
  const auditRecording = buildAuditRecordingSummary({
    auditEvents: nextAuditEvents,
    policyPackVersion: current.governanceConfig.activePolicyPack.version,
    scanId: profile.scanId,
    state: 'pending',
  })
  const runningScan: Scan = {
    scanId: profile.scanId,
    sourceId: source.sourceId,
    scanType: input.scanType,
    status: 'running',
    stage: 'extracting_content',
    progress: profile.progress,
    totalFiles: profile.totalFiles,
    scannedFiles: profile.scannedFiles,
    flaggedFiles: profile.flaggedFiles,
    totalBytes: profile.totalBytes,
    durationMs: null,
    throughputFilesPerSecond: null,
    reproducibilityFingerprint: null,
    pipelineStages: createPipelineStages(fileInventory, contentExtraction, signalDetection, contextRisk, ownerAssignment, findingAssembly, reviewSupport, auditRecording, false, deltaScan),
    fileInventory,
    contentExtraction,
    signalDetection,
    contextRisk,
    ownerAssignment,
    findingAssembly,
    reviewSupport,
    auditRecording,
    deltaScan,
  }

  return {
    accepted: true,
    completionDelayMs: profile.completionDelayMs,
    data: {
      ...current,
      scan: runningScan,
      metrics: buildRunningScanMetrics({
        auditRecording,
        contentExtraction,
        contextRisk,
        currentMetrics: current.metrics,
        deltaScan,
        fileInventory,
        findingAssembly,
        ownerAssignment,
        profile,
        reviewSupport,
        signalDetection,
      }),
      auditEvents: nextAuditEvents,
      meta: createPartialMeta(current.meta, [
        ...(deltaScan?.warnings ?? []),
        ...fileInventory.warnings,
        ...contentExtraction.warnings,
      ]),
    },
    scanId: runningScan.scanId,
    toast: `${formatScanType(input.scanType)} scan started for ${source.name}.`,
  }
}

export function completeScanWorkflow(current: MockData, input: CompleteScanInput): MockData {
  if (current.scan.scanId !== input.scanId || current.scan.status !== 'running') {
    return current
  }

  const scanType = normalizeScanType(current.scan.scanType)
  const profile = scanProfiles[scanType]
  const source = current.sources.find((candidate) => candidate.sourceId === current.scan.sourceId)
  const fallbackSource = source ?? {
    sourceId: current.scan.sourceId,
    name: 'Configured source',
    sourceType: 'unknown',
    status: 'unknown',
  }
  const fileInventory = buildFileInventorySummary(
    fallbackSource,
    { ...profile, flaggedFiles: profile.completedFlaggedFiles },
    'completed',
  )
  const contentExtraction = buildContentExtractionSummary(scanType, fileInventory, 'completed')
  const signalDetection = buildSignalDetectionSummary(
    fileInventory,
    contentExtraction,
    current.governanceConfig,
    'completed',
  )
  const contextRisk = buildContextRiskSummary(scanType, fileInventory, contentExtraction, current.governanceConfig, 'completed')
  const ownerAssignment = buildOwnerAssignmentSummary(scanType, fallbackSource, contextRisk, current.governanceConfig, 'completed')
  const deltaScan = completeDeltaScanSummary(current.scan, profile)
  const baseCompletedScan: Scan = {
    ...current.scan,
    status: 'completed',
    stage: 'completed',
    progress: 1,
    scannedFiles: profile.totalFiles,
    flaggedFiles: profile.completedFlaggedFiles,
    durationMs: profile.durationMs,
    throughputFilesPerSecond: profile.throughputFilesPerSecond,
    reproducibilityFingerprint: scanType === 'delta' ? 'sha256:demo_delta_findings' : 'sha256:demo_findings',
    fileInventory,
    contentExtraction,
    signalDetection,
    contextRisk,
    ownerAssignment,
    deltaScan,
  }
  const assembly = assembleFindings({
    contentExtraction,
    contextRisk,
    governanceConfig: current.governanceConfig,
    occurredAt: input.occurredAt,
    ownerAssignment,
    scan: baseCompletedScan,
    source: fallbackSource,
    state: 'completed',
  })
  const primaryFinding = assembly.findingDetails.finding_001 ?? Object.values(assembly.findingDetails)[0]
  const findingReviewSupport = primaryFinding
    ? buildReviewSupport({
        actorId: demoReviewActorId,
        finding: primaryFinding,
        governanceConfig: current.governanceConfig,
        occurredAt: input.occurredAt,
      })
    : current.reviewSupport
  const permissionBoundary = findingReviewSupport.permissionBoundary ?? current.permissionBoundary
  const reviewSupport = buildReviewSupportSummary({
    actorId: findingReviewSupport.actorId,
    findingAssembly: assembly.summary,
    governanceConfig: current.governanceConfig,
    permissionBoundary,
    state: 'completed',
  })
  const auditEvent = createScanAuditEvent({
    actorId: 'system',
    auditEventId: input.auditEventId,
    eventType: `${scanType}_scan_completed`,
    occurredAt: input.occurredAt,
    scanId: baseCompletedScan.scanId,
    sourceId: fallbackSource.sourceId,
    sourceName: source?.name ?? 'configured source',
    scanType,
    previousState: current.scan.status,
    policyPackVersion: current.governanceConfig.activePolicyPack.version,
  })
  const ownerAssignmentEvent = createOwnerAssignmentAuditEvent({
    actorId: 'system',
    auditEventId: `${input.auditEventId}_owner_assignment`,
    occurredAt: input.occurredAt,
    ownerAssignment,
    scanId: baseCompletedScan.scanId,
  })
  const findingAssemblyEvent = createFindingAssemblyAuditEvent({
    actorId: 'system',
    auditEventId: `${input.auditEventId}_finding_assembly`,
    occurredAt: input.occurredAt,
    findingAssembly: assembly.summary,
    scanId: baseCompletedScan.scanId,
  })
  const nextAuditEvents = prependAuditEvents(current.auditEvents, [
    auditEvent,
    ownerAssignmentEvent,
    findingAssemblyEvent,
    ...collectFindingTimelineEvents(assembly.findingDetails),
  ])
  const auditRecording = buildAuditRecordingSummary({
    auditEvents: nextAuditEvents,
    policyPackVersion: current.governanceConfig.activePolicyPack.version,
    scanId: baseCompletedScan.scanId,
    state: 'completed',
  })
  const scanWithSummaries: Scan = {
    ...baseCompletedScan,
    findingAssembly: assembly.summary,
    reviewSupport,
    auditRecording,
  }
  const evaluation = updateEvaluation({
    auditRecording,
    completedScan: scanWithSummaries,
    contentExtraction,
    contextRisk,
    currentMetrics: current.metrics,
    current: current.evaluation,
    deltaScan,
    fileInventory,
    findingAssembly: assembly.summary,
    ownerAssignment,
    reviewSupport,
    signalDetection,
  })
  const completedScan: Scan = {
    ...scanWithSummaries,
    pipelineStages: createPipelineStages(fileInventory, contentExtraction, signalDetection, contextRisk, ownerAssignment, assembly.summary, reviewSupport, auditRecording, true, deltaScan, evaluation),
  }

  return {
    ...current,
    scan: completedScan,
    findings: assembly.findings,
    findingDetail: primaryFinding ?? current.findingDetail,
    findingDetails: assembly.findingDetails,
    permissionBoundary,
    reviewSupport: findingReviewSupport,
    metrics: buildCompletedScanMetrics({
      auditRecording,
      contentExtraction,
      contextRisk,
      currentMetrics: current.metrics,
      deltaScan,
      evaluation,
      fileInventory,
      findingAssembly: assembly.summary,
      ownerAssignment,
      profile,
      reviewSupport,
      signalDetection,
    }),
    evaluation,
    auditEvents: nextAuditEvents,
    meta: clearPartialMeta(current.meta),
  }
}
