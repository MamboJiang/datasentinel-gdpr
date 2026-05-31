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
  Signal,
  SignalEvidenceAnchor,
  SourceReviewPreview,
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

function mergeFixtureReviewPreview(candidate: Finding, fixture: Finding): Finding {
  if (
    candidate.findingId === fixture.findingId
    && fixture.sourceReviewPreview
    && !candidate.sourceReviewPreview
  ) {
    const sourceReviewPreview = hasMatchingPreviewAnchor(candidate, fixture.sourceReviewPreview)
      ? fixture.sourceReviewPreview
      : buildRedactedSignalReviewPreview(candidate)

    return {
      ...candidate,
      sourceReviewPreview,
    }
  }

  return candidate
}

function hasMatchingPreviewAnchor(candidate: Finding, preview: SourceReviewPreview): boolean {
  const signalAnchorIds = new Set((candidate.signals ?? []).map(signalAnchorId))

  return (preview.anchors ?? []).some((anchor) => signalAnchorIds.has(anchor.anchorId))
}

function buildRedactedSignalReviewPreview(finding: Finding): SourceReviewPreview {
  const fileFormat = fileExtension(finding.fileName) ?? 'redacted_signal'
  const anchors = (finding.signals ?? []).map((signal, index) => {
    const anchorId = signalAnchorId(signal, index)
    const page = typeof signal.page === 'number' ? signal.page : 1
    const redactedText = signal.evidenceAnchor?.redactedText
      ?? signal.evidenceAnchor?.fallback?.redactedText
      ?? signal.snippet
    const selector = signal.evidenceAnchor?.selector ?? {
      type: 'textPosition',
      page,
    }
    const contextWindow = buildRedactedContextWindow(anchorId, redactedText)

    return {
      anchorId,
      label: signal.evidenceAnchor?.label ?? signal.type,
      format: signal.evidenceAnchor?.format ?? fileFormat,
      redactedText,
      fallbackLabel: signal.evidenceAnchor?.fallback?.label ?? `Page ${page} / redacted signal`,
      selector,
      contextWindow,
      confidence: signal.confidence,
      rawContentExposed: false,
    }
  })
  const pages = Array.from(new Set(anchors.map((anchor) => anchor.selector.page ?? 1)))
    .sort((left, right) => left - right)
    .map((page) => ({
      page,
      label: `Page ${page}`,
      pageImageExposed: false,
      regions: [],
    }))

  return {
    sourcePreviewId: `source_preview_${finding.findingId}`,
    sourceName: finding.fileName,
    fileFormat,
    extractionMethod: 'redacted_signal_summary',
    recognitionDifficulty: 'moderate',
    redactionMode: 'anchor_only',
    rawContentExposed: false,
    pageImagesExposed: false,
    anchors,
    contextWindows: anchors.map((anchor) => anchor.contextWindow),
    pages,
    warnings: ['Mock source preview uses redacted signal context only; raw source bytes remain sealed.'],
  }
}

function signalAnchorId(signal: Signal, index = 0): string {
  return signal.evidenceAnchor?.anchorId ?? `${signal.type}-${signal.detector}-${index}`
}

function buildRedactedContextWindow(anchorId: string, redactedText: string) {
  const markerMatch = redactedText.match(/\[REDACTED_[A-Z0-9_]+\]/)
  const highlightStart = markerMatch?.index ?? 0
  const highlightEnd = markerMatch ? highlightStart + markerMatch[0].length : redactedText.length

  return {
    anchorId,
    redactedContext: redactedText,
    contextStart: 0,
    contextEnd: redactedText.length,
    highlightStart,
    highlightEnd,
    redactionMode: 'signal_span_context',
    rawContentExposed: false,
  }
}

function fileExtension(fileName: string): SignalEvidenceAnchor['format'] | null {
  const match = /\.([a-z0-9]+)$/i.exec(fileName)
  return match ? match[1].toLowerCase() : null
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
  const findingDetail = mergeFixtureReviewPreview(
    assembly.findingDetails.finding_001 ?? Object.values(assembly.findingDetails)[0] ?? data.findingDetail,
    data.findingDetail,
  )
  const findingDetails = {
    ...assembly.findingDetails,
    [findingDetail.findingId]: findingDetail,
  }
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
    ...collectFindingTimelineEvents(findingDetails),
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
    findingDetails,
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
