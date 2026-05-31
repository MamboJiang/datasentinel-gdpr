import adminMetricsEnvelope from '../../../contracts/mocks/adminMetrics.json'
import auditEventsEnvelope from '../../../contracts/mocks/auditEvents.json'
import evaluationEnvelope from '../../../contracts/mocks/evaluationLatest.json'
import findingDetailEnvelope from '../../../contracts/mocks/findingDetail.json'
import findingsEnvelope from '../../../contracts/mocks/myFindings.json'
import governanceConfigEnvelope from '../../../contracts/mocks/governanceConfig.json'
import permissionBoundaryEnvelope from '../../../contracts/mocks/permissionBoundary.json'
import reviewSupportEnvelope from '../../../contracts/mocks/reviewSupport.json'
import scanEnvelope from '../../../contracts/mocks/scanStatus.json'
import sourcesEnvelope from '../../../contracts/mocks/sources.json'
import workspaceAdminEnvelope from '../../../contracts/mocks/workspaceAdmin.json'
import workspaceDirectoryEnvelope from '../../../contracts/mocks/workspaceDirectory.json'
import {
  buildAuditRecordingSummary,
  collectFindingTimelineEvents,
  deduplicateAuditEvents,
} from './auditEventRecording'
import { buildAdminMetricsAggregation } from './adminMetricsAggregation'
import { assembleFindings } from './findingAssembly'
import { buildReviewSupport, buildReviewSupportSummary } from './reviewSupport'
import { updateEvaluation } from './scanEvaluation'
import type {
  AdminMetrics,
  AuditEvent,
  EvaluationSummary,
  Finding,
  FindingSummary,
  Meta,
  Scan,
  Source,
  GovernanceConfig,
  PermissionBoundary,
  ReviewSupport,
  WorkspaceAdminSummary,
  WorkspaceDirectory,
} from '../types'

export type MockData = {
  sources: Source[]
  scan: Scan
  findings: FindingSummary[]
  findingDetail: Finding
  findingDetails: Record<string, Finding>
  auditEvents: AuditEvent[]
  metrics: AdminMetrics
  evaluation: EvaluationSummary
  governanceConfig: GovernanceConfig
  permissionBoundary: PermissionBoundary
  reviewSupport: ReviewSupport
  workspaceDirectory: WorkspaceDirectory
  workspaceAdmin: WorkspaceAdminSummary
  meta: Meta
}

const fixtures: MockData = {
  sources: sourcesEnvelope.data,
  scan: scanEnvelope.data,
  findings: findingsEnvelope.data,
  findingDetail: findingDetailEnvelope.data as Finding,
  findingDetails: {
    [findingDetailEnvelope.data.findingId]: findingDetailEnvelope.data as Finding,
  },
  auditEvents: auditEventsEnvelope.data as AuditEvent[],
  metrics: adminMetricsEnvelope.data,
  evaluation: evaluationEnvelope.data,
  governanceConfig: governanceConfigEnvelope.data,
  permissionBoundary: permissionBoundaryEnvelope.data,
  reviewSupport: reviewSupportEnvelope.data as ReviewSupport,
  workspaceDirectory: workspaceDirectoryEnvelope.data as WorkspaceDirectory,
  workspaceAdmin: workspaceAdminEnvelope.data as WorkspaceAdminSummary,
  meta: sourcesEnvelope.meta,
}

export function getInitialMockData(): MockData {
  const data = structuredClone(fixtures)

  if (
    data.scan.status !== 'completed'
    || !data.scan.fileInventory
    || !data.scan.contentExtraction
    || !data.scan.signalDetection
    || !data.scan.contextRisk
    || !data.scan.ownerAssignment
  ) {
    return data
  }

  const source = data.sources.find((candidate) => candidate.sourceId === data.scan.sourceId) ?? data.sources[0]

  if (!source) {
    return data
  }

  const assembly = assembleFindings({
    contentExtraction: data.scan.contentExtraction,
    contextRisk: data.scan.contextRisk,
    governanceConfig: data.governanceConfig,
    occurredAt: data.meta.generatedAt,
    ownerAssignment: data.scan.ownerAssignment,
    scan: data.scan,
    source,
    state: 'completed',
  })
  const findingDetail = assembly.findingDetails.finding_001 ?? Object.values(assembly.findingDetails)[0] ?? data.findingDetail
  const reviewSupport = buildReviewSupport({
    actorId: data.permissionBoundary.actorId,
    finding: findingDetail,
    governanceConfig: data.governanceConfig,
    occurredAt: data.meta.generatedAt,
  })
  const permissionBoundary = reviewSupport.permissionBoundary ?? data.permissionBoundary
  const reviewSupportSummary = buildReviewSupportSummary({
    actorId: reviewSupport.actorId,
    findingAssembly: assembly.summary,
    governanceConfig: data.governanceConfig,
    permissionBoundary,
    state: 'completed',
  })
  const auditEvents = deduplicateAuditEvents([
    ...data.auditEvents,
    ...collectFindingTimelineEvents(assembly.findingDetails),
  ])
  const auditRecording = buildAuditRecordingSummary({
    auditEvents,
    policyPackVersion: data.governanceConfig.activePolicyPack.version,
    scanId: data.scan.scanId,
    state: 'completed',
  })
  const aggregation = buildAdminMetricsAggregation({
    auditRecording,
    contentExtraction: data.scan.contentExtraction,
    contextRisk: data.scan.contextRisk,
    currentMetrics: data.metrics,
    deltaScan: data.scan.deltaScan,
    evaluation: data.evaluation,
    fileInventory: data.scan.fileInventory,
    findingAssembly: assembly.summary,
    flaggedFiles: data.scan.flaggedFiles ?? data.metrics.flaggedFiles,
    lastScanTimeSeconds: data.metrics.lastScanTimeSeconds ?? null,
    ownerAssignment: data.scan.ownerAssignment,
    reviewSupport: reviewSupportSummary,
    scannedFiles: data.scan.scannedFiles ?? data.metrics.totalScannedFiles,
    scannedGb: data.metrics.totalScannedGb ?? 0,
    scanId: data.scan.scanId,
    scanProgress: data.scan.progress,
    scanType: data.scan.scanType,
    signalDetection: data.scan.signalDetection,
    sourceId: data.scan.sourceId,
    state: 'completed',
    throughputFilesPerSecond: data.scan.throughputFilesPerSecond ?? null,
  })
  const evaluation = updateEvaluation({
    auditRecording,
    completedScan: data.scan,
    contentExtraction: data.scan.contentExtraction,
    contextRisk: data.scan.contextRisk,
    currentMetrics: data.metrics,
    current: data.evaluation,
    deltaScan: data.scan.deltaScan,
    fileInventory: data.scan.fileInventory,
    findingAssembly: assembly.summary,
    ownerAssignment: data.scan.ownerAssignment,
    reviewSupport: reviewSupportSummary,
    signalDetection: data.scan.signalDetection,
  })
  const existingStages = data.scan.pipelineStages ?? []
  const pipelineStages = [
    ...existingStages,
    ...(!existingStages.some((stage) => stage.stage === 'assembling_findings')
      ? [{
          stage: 'assembling_findings',
          status: assembly.summary.status,
          processedFiles: assembly.summary.assembledFindings,
          totalFiles: data.scan.ownerAssignment.assignedFindings,
          warnings: assembly.summary.warnings,
        }]
      : []),
    ...(!existingStages.some((stage) => stage.stage === 'preparing_review_support')
      ? [{
          stage: 'preparing_review_support',
          status: reviewSupportSummary.status,
          processedFiles: reviewSupportSummary.supportedFindings,
          totalFiles: assembly.summary.evidenceCards,
          warnings: reviewSupportSummary.warnings,
        }]
      : []),
    ...(!existingStages.some((stage) => stage.stage === 'recording_audit_events')
      ? [{
          stage: 'recording_audit_events',
          status: auditRecording.status,
          processedFiles: auditRecording.recordedEventCount,
          totalFiles: auditRecording.recordedEventCount,
          warnings: auditRecording.warnings,
        }]
      : []),
  ]

  return {
    ...data,
    scan: {
      ...data.scan,
      findingAssembly: assembly.summary,
      reviewSupport: reviewSupportSummary,
      pipelineStages,
      auditRecording,
    },
    findings: assembly.findings,
    findingDetail,
    findingDetails: assembly.findingDetails,
    auditEvents,
    permissionBoundary,
    reviewSupport,
    metrics: {
      ...data.metrics,
      assembledFindings: assembly.summary.assembledFindings,
      evidenceCards: assembly.summary.evidenceCards,
      reviewSupportedFindings: reviewSupportSummary.supportedFindings,
      deniedReviewActions: reviewSupportSummary.deniedActionCount,
      reviewChecklistItems: reviewSupportSummary.checklistItemCount,
      reviewTransferOptions: reviewSupportSummary.transferOptionCount,
      reviewEscalationOptions: reviewSupportSummary.escalationOptionCount,
      auditRecordedEvents: auditRecording.recordedEventCount,
      auditLinkedFindingEvents: auditRecording.linkedFindingEvents,
      auditReviewDecisionEvents: auditRecording.reviewDecisionEvents,
      evaluation,
      aggregation,
    },
    evaluation,
  }
}
