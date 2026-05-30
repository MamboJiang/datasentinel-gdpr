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
} from '../types'

export type MockData = {
  sources: Source[]
  scan: Scan
  findings: FindingSummary[]
  findingDetail: Finding
  auditEvents: AuditEvent[]
  metrics: AdminMetrics
  evaluation: EvaluationSummary
  governanceConfig: GovernanceConfig
  permissionBoundary: PermissionBoundary
  reviewSupport: ReviewSupport
  meta: Meta
}

const fixtures: MockData = {
  sources: sourcesEnvelope.data,
  scan: scanEnvelope.data,
  findings: findingsEnvelope.data,
  findingDetail: findingDetailEnvelope.data,
  auditEvents: auditEventsEnvelope.data,
  metrics: adminMetricsEnvelope.data,
  evaluation: evaluationEnvelope.data,
  governanceConfig: governanceConfigEnvelope.data,
  permissionBoundary: permissionBoundaryEnvelope.data,
  reviewSupport: reviewSupportEnvelope.data as ReviewSupport,
  meta: sourcesEnvelope.meta,
}

export function getInitialMockData(): MockData {
  return structuredClone(fixtures)
}
