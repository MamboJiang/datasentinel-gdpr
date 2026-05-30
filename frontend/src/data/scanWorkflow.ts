import type { MockData } from './mockApi'
import {
  buildAuditRecordingSummary,
  collectFindingTimelineEvents,
  prependAuditEvent,
  prependAuditEvents,
} from './auditEventRecording'
import { buildContentExtractionSummary } from './contentExtraction'
import { buildContextRiskSummary } from './contextRisk'
import { assembleFindings, buildFindingAssemblySummary, createFindingAssemblyAuditEvent } from './findingAssembly'
import { buildFileInventorySummary } from './fileInventory'
import { buildOwnerAssignmentSummary } from './ownerRouting'
import { buildReviewSupport, buildReviewSupportSummary } from './reviewSupport'
import { createOwnerAssignmentAuditEvent, createScanAuditEvent } from './scanAudit'
import { updateEvaluation } from './scanEvaluation'
import { formatScanType } from './scanLabels'
import {
  getDefaultFullScanSource,
  isSourceScanReady,
  scanProfiles,
  type ScanType,
  type StartScanOptions,
} from './scanProfiles'
import { createPipelineStages } from './scanStages'
import {
  calculateScannedGb,
  clearPartialMeta,
  createPartialMeta,
  getSourceConnectionMessage,
  normalizeScanType,
} from './scanWorkflowUtils'
import type { Scan } from '../types'

export { getDefaultFullScanSource, getSourceConnectionMessage, isSourceScanReady }
export type { ScanType, StartScanOptions }

type StartScanInput = StartScanOptions & {
  actorId: string
  auditEventId: string
  occurredAt: string
}

type CompleteScanInput = {
  auditEventId: string
  occurredAt: string
  scanId: string
}

type StartScanAccepted = {
  accepted: true
  completionDelayMs: number
  data: MockData
  scanId: string
  toast: string
}

type StartScanRejected = {
  accepted: false
  data: MockData
  toast: string
}

export type StartScanResult = StartScanAccepted | StartScanRejected

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

  if (current.scan.status === 'running' && current.scan.sourceId === source.sourceId && current.scan.scanType === input.scanType) {
    return {
      accepted: false,
      data: current,
      toast: `${formatScanType(input.scanType)} scan is already running for ${source.name}.`,
    }
  }

  const fileInventory = buildFileInventorySummary(source, profile, 'running')
  const contentExtraction = buildContentExtractionSummary(input.scanType, fileInventory, 'running')
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
    pipelineStages: createPipelineStages(fileInventory, contentExtraction, contextRisk, ownerAssignment, findingAssembly, reviewSupport, auditRecording, false),
    fileInventory,
    contentExtraction,
    contextRisk,
    ownerAssignment,
    findingAssembly,
    reviewSupport,
    auditRecording,
  }

  return {
    accepted: true,
    completionDelayMs: profile.completionDelayMs,
    data: {
      ...current,
      scan: runningScan,
      metrics: {
        ...current.metrics,
        totalScannedFiles: profile.scannedFiles,
        flaggedFiles: profile.flaggedFiles,
        totalScannedGb: calculateScannedGb(profile.totalBytes, profile.progress),
        scanProgress: profile.progress,
        lastScanTimeSeconds: null,
        inventoryCandidateFiles: fileInventory.totalCandidateFiles,
        fingerprintedFiles: fileInventory.fingerprintedFiles,
        extractedFiles: contentExtraction.successfulFiles,
        extractionWarnings: contentExtraction.warningFiles,
        redactedEvidenceCandidates: contentExtraction.redactedEvidenceCandidates,
        contextClassifiedFindings: contextRisk.contextClassifiedFindings,
        riskAssessedFindings: contextRisk.riskAssessedFindings,
        humanReviewRequiredFindings: contextRisk.humanReviewRequiredFindings,
        ownerRoutedFindings: ownerAssignment.assignedFindings,
        assignedFindings: ownerAssignment.assignedFindings,
        directOwnerAssignments: ownerAssignment.directOwnerAssignments,
        masterOfDataAssignments: ownerAssignment.masterOfDataAssignments,
        escalationAssignments: ownerAssignment.escalationAssignments,
        assembledFindings: findingAssembly.assembledFindings,
        evidenceCards: findingAssembly.evidenceCards,
        reviewSupportedFindings: reviewSupport.supportedFindings,
        deniedReviewActions: reviewSupport.deniedActionCount,
        reviewChecklistItems: reviewSupport.checklistItemCount,
        reviewTransferOptions: reviewSupport.transferOptionCount,
        reviewEscalationOptions: reviewSupport.escalationOptionCount,
        auditRecordedEvents: auditRecording.recordedEventCount,
        auditLinkedFindingEvents: auditRecording.linkedFindingEvents,
        auditReviewDecisionEvents: auditRecording.reviewDecisionEvents,
      },
      auditEvents: nextAuditEvents,
      meta: createPartialMeta(current.meta, [
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
  const contextRisk = buildContextRiskSummary(
    scanType,
    fileInventory,
    contentExtraction,
    current.governanceConfig,
    'completed',
  )
  const ownerAssignment = buildOwnerAssignmentSummary(
    scanType,
    fallbackSource,
    contextRisk,
    current.governanceConfig,
    'completed',
  )
  const baseCompletedScan: Scan = {
    ...current.scan,
    status: 'completed',
    stage: 'completed',
    progress: 1,
    scannedFiles: profile.totalFiles,
    flaggedFiles: profile.completedFlaggedFiles,
    durationMs: profile.durationMs,
    throughputFilesPerSecond: profile.throughputFilesPerSecond,
    reproducibilityFingerprint: 'sha256:demo_findings',
    fileInventory,
    contentExtraction,
    contextRisk,
    ownerAssignment,
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
  const completedScan: Scan = {
    ...baseCompletedScan,
    pipelineStages: createPipelineStages(fileInventory, contentExtraction, contextRisk, ownerAssignment, assembly.summary, reviewSupport, auditRecording, true),
    findingAssembly: assembly.summary,
    reviewSupport,
    auditRecording,
  }
  const evaluation = updateEvaluation(current.evaluation, completedScan, fileInventory, contentExtraction, contextRisk, ownerAssignment, assembly.summary, reviewSupport, auditRecording)

  return {
    ...current,
    scan: completedScan,
    findings: assembly.findings,
    findingDetail: primaryFinding ?? current.findingDetail,
    findingDetails: assembly.findingDetails,
    permissionBoundary,
    reviewSupport: findingReviewSupport,
    metrics: {
      ...current.metrics,
      totalScannedFiles: profile.totalFiles,
      flaggedFiles: profile.completedFlaggedFiles,
      totalScannedGb: calculateScannedGb(profile.totalBytes, 1),
      scanProgress: 1,
      lastScanTimeSeconds: profile.durationMs / 1000,
      inventoryCandidateFiles: fileInventory.totalCandidateFiles,
      fingerprintedFiles: fileInventory.fingerprintedFiles,
      extractedFiles: contentExtraction.successfulFiles,
      extractionWarnings: contentExtraction.warningFiles,
      redactedEvidenceCandidates: contentExtraction.redactedEvidenceCandidates,
      contextClassifiedFindings: contextRisk.contextClassifiedFindings,
      riskAssessedFindings: contextRisk.riskAssessedFindings,
      highRiskFindings: contextRisk.highRiskFindings,
      retentionOverdueFiles: contextRisk.retentionReviewFiles,
      humanReviewRequiredFindings: contextRisk.humanReviewRequiredFindings,
      ownerRoutedFindings: ownerAssignment.assignedFindings,
      assignedFindings: ownerAssignment.assignedFindings,
      directOwnerAssignments: ownerAssignment.directOwnerAssignments,
      masterOfDataAssignments: ownerAssignment.masterOfDataAssignments,
      escalationAssignments: ownerAssignment.escalationAssignments,
      assembledFindings: assembly.summary.assembledFindings,
      evidenceCards: assembly.summary.evidenceCards,
      reviewSupportedFindings: reviewSupport.supportedFindings,
      deniedReviewActions: reviewSupport.deniedActionCount,
      reviewChecklistItems: reviewSupport.checklistItemCount,
      reviewTransferOptions: reviewSupport.transferOptionCount,
      reviewEscalationOptions: reviewSupport.escalationOptionCount,
      auditRecordedEvents: auditRecording.recordedEventCount,
      auditLinkedFindingEvents: auditRecording.linkedFindingEvents,
      auditReviewDecisionEvents: auditRecording.reviewDecisionEvents,
      evaluation,
    },
    evaluation,
    auditEvents: nextAuditEvents,
    meta: clearPartialMeta(current.meta),
  }
}
